"""
Unit tests for Twitter adapter.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os

from multi_source.adapters.twitter_adapter import TwitterAdapter
from multi_source.core.models import SourceConfig, SourcePlatform, Prospect


class TestTwitterAdapter(unittest.TestCase):
    """Test cases for TwitterAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = SourceConfig(
            platform=SourcePlatform.TWITTER,
            priority=8,
            max_results=50,
            rate_limit_delay=1.0,
            enabled=True
        )
        
        # Mock environment variable
        self.mock_token = "mock_bearer_token"
        
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    def test_init(self):
        """Test TwitterAdapter initialization."""
        adapter = TwitterAdapter(self.config)
        
        self.assertEqual(adapter.config, self.config)
        self.assertEqual(adapter.bearer_token, "mock_bearer_token")
        self.assertEqual(adapter.base_url, "https://api.twitter.com/2")
        self.assertIsNotNone(adapter.session)
        self.assertEqual(adapter.rate_limit_info.requests_per_minute, 300)
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    @patch('requests.Session.get')
    def test_authenticate_success(self, mock_get):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        adapter = TwitterAdapter(self.config)
        result = adapter.authenticate()
        
        self.assertTrue(result)
        mock_get.assert_called_once_with("https://api.twitter.com/2/users/me")
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    @patch('requests.Session.get')
    def test_authenticate_failure(self, mock_get):
        """Test authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        adapter = TwitterAdapter(self.config)
        result = adapter.authenticate()
        
        self.assertFalse(result)
    
    @patch.dict(os.environ, {})
    def test_authenticate_no_token(self):
        """Test authentication without bearer token."""
        adapter = TwitterAdapter(self.config)
        result = adapter.authenticate()
        
        self.assertFalse(result)
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    @patch('time.sleep')
    @patch('time.time')
    def test_rate_limiting(self, mock_time, mock_sleep):
        """Test rate limiting functionality."""
        mock_time.side_effect = [0, 0.5, 1.0]  # Simulate time progression
        
        adapter = TwitterAdapter(self.config)
        adapter.last_request_time = 0
        adapter.rate_limit_info.delay_seconds = 1.0
        
        adapter._handle_rate_limiting()
        
        mock_sleep.assert_called_once_with(1.0)  # Should sleep for remaining time
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    @patch('requests.Session.get')
    @patch('time.time')
    def test_make_request_success(self, mock_time, mock_get):
        """Test successful API request."""
        mock_time.return_value = 1000
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response
        
        adapter = TwitterAdapter(self.config)
        result = adapter._make_request("test/endpoint", {'param': 'value'})
        
        self.assertEqual(result, {'data': 'test'})
        mock_get.assert_called_once_with(
            "https://api.twitter.com/2/test/endpoint",
            params={'param': 'value'}
        )
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    @patch('requests.Session.get')
    @patch('time.time')
    def test_make_request_rate_limit(self, mock_time, mock_get):
        """Test API request with rate limit response."""
        mock_time.return_value = 1000
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'x-rate-limit-reset': '1234567890'}
        mock_get.return_value = mock_response
        
        adapter = TwitterAdapter(self.config)
        result = adapter._make_request("test/endpoint", {})
        
        self.assertIsNone(result)
        self.assertIsNotNone(adapter.rate_limit_info.reset_time)
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    def test_search_tweets(self):
        """Test tweet search functionality."""
        adapter = TwitterAdapter(self.config)
        
        # Mock the _make_request method
        mock_response = {
            'data': [
                {
                    'id': '123',
                    'text': 'Test tweet',
                    'author_id': 'user123',
                    'created_at': '2023-01-01T12:00:00.000Z'
                }
            ],
            'includes': {
                'users': [
                    {
                        'id': 'user123',
                        'name': 'Test User',
                        'username': 'testuser',
                        'description': 'CEO at TestCorp',
                        'public_metrics': {
                            'followers_count': 1000,
                            'following_count': 500,
                            'tweet_count': 2000
                        }
                    }
                ]
            }
        }
        
        with patch.object(adapter, '_make_request', return_value=mock_response):
            results = adapter._search_tweets("test query", {})
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['type'], 'tweet_author')
        self.assertEqual(results[0]['user']['name'], 'Test User')
        self.assertEqual(results[0]['tweet']['text'], 'Test tweet')
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    def test_extract_prospects(self):
        """Test prospect extraction from Twitter data."""
        adapter = TwitterAdapter(self.config)
        
        twitter_results = [
            {
                'type': 'tweet_author',
                'user': {
                    'name': 'John Doe',
                    'username': 'johndoe',
                    'description': 'CEO at TechCorp | Building the future',
                    'location': 'San Francisco, CA',
                    'url': 'https://techcorp.com',
                    'verified': True,
                    'public_metrics': {
                        'followers_count': 5000,
                        'following_count': 1000,
                        'tweet_count': 3000
                    }
                },
                'tweet': {
                    'text': 'Excited about our new product launch!',
                    'created_at': '2023-01-01T12:00:00.000Z'
                },
                'source_url': 'https://twitter.com/johndoe/status/123'
            }
        ]
        
        prospects = adapter.extract_prospects(twitter_results)
        
        self.assertEqual(len(prospects), 1)
        prospect = prospects[0]
        
        self.assertEqual(prospect.name, 'John Doe')
        self.assertEqual(prospect.title, 'CEO at TechCorp')
        self.assertEqual(prospect.company, 'TechCorp | Building')
        self.assertEqual(prospect.twitter_url, 'https://twitter.com/johndoe')
        self.assertEqual(prospect.website, 'https://techcorp.com')
        self.assertEqual(prospect.location, 'San Francisco, CA')
        self.assertEqual(prospect.source_platform, 'twitter')
        self.assertGreater(prospect.engagement_score, 0)
        self.assertIsNotNone(prospect.last_activity)
        self.assertTrue(prospect.additional_data['verified'])
    
    def test_extract_title_company_from_bio(self):
        """Test title and company extraction from bio."""
        adapter = TwitterAdapter(self.config)
        
        # Test CEO pattern
        title, company = adapter._extract_title_company_from_bio("CEO at TechCorp")
        self.assertEqual(title, "CEO at TechCorp")
        self.assertEqual(company, "TechCorp")
        
        # Test founder pattern
        title, company = adapter._extract_title_company_from_bio("Founder of StartupXYZ | Building the future")
        self.assertIn("Founder", title)
        self.assertEqual(company, "StartupXYZ | Building")
        
        # Test @ pattern
        title, company = adapter._extract_title_company_from_bio("Software Engineer @Google")
        self.assertEqual(company, "Google")
        
        # Test empty bio
        title, company = adapter._extract_title_company_from_bio("")
        self.assertIsNone(title)
        self.assertIsNone(company)
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    def test_search_integration(self):
        """Test the main search method integration."""
        adapter = TwitterAdapter(self.config)
        
        # Mock both search methods
        with patch.object(adapter, '_search_tweets', return_value=[{'type': 'tweet'}]) as mock_tweets, \
             patch.object(adapter, '_search_users', return_value=[{'type': 'user'}]) as mock_users:
            
            results = adapter.search("test query", {'max_results': 25})
            
            self.assertEqual(len(results), 2)
            mock_tweets.assert_called_once_with("test query", {'max_results': 25})
            mock_users.assert_called_once_with("test query", {'max_results': 25})
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': 'mock_bearer_token'})
    def test_get_rate_limits(self):
        """Test rate limit info retrieval."""
        adapter = TwitterAdapter(self.config)
        
        rate_limits = adapter.get_rate_limits()
        
        self.assertEqual(rate_limits.requests_per_minute, 300)
        self.assertEqual(rate_limits.requests_per_hour, 300)
        self.assertEqual(rate_limits.current_usage, 0)


if __name__ == '__main__':
    unittest.main()