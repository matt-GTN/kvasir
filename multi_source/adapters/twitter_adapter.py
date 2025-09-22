"""
Twitter/X platform adapter for lead generation.
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


class TwitterAdapter(PlatformAdapter):
    """Twitter/X API v2 adapter for prospect discovery."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.base_url = "https://api.twitter.com/2"
        self.session = requests.Session()
        self.last_request_time = 0
        self.rate_limit_info = RateLimitInfo(
            requests_per_minute=300,
            requests_per_hour=300,
            current_usage=0,
            delay_seconds=1.0
        )
        
        if self.bearer_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            })
    
    def authenticate(self) -> bool:
        """Handle Twitter API authentication."""
        if not self.bearer_token:
            logger.error("Twitter Bearer Token not found in environment variables")
            return False
        
        try:
            # Test authentication with a simple API call
            response = self.session.get(f"{self.base_url}/users/me")
            if response.status_code == 200:
                logger.info("Twitter authentication successful")
                return True
            else:
                logger.error(f"Twitter authentication failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Twitter authentication error: {str(e)}")
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
        """Make rate-limited request to Twitter API."""
        self._handle_rate_limiting()
        
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            self.rate_limit_info.current_usage += 1
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit exceeded
                logger.warning("Twitter rate limit exceeded")
                reset_time = response.headers.get('x-rate-limit-reset')
                if reset_time:
                    self.rate_limit_info.reset_time = datetime.fromtimestamp(int(reset_time))
                return None
            else:
                logger.error(f"Twitter API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Twitter API request error: {str(e)}")
            return None
    
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute search with Twitter API v2.
        
        Searches for users, tweets, and hashtags based on the query.
        """
        results = []
        filters = filters or {}
        
        # Search for tweets first to find active users
        tweet_results = self._search_tweets(query, filters)
        if tweet_results:
            results.extend(tweet_results)
        
        # Search for users directly
        user_results = self._search_users(query, filters)
        if user_results:
            results.extend(user_results)
        
        return results
    
    def _search_tweets(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for tweets and extract user information."""
        params = {
            'query': query,
            'max_results': min(filters.get('max_results', 50), 100),
            'tweet.fields': 'author_id,created_at,public_metrics,context_annotations',
            'user.fields': 'name,username,description,location,url,public_metrics,verified',
            'expansions': 'author_id'
        }
        
        # Add additional filters
        if filters.get('language'):
            params['query'] += f" lang:{filters['language']}"
        
        if filters.get('has_links'):
            params['query'] += " has:links"
        
        if filters.get('min_followers'):
            params['query'] += f" followers_count:{filters['min_followers']}"
        
        data = self._make_request("tweets/search/recent", params)
        if not data or 'data' not in data:
            return []
        
        results = []
        users_data = {user['id']: user for user in data.get('includes', {}).get('users', [])}
        
        for tweet in data['data']:
            author_id = tweet.get('author_id')
            if author_id and author_id in users_data:
                user_data = users_data[author_id]
                result = {
                    'type': 'tweet_author',
                    'tweet': tweet,
                    'user': user_data,
                    'source_url': f"https://twitter.com/{user_data['username']}/status/{tweet['id']}"
                }
                results.append(result)
        
        return results
    
    def _search_users(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for users directly (limited functionality in API v2)."""
        # Note: Direct user search is limited in Twitter API v2
        # This would typically require additional endpoints or different approach
        results = []
        
        # For now, we'll focus on tweet-based user discovery
        # In a full implementation, you might use the user lookup endpoint
        # with known usernames or IDs from other sources
        
        return results
    
    def extract_prospects(self, results: List[Dict[str, Any]]) -> List[Prospect]:
        """Convert Twitter results to standardized prospect format."""
        prospects = []
        
        for result in results:
            try:
                user_data = result.get('user', {})
                tweet_data = result.get('tweet', {})
                
                if not user_data:
                    continue
                
                # Extract basic information
                name = user_data.get('name', '')
                username = user_data.get('username', '')
                bio = user_data.get('description', '')
                location = user_data.get('location', '')
                website = user_data.get('url', '')
                
                # Calculate engagement score based on metrics
                public_metrics = user_data.get('public_metrics', {})
                followers_count = public_metrics.get('followers_count', 0)
                following_count = public_metrics.get('following_count', 0)
                tweet_count = public_metrics.get('tweet_count', 0)
                
                # Simple engagement scoring algorithm
                engagement_score = min(1.0, (
                    (followers_count / 10000) * 0.4 +  # Follower influence
                    (tweet_count / 1000) * 0.3 +       # Activity level
                    (1 if user_data.get('verified') else 0) * 0.3  # Verification status
                ))
                
                # Extract potential company/title from bio
                title, company = self._extract_title_company_from_bio(bio)
                
                # Determine last activity
                last_activity = None
                if tweet_data and 'created_at' in tweet_data:
                    last_activity = datetime.fromisoformat(
                        tweet_data['created_at'].replace('Z', '+00:00')
                    )
                
                prospect = Prospect(
                    name=name,
                    title=title,
                    company=company,
                    twitter_url=f"https://twitter.com/{username}",
                    website=website if website else None,
                    bio=bio,
                    location=location,
                    source_platform="twitter",
                    source_url=result.get('source_url', f"https://twitter.com/{username}"),
                    engagement_score=engagement_score,
                    last_activity=last_activity,
                    additional_data={
                        'username': username,
                        'followers_count': followers_count,
                        'following_count': following_count,
                        'tweet_count': tweet_count,
                        'verified': user_data.get('verified', False),
                        'tweet_context': tweet_data.get('text', '') if tweet_data else ''
                    }
                )
                
                prospects.append(prospect)
                
            except Exception as e:
                logger.error(f"Error extracting prospect from Twitter data: {str(e)}")
                continue
        
        return prospects
    
    def _extract_title_company_from_bio(self, bio: str) -> tuple[Optional[str], Optional[str]]:
        """Extract potential title and company from Twitter bio."""
        if not bio:
            return None, None
        
        title = None
        company = None
        
        # Common patterns for title/company in Twitter bios
        bio_lower = bio.lower()
        
        # Look for common title keywords
        title_keywords = ['ceo', 'founder', 'cto', 'cmo', 'vp', 'director', 'manager', 'lead', 'head']
        for keyword in title_keywords:
            if keyword in bio_lower:
                # Try to extract the full title context
                words = bio.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        # Take surrounding words as potential title
                        start = max(0, i-1)
                        end = min(len(words), i+3)
                        title = ' '.join(words[start:end])
                        break
                break
        
        # Look for company indicators
        company_indicators = ['@', 'at ', 'working at', 'founder of', 'ceo of']
        for indicator in company_indicators:
            if indicator in bio_lower:
                # Extract potential company name
                if indicator == '@':
                    # Look for @company pattern
                    import re
                    matches = re.findall(r'@(\w+)', bio)
                    if matches:
                        company = matches[0]
                else:
                    # Extract text after indicator
                    idx = bio_lower.find(indicator)
                    if idx != -1:
                        after_indicator = bio[idx + len(indicator):].strip()
                        # Take first few words as company name
                        company_words = after_indicator.split()[:3]
                        company = ' '.join(company_words).strip('.,!?')
                break
        
        return title, company
    
    def get_rate_limits(self) -> RateLimitInfo:
        """Return current rate limit status."""
        return self.rate_limit_info