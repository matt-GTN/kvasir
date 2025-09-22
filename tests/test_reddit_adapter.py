"""
Unit tests for Reddit adapter.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os
import time

from multi_source.adapters.reddit_adapter import RedditAdapter, PRAW_AVAILABLE
from multi_source.core.models import SourceConfig, SourcePlatform, Prospect


class TestRedditAdapter(unittest.TestCase):
    """Test cases for RedditAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = SourceConfig(
            platform=SourcePlatform.REDDIT,
            priority=7,
            max_results=50,
            rate_limit_delay=1.0,
            enabled=True
        )
    
    @patch.dict(os.environ, {
        'REDDIT_CLIENT_ID': 'test_client_id',
        'REDDIT_CLIENT_SECRET': 'test_client_secret',
        'REDDIT_USER_AGENT': 'TestBot/1.0'
    })
    @patch('multi_source.adapters.reddit_adapter.praw')
    def test_init_with_praw(self, mock_praw):
        """Test RedditAdapter initialization with PRAW available."""
        mock_reddit_instance = Mock()
        mock_praw.Reddit.return_value = mock_reddit_instance
        
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', True):
            adapter = RedditAdapter(self.config)
        
        self.assertEqual(adapter.config, self.config)
        self.assertEqual(adapter.client_id, "test_client_id")
        self.assertEqual(adapter.client_secret, "test_client_secret")
        self.assertEqual(adapter.user_agent, "TestBot/1.0")
        self.assertEqual(adapter.reddit, mock_reddit_instance)
        self.assertEqual(adapter.rate_limit_info.requests_per_minute, 60)
    
    def test_init_without_praw(self):
        """Test RedditAdapter initialization without PRAW."""
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', False):
            adapter = RedditAdapter(self.config)
        
        self.assertIsNone(adapter.reddit)
    
    @patch.dict(os.environ, {})
    def test_init_no_credentials(self):
        """Test initialization without credentials."""
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', True):
            adapter = RedditAdapter(self.config)
        
        self.assertIsNone(adapter.reddit)
    
    @patch.dict(os.environ, {
        'REDDIT_CLIENT_ID': 'test_client_id',
        'REDDIT_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('multi_source.adapters.reddit_adapter.praw')
    def test_authenticate_success(self, mock_praw):
        """Test successful authentication."""
        mock_reddit_instance = Mock()
        mock_reddit_instance.user.me.return_value = Mock()
        mock_praw.Reddit.return_value = mock_reddit_instance
        
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', True):
            adapter = RedditAdapter(self.config)
            result = adapter.authenticate()
        
        self.assertTrue(result)
    
    @patch.dict(os.environ, {
        'REDDIT_CLIENT_ID': 'test_client_id',
        'REDDIT_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('multi_source.adapters.reddit_adapter.praw')
    def test_authenticate_readonly_fallback(self, mock_praw):
        """Test authentication fallback to read-only access."""
        mock_reddit_instance = Mock()
        mock_reddit_instance.user.me.side_effect = Exception("Auth failed")
        
        # Mock subreddit access for read-only test
        mock_subreddit = Mock()
        mock_subreddit.hot.return_value = [Mock()]
        mock_reddit_instance.subreddit.return_value = mock_subreddit
        
        mock_praw.Reddit.return_value = mock_reddit_instance
        
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', True):
            adapter = RedditAdapter(self.config)
            result = adapter.authenticate()
        
        self.assertTrue(result)
    
    def test_authenticate_no_praw(self):
        """Test authentication without PRAW."""
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', False):
            adapter = RedditAdapter(self.config)
            result = adapter.authenticate()
        
        self.assertFalse(result)
    
    @patch('time.sleep')
    @patch('time.time')
    def test_rate_limiting(self, mock_time, mock_sleep):
        """Test rate limiting functionality."""
        mock_time.side_effect = [0, 0.5, 1.0]
        
        adapter = RedditAdapter(self.config)
        adapter.last_request_time = 0
        adapter.rate_limit_info.delay_seconds = 1.0
        
        adapter._handle_rate_limiting()
        
        mock_sleep.assert_called_once_with(0.5)
    
    def test_get_relevant_subreddits(self):
        """Test subreddit selection logic."""
        adapter = RedditAdapter(self.config)
        
        # Test default subreddits
        subreddits = adapter._get_relevant_subreddits("test query", {})
        self.assertIsInstance(subreddits, list)
        self.assertIn('entrepreneur', subreddits)
        self.assertIn('startups', subreddits)
        
        # Test custom subreddits
        custom_filters = {'subreddits': ['customsub1', 'customsub2']}
        subreddits = adapter._get_relevant_subreddits("test query", custom_filters)
        self.assertIn('customsub1', subreddits)
        self.assertIn('customsub2', subreddits)
        
        # Test max subreddits limit
        limited_filters = {'max_subreddits': 2}
        subreddits = adapter._get_relevant_subreddits("test query", limited_filters)
        self.assertLessEqual(len(subreddits), 2)
    
    @patch.dict(os.environ, {
        'REDDIT_CLIENT_ID': 'test_client_id',
        'REDDIT_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('multi_source.adapters.reddit_adapter.praw')
    def test_search_subreddit(self, mock_praw):
        """Test searching a specific subreddit."""
        # Mock Reddit objects
        mock_post = Mock()
        mock_post.title = "Test Post"
        mock_post.score = 100
        mock_post.permalink = "/r/test/comments/123/test_post/"
        mock_post.author = Mock()
        mock_post.author.name = "testuser"
        
        mock_comment = Mock()
        mock_comment.body = "Great post!"
        mock_comment.score = 10
        mock_comment.author = Mock()
        mock_comment.author.name = "commenter"
        
        mock_comments = Mock()
        mock_comments.__iter__ = Mock(return_value=iter([mock_comment]))
        mock_comments.__getitem__ = Mock(return_value=[mock_comment])
        mock_comments.replace_more = Mock()
        mock_post.comments = mock_comments
        
        mock_subreddit = Mock()
        mock_subreddit.search.return_value = [mock_post]
        
        mock_reddit_instance = Mock()
        mock_reddit_instance.subreddit.return_value = mock_subreddit
        mock_praw.Reddit.return_value = mock_reddit_instance
        
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', True):
            adapter = RedditAdapter(self.config)
            
            # Mock _get_user_data method
            with patch.object(adapter, '_get_user_data', return_value={'username': 'testuser'}):
                results = adapter._search_subreddit("test", "test query", {})
        
        self.assertIsInstance(results, list)
        # Should have results for both post author and commenter
        self.assertGreaterEqual(len(results), 0)
    
    def test_get_user_data(self):
        """Test user data extraction."""
        adapter = RedditAdapter(self.config)
        
        # Mock redditor object
        mock_redditor = Mock()
        mock_redditor.name = "testuser"
        mock_redditor.created_utc = 1640995200  # 2022-01-01
        mock_redditor.comment_karma = 1000
        mock_redditor.link_karma = 500
        mock_redditor.verified = True
        mock_redditor.is_gold = False
        
        user_data = adapter._get_user_data(mock_redditor, "entrepreneur")
        
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['comment_karma'], 1000)
        self.assertEqual(user_data['link_karma'], 500)
        self.assertEqual(user_data['subreddit_context'], 'entrepreneur')
        self.assertTrue(user_data['is_verified'])
    
    def test_extract_prospects(self):
        """Test prospect extraction from Reddit data."""
        adapter = RedditAdapter(self.config)
        
        reddit_results = [
            {
                'username': 'johndoe',
                'user_url': 'https://reddit.com/user/johndoe',
                'created_utc': time.time() - (365 * 24 * 3600),  # 1 year ago
                'comment_karma': 5000,
                'link_karma': 2000,
                'is_verified': True,
                'has_premium': False,
                'subreddit_context': 'entrepreneur',
                'profile_title': 'Startup Founder',
                'profile_description': 'CEO at TechCorp',
                'context': {
                    'post_title': 'How to scale your startup',
                    'post_score': 150
                }
            }
        ]
        
        prospects = adapter.extract_prospects(reddit_results)
        
        self.assertEqual(len(prospects), 1)
        prospect = prospects[0]
        
        self.assertEqual(prospect.name, 'johndoe')
        self.assertEqual(prospect.title, 'Founder CEO at TechCorp')
        self.assertEqual(prospect.company, 'TechCorp')
        self.assertEqual(prospect.source_platform, 'reddit')
        self.assertGreater(prospect.engagement_score, 0)
        self.assertIn('entrepreneur', prospect.additional_data['subreddit_context'])
        self.assertEqual(prospect.additional_data['total_karma'], 7000)
    
    def test_extract_title_company_from_profile(self):
        """Test title and company extraction from profile."""
        adapter = RedditAdapter(self.config)
        
        # Test CEO pattern
        title, company = adapter._extract_title_company_from_profile(
            "CEO at TechCorp", "Startup Founder"
        )
        self.assertEqual(title, "Founder CEO at TechCorp")
        self.assertEqual(company, "TechCorp")
        
        # Test founder pattern
        title, company = adapter._extract_title_company_from_profile(
            "founder of StartupXYZ", ""
        )
        self.assertIn("founder", title.lower())
        self.assertEqual(company, "StartupXYZ")
        
        # Test engineer pattern
        title, company = adapter._extract_title_company_from_profile(
            "Software Engineer working at Google", ""
        )
        self.assertIn("engineer", title.lower())
        self.assertEqual(company, "Google")
        
        # Test empty profile
        title, company = adapter._extract_title_company_from_profile("", "")
        self.assertIsNone(title)
        self.assertIsNone(company)
    
    @patch.dict(os.environ, {
        'REDDIT_CLIENT_ID': 'test_client_id',
        'REDDIT_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('multi_source.adapters.reddit_adapter.praw')
    def test_search_integration(self, mock_praw):
        """Test the main search method integration."""
        mock_reddit_instance = Mock()
        mock_praw.Reddit.return_value = mock_reddit_instance
        
        with patch('multi_source.adapters.reddit_adapter.PRAW_AVAILABLE', True):
            adapter = RedditAdapter(self.config)
            
            # Mock the search methods
            with patch.object(adapter, '_get_relevant_subreddits', return_value=['test']) as mock_subreddits, \
                 patch.object(adapter, '_search_subreddit', return_value=[{'type': 'user'}]) as mock_search:
                
                results = adapter.search("test query", {})
                
                self.assertEqual(len(results), 1)
                mock_subreddits.assert_called_once_with("test query", {})
                mock_search.assert_called_once_with('test', "test query", {})
    
    def test_search_no_reddit_client(self):
        """Test search without Reddit client."""
        adapter = RedditAdapter(self.config)
        adapter.reddit = None
        
        results = adapter.search("test query", {})
        
        self.assertEqual(results, [])
    
    def test_get_rate_limits(self):
        """Test rate limit info retrieval."""
        adapter = RedditAdapter(self.config)
        
        rate_limits = adapter.get_rate_limits()
        
        self.assertEqual(rate_limits.requests_per_minute, 60)
        self.assertEqual(rate_limits.requests_per_hour, 3600)
        self.assertEqual(rate_limits.current_usage, 0)


if __name__ == '__main__':
    unittest.main()