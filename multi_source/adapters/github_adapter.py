"""
GitHub platform adapter for developer prospecting.
"""
import os
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from ..core.interfaces import PlatformAdapter
from ..core.models import Prospect, SourceConfig, RateLimitInfo


logger = logging.getLogger(__name__)


class GitHubAdapter(PlatformAdapter):
    """GitHub API adapter for developer prospect discovery."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.token = os.getenv('GITHUB_TOKEN')
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.last_request_time = 0
        self.rate_limit_info = RateLimitInfo(
            requests_per_minute=60,  # GitHub's rate limit for authenticated requests
            requests_per_hour=5000,
            current_usage=0,
            delay_seconds=1.0
        )
        
        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'LeadGenBot/1.0'
            })
        else:
            # Unauthenticated requests have lower rate limits
            self.rate_limit_info.requests_per_minute = 10
            self.rate_limit_info.requests_per_hour = 60
            self.session.headers.update({
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'LeadGenBot/1.0'
            })
    
    def authenticate(self) -> bool:
        """Handle GitHub API authentication."""
        try:
            if self.token:
                # Test authentication with user info
                response = self.session.get(f"{self.base_url}/user")
                if response.status_code == 200:
                    logger.info("GitHub authentication successful")
                    return True
                else:
                    logger.error(f"GitHub authentication failed: {response.status_code}")
                    return False
            else:
                # Test unauthenticated access
                response = self.session.get(f"{self.base_url}/rate_limit")
                if response.status_code == 200:
                    logger.info("GitHub unauthenticated access successful")
                    return True
                else:
                    logger.error("GitHub API access failed")
                    return False
        except Exception as e:
            logger.error(f"GitHub authentication error: {str(e)}")
            return False
    
    def _handle_rate_limiting(self):
        """Implement rate limiting with delays."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_info.delay_seconds:
            sleep_time = self.rate_limit_info.delay_seconds - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make rate-limited request to GitHub API."""
        self._handle_rate_limiting()
        
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            self.rate_limit_info.current_usage += 1
            
            # Update rate limit info from headers
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = int(response.headers['X-RateLimit-Remaining'])
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                self.rate_limit_info.reset_time = datetime.fromtimestamp(reset_time)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                # Rate limit exceeded or forbidden
                logger.warning(f"GitHub API rate limit or access denied: {response.status_code}")
                return None
            else:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"GitHub API request error: {str(e)}")
            return None
    
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute search with GitHub API.
        
        Searches for repositories, users, and organizations.
        """
        results = []
        filters = filters or {}
        
        # Search repositories to find active contributors
        repo_results = self._search_repositories(query, filters)
        if repo_results:
            results.extend(repo_results)
        
        # Search users directly
        user_results = self._search_users(query, filters)
        if user_results:
            results.extend(user_results)
        
        # Search organizations
        org_results = self._search_organizations(query, filters)
        if org_results:
            results.extend(org_results)
        
        return results
    
    def _search_repositories(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for repositories and extract contributor information."""
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': min(filters.get('repos_per_search', 20), 100)
        }
        
        # Add language filter if specified
        if filters.get('language'):
            params['q'] += f" language:{filters['language']}"
        
        # Add minimum stars filter
        if filters.get('min_stars'):
            params['q'] += f" stars:>={filters['min_stars']}"
        
        data = self._make_request("search/repositories", params)
        if not data or 'items' not in data:
            return []
        
        results = []
        
        for repo in data['items']:
            try:
                # Get repository contributors
                contributors = self._get_repository_contributors(
                    repo['owner']['login'], 
                    repo['name'],
                    filters.get('max_contributors_per_repo', 5)
                )
                
                for contributor in contributors:
                    contributor['repository_context'] = {
                        'repo_name': repo['full_name'],
                        'repo_url': repo['html_url'],
                        'repo_description': repo.get('description', ''),
                        'repo_stars': repo.get('stargazers_count', 0),
                        'repo_language': repo.get('language', ''),
                        'contributions': contributor.get('contributions', 0)
                    }
                    results.append(contributor)
                
                # Also include repository owner if they're not already included
                owner_data = self._get_user_details(repo['owner']['login'])
                if owner_data:
                    owner_data['repository_context'] = {
                        'repo_name': repo['full_name'],
                        'repo_url': repo['html_url'],
                        'repo_description': repo.get('description', ''),
                        'repo_stars': repo.get('stargazers_count', 0),
                        'repo_language': repo.get('language', ''),
                        'role': 'owner'
                    }
                    results.append(owner_data)
                
            except Exception as e:
                logger.error(f"Error processing repository {repo['full_name']}: {str(e)}")
                continue
        
        return results
    
    def _search_users(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for users directly."""
        params = {
            'q': query,
            'sort': 'followers',
            'order': 'desc',
            'per_page': min(filters.get('users_per_search', 20), 100)
        }
        
        # Add location filter if specified
        if filters.get('location'):
            params['q'] += f" location:{filters['location']}"
        
        # Add minimum followers filter
        if filters.get('min_followers'):
            params['q'] += f" followers:>={filters['min_followers']}"
        
        data = self._make_request("search/users", params)
        if not data or 'items' not in data:
            return []
        
        results = []
        
        for user in data['items']:
            try:
                user_details = self._get_user_details(user['login'])
                if user_details:
                    user_details['search_context'] = 'direct_user_search'
                    results.append(user_details)
            except Exception as e:
                logger.error(f"Error getting user details for {user['login']}: {str(e)}")
                continue
        
        return results
    
    def _search_organizations(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for organizations and their members."""
        params = {
            'q': query + ' type:org',
            'sort': 'repositories',
            'order': 'desc',
            'per_page': min(filters.get('orgs_per_search', 10), 100)
        }
        
        data = self._make_request("search/users", params)
        if not data or 'items' not in data:
            return []
        
        results = []
        
        for org in data['items']:
            try:
                # Get organization members (public members only)
                members = self._get_organization_members(
                    org['login'],
                    filters.get('max_members_per_org', 10)
                )
                
                for member in members:
                    member['organization_context'] = {
                        'org_name': org['login'],
                        'org_url': org['html_url'],
                        'org_type': 'Organization'
                    }
                    results.append(member)
                
            except Exception as e:
                logger.error(f"Error processing organization {org['login']}: {str(e)}")
                continue
        
        return results
    
    def _get_repository_contributors(self, owner: str, repo: str, max_contributors: int) -> List[Dict[str, Any]]:
        """Get contributors for a specific repository."""
        params = {
            'per_page': max_contributors,
            'anon': 'false'  # Exclude anonymous contributors
        }
        
        data = self._make_request(f"repos/{owner}/{repo}/contributors", params)
        if not data:
            return []
        
        contributors = []
        for contributor in data:
            try:
                user_details = self._get_user_details(contributor['login'])
                if user_details:
                    user_details['contributions'] = contributor.get('contributions', 0)
                    contributors.append(user_details)
            except Exception as e:
                logger.error(f"Error getting contributor details for {contributor['login']}: {str(e)}")
                continue
        
        return contributors
    
    def _get_organization_members(self, org: str, max_members: int) -> List[Dict[str, Any]]:
        """Get public members of an organization."""
        params = {
            'per_page': max_members
        }
        
        data = self._make_request(f"orgs/{org}/public_members", params)
        if not data:
            return []
        
        members = []
        for member in data:
            try:
                user_details = self._get_user_details(member['login'])
                if user_details:
                    members.append(user_details)
            except Exception as e:
                logger.error(f"Error getting member details for {member['login']}: {str(e)}")
                continue
        
        return members
    
    def _get_user_details(self, username: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific user."""
        data = self._make_request(f"users/{username}", {})
        if not data:
            return None
        
        return {
            'type': 'github_user',
            'username': username,
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'bio': data.get('bio', ''),
            'company': data.get('company', ''),
            'location': data.get('location', ''),
            'blog': data.get('blog', ''),
            'twitter_username': data.get('twitter_username', ''),
            'public_repos': data.get('public_repos', 0),
            'followers': data.get('followers', 0),
            'following': data.get('following', 0),
            'created_at': data.get('created_at', ''),
            'updated_at': data.get('updated_at', ''),
            'html_url': data.get('html_url', ''),
            'avatar_url': data.get('avatar_url', ''),
            'hireable': data.get('hireable', False)
        }
    
    def extract_prospects(self, results: List[Dict[str, Any]]) -> List[Prospect]:
        """Convert GitHub results to standardized prospect format."""
        prospects = []
        
        for result in results:
            try:
                username = result.get('username', '')
                name = result.get('name', '') or username
                
                if not username:
                    continue
                
                # Calculate engagement score
                followers = result.get('followers', 0)
                public_repos = result.get('public_repos', 0)
                contributions = result.get('contributions', 0)
                
                # Account age factor
                created_at = result.get('created_at', '')
                account_age_days = 0
                if created_at:
                    try:
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        account_age_days = (datetime.now(created_date.tzinfo) - created_date).days
                    except:
                        pass
                
                # Engagement scoring algorithm
                engagement_score = min(1.0, (
                    (followers / 1000) * 0.3 +  # Follower influence
                    (public_repos / 50) * 0.3 +  # Repository activity
                    (contributions / 100) * 0.2 +  # Contribution activity
                    (1 if account_age_days > 365 else account_age_days / 365) * 0.1 +  # Account maturity
                    (1 if result.get('hireable') else 0) * 0.1  # Hireable status
                ))
                
                # Extract company and title
                company = result.get('company', '').strip()
                if company.startswith('@'):
                    company = company[1:]  # Remove @ prefix
                
                # Try to extract title from bio
                bio = result.get('bio', '')
                title = self._extract_title_from_bio(bio)
                
                # Determine last activity
                last_activity = None
                updated_at = result.get('updated_at', '')
                if updated_at:
                    try:
                        last_activity = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Build context information
                context_info = []
                repo_context = result.get('repository_context', {})
                org_context = result.get('organization_context', {})
                
                if repo_context:
                    if repo_context.get('role') == 'owner':
                        context_info.append(f"Owner of {repo_context['repo_name']}")
                    else:
                        context_info.append(f"Contributor to {repo_context['repo_name']}")
                
                if org_context:
                    context_info.append(f"Member of {org_context['org_name']}")
                
                # Build bio with context
                bio_parts = []
                if bio:
                    bio_parts.append(bio)
                if context_info:
                    bio_parts.extend(context_info)
                
                final_bio = ' | '.join(bio_parts) if bio_parts else f"GitHub developer with {public_repos} repositories"
                
                # Build URLs
                twitter_url = None
                if result.get('twitter_username'):
                    twitter_url = f"https://twitter.com/{result['twitter_username']}"
                
                website = result.get('blog', '')
                if website and not website.startswith('http'):
                    website = f"https://{website}"
                
                prospect = Prospect(
                    name=name,
                    title=title,
                    company=company if company else None,
                    email=result.get('email'),
                    github_url=result.get('html_url', f"https://github.com/{username}"),
                    twitter_url=twitter_url,
                    website=website if website else None,
                    bio=final_bio,
                    location=result.get('location'),
                    source_platform="github",
                    source_url=result.get('html_url', f"https://github.com/{username}"),
                    engagement_score=engagement_score,
                    last_activity=last_activity,
                    additional_data={
                        'username': username,
                        'followers': followers,
                        'following': result.get('following', 0),
                        'public_repos': public_repos,
                        'contributions': contributions,
                        'account_age_days': account_age_days,
                        'hireable': result.get('hireable', False),
                        'avatar_url': result.get('avatar_url', ''),
                        'repository_context': repo_context,
                        'organization_context': org_context,
                        'search_context': result.get('search_context', '')
                    }
                )
                
                prospects.append(prospect)
                
            except Exception as e:
                logger.error(f"Error extracting prospect from GitHub data: {str(e)}")
                continue
        
        return prospects
    
    def _extract_title_from_bio(self, bio: str) -> Optional[str]:
        """Extract potential job title from GitHub bio."""
        if not bio:
            return None
        
        bio_lower = bio.lower()
        
        # Common title keywords
        title_keywords = [
            'engineer', 'developer', 'architect', 'lead', 'senior', 'principal',
            'manager', 'director', 'cto', 'ceo', 'founder', 'co-founder',
            'consultant', 'freelancer', 'student', 'researcher'
        ]
        
        for keyword in title_keywords:
            if keyword in bio_lower:
                # Try to extract the full title context
                words = bio.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        # Take surrounding words as potential title
                        start = max(0, i-2)
                        end = min(len(words), i+3)
                        title = ' '.join(words[start:end])
                        # Clean up the title
                        title = title.strip('.,!?@#$%^&*()')
                        return title
                break
        
        return None
    
    def get_rate_limits(self) -> RateLimitInfo:
        """Return current rate limit status."""
        return self.rate_limit_info