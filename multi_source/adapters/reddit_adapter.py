"""
Reddit platform adapter for lead generation using PRAW.
"""
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

try:
    import praw
    from praw.exceptions import PRAWException
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    praw = None

from ..core.interfaces import PlatformAdapter
from ..core.models import Prospect, SourceConfig, RateLimitInfo


logger = logging.getLogger(__name__)


class RedditAdapter(PlatformAdapter):
    """Reddit adapter using PRAW for prospect discovery."""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        
        self.rate_limit_info = RateLimitInfo(
            requests_per_minute=60,  # Reddit's rate limit
            requests_per_hour=3600,
            current_usage=0,
            delay_seconds=1.0
        )
        self.last_request_time = 0
        
        if not PRAW_AVAILABLE:
            logger.error("PRAW library not available. Install with: pip install praw")
            self.reddit = None
            return
        
        # Reddit API credentials
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'LeadGenBot/1.0')
        
        self.reddit = None
        
        if self.client_id and self.client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent
                )
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {str(e)}")
                self.reddit = None
    
    def authenticate(self) -> bool:
        """Handle Reddit API authentication."""
        if not PRAW_AVAILABLE:
            logger.error("PRAW library not available")
            return False
        
        if not self.client_id or not self.client_secret:
            logger.error("Reddit API credentials not found in environment variables")
            return False
        
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return False
        
        try:
            # Test authentication by accessing user info
            user = self.reddit.user.me()
            logger.info("Reddit authentication successful")
            return True
        except Exception as e:
            # For read-only access, we don't need user authentication
            # Try a simple API call instead
            try:
                subreddit = self.reddit.subreddit('test')
                list(subreddit.hot(limit=1))
                logger.info("Reddit read-only access successful")
                return True
            except Exception as e2:
                logger.error(f"Reddit authentication failed: {str(e2)}")
                return False
    
    def _handle_rate_limiting(self):
        """Implement rate limiting with delays."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_info.delay_seconds:
            sleep_time = self.rate_limit_info.delay_seconds - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute search with Reddit API.
        
        Searches relevant subreddits for active contributors.
        """
        if not self.reddit:
            logger.error("Reddit client not available")
            return []
        
        results = []
        filters = filters or {}
        
        # Get relevant subreddits based on query
        subreddits = self._get_relevant_subreddits(query, filters)
        
        for subreddit_name in subreddits:
            try:
                subreddit_results = self._search_subreddit(subreddit_name, query, filters)
                results.extend(subreddit_results)
                
                # Respect rate limits
                self._handle_rate_limiting()
                
            except Exception as e:
                logger.error(f"Error searching subreddit {subreddit_name}: {str(e)}")
                continue
        
        return results
    
    def _get_relevant_subreddits(self, query: str, filters: Dict[str, Any]) -> List[str]:
        """Get list of relevant subreddits based on query and filters."""
        # Default professional/business subreddits
        default_subreddits = [
            'entrepreneur', 'startups', 'business', 'marketing', 'sales',
            'technology', 'programming', 'webdev', 'MachineLearning',
            'artificial', 'datascience', 'investing', 'finance'
        ]
        
        # Allow custom subreddits from filters
        custom_subreddits = filters.get('subreddits', [])
        
        # Combine and deduplicate
        all_subreddits = list(set(default_subreddits + custom_subreddits))
        
        # Limit to prevent excessive API calls
        max_subreddits = filters.get('max_subreddits', 5)
        return all_subreddits[:max_subreddits]
    
    def _search_subreddit(self, subreddit_name: str, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search a specific subreddit for relevant posts and active users."""
        results = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Search for relevant posts
            search_results = subreddit.search(
                query,
                limit=filters.get('posts_per_subreddit', 20),
                time_filter='month'  # Focus on recent activity
            )
            
            for post in search_results:
                try:
                    # Get post author
                    if post.author and not post.author.name.startswith('[deleted]'):
                        author_data = self._get_user_data(post.author, subreddit_name)
                        if author_data:
                            author_data['context'] = {
                                'post_title': post.title,
                                'post_url': f"https://reddit.com{post.permalink}",
                                'post_score': post.score,
                                'subreddit': subreddit_name
                            }
                            results.append(author_data)
                    
                    # Get active commenters (top comments only)
                    post.comments.replace_more(limit=0)  # Remove "more comments"
                    top_comments = post.comments[:5]  # Limit to top 5 comments
                    
                    for comment in top_comments:
                        if comment.author and not comment.author.name.startswith('[deleted]'):
                            commenter_data = self._get_user_data(comment.author, subreddit_name)
                            if commenter_data:
                                commenter_data['context'] = {
                                    'comment_text': comment.body[:200] + '...' if len(comment.body) > 200 else comment.body,
                                    'comment_score': comment.score,
                                    'post_title': post.title,
                                    'post_url': f"https://reddit.com{post.permalink}",
                                    'subreddit': subreddit_name
                                }
                                results.append(commenter_data)
                
                except Exception as e:
                    logger.error(f"Error processing post in {subreddit_name}: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error accessing subreddit {subreddit_name}: {str(e)}")
        
        return results
    
    def _get_user_data(self, redditor, subreddit_context: str) -> Optional[Dict[str, Any]]:
        """Extract user data from Reddit user object."""
        try:
            # Basic user info
            user_data = {
                'type': 'reddit_user',
                'username': redditor.name,
                'user_url': f"https://reddit.com/user/{redditor.name}",
                'subreddit_context': subreddit_context,
                'created_utc': redditor.created_utc,
                'comment_karma': getattr(redditor, 'comment_karma', 0),
                'link_karma': getattr(redditor, 'link_karma', 0),
                'is_verified': getattr(redditor, 'verified', False),
                'has_premium': getattr(redditor, 'is_gold', False)
            }
            
            # Try to get additional profile info (may not be available)
            try:
                if hasattr(redditor, 'subreddit') and redditor.subreddit:
                    user_data['profile_description'] = getattr(redditor.subreddit, 'public_description', '')
                    user_data['profile_title'] = getattr(redditor.subreddit, 'title', '')
            except Exception:
                pass  # Profile info not available
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data for {redditor.name}: {str(e)}")
            return None
    
    def extract_prospects(self, results: List[Dict[str, Any]]) -> List[Prospect]:
        """Convert Reddit results to standardized prospect format."""
        prospects = []
        
        for result in results:
            try:
                username = result.get('username', '')
                if not username:
                    continue
                
                # Calculate engagement score
                comment_karma = result.get('comment_karma', 0)
                link_karma = result.get('link_karma', 0)
                total_karma = comment_karma + link_karma
                
                # Account age factor
                created_utc = result.get('created_utc', 0)
                account_age_days = (time.time() - created_utc) / (24 * 3600) if created_utc else 0
                
                # Engagement scoring algorithm
                engagement_score = min(1.0, (
                    (total_karma / 10000) * 0.5 +  # Karma influence
                    (1 if account_age_days > 365 else account_age_days / 365) * 0.2 +  # Account maturity
                    (1 if result.get('is_verified') else 0) * 0.2 +  # Verification
                    (1 if result.get('has_premium') else 0) * 0.1  # Premium status
                ))
                
                # Extract potential company/title from profile
                profile_description = result.get('profile_description', '')
                profile_title = result.get('profile_title', '')
                
                title, company = self._extract_title_company_from_profile(
                    profile_description, profile_title
                )
                
                # Determine activity context
                context = result.get('context', {})
                subreddit_context = result.get('subreddit_context', '')
                
                # Create bio from available information
                bio_parts = []
                if profile_title:
                    bio_parts.append(profile_title)
                if profile_description:
                    bio_parts.append(profile_description)
                if context.get('post_title'):
                    bio_parts.append(f"Recent post: {context['post_title']}")
                
                bio = ' | '.join(bio_parts) if bio_parts else f"Active in r/{subreddit_context}"
                
                prospect = Prospect(
                    name=username,  # Reddit doesn't provide real names
                    title=title,
                    company=company,
                    source_platform="reddit",
                    source_url=result.get('user_url', f"https://reddit.com/user/{username}"),
                    bio=bio,
                    engagement_score=engagement_score,
                    last_activity=datetime.fromtimestamp(created_utc) if created_utc else None,
                    additional_data={
                        'username': username,
                        'comment_karma': comment_karma,
                        'link_karma': link_karma,
                        'total_karma': total_karma,
                        'account_age_days': account_age_days,
                        'subreddit_context': subreddit_context,
                        'is_verified': result.get('is_verified', False),
                        'has_premium': result.get('has_premium', False),
                        'context': context
                    }
                )
                
                prospects.append(prospect)
                
            except Exception as e:
                logger.error(f"Error extracting prospect from Reddit data: {str(e)}")
                continue
        
        return prospects
    
    def _extract_title_company_from_profile(self, description: str, title: str) -> tuple[Optional[str], Optional[str]]:
        """Extract potential title and company from Reddit profile."""
        text = f"{title} {description}".strip()
        if not text:
            return None, None
        
        extracted_title = None
        company = None
        
        text_lower = text.lower()
        
        # Look for common title keywords
        title_keywords = ['ceo', 'founder', 'cto', 'cmo', 'vp', 'director', 'manager', 'lead', 'head', 'engineer', 'developer']
        for keyword in title_keywords:
            if keyword in text_lower:
                # Try to extract the full title context
                words = text.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        # Take surrounding words as potential title
                        start = max(0, i-1)
                        end = min(len(words), i+3)
                        extracted_title = ' '.join(words[start:end])
                        break
                break
        
        # Look for company indicators
        company_indicators = ['at ', 'working at', 'founder of', 'ceo of', 'works at']
        for indicator in company_indicators:
            if indicator in text_lower:
                # Extract text after indicator
                idx = text_lower.find(indicator)
                if idx != -1:
                    after_indicator = text[idx + len(indicator):].strip()
                    # Take first few words as company name
                    company_words = after_indicator.split()[:3]
                    company = ' '.join(company_words).strip('.,!?')
                break
        
        return extracted_title, company
    
    def get_rate_limits(self) -> RateLimitInfo:
        """Return current rate limit status."""
        return self.rate_limit_info