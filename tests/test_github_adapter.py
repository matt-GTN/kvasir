"""
Unit tests for GitHub adapter.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os

from multi_source.adapters.github_adapter import GitHubAdapter
from multi_source.core.models import SourceConfig, SourcePlatform, Prospect


class TestGitHubAdapter(unittest.TestCase):
    """Test cases for GitHubAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = SourceConfig(
            platform=SourcePlatform.GITHUB,
            priority=9,
            max_results=50,
            rate_limit_delay=1.0,
            enabled=True
        )
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token'})
    def test_init_with_token(self):
        """Test GitHubAdapter initialization with token."""
        adapter = GitHubAdapter(self.config)
        
        self.assertEqual(adapter.config, self.config)
        self.assertEqual(adapter.token, "test_token")
        self.assertEqual(adapter.base_url, "https://api.github.com")
        self.assertEqual(adapter.rate_limit_info.requests_per_minute, 60)
        self.assertEqual(adapter.rate_limit_info.requests_per_hour, 5000)
        self.assertIn('Authorization', adapter.session.headers)
    
    @patch.dict(os.environ, {})
    def test_init_without_token(self):
        """Test GitHubAdapter initialization without token."""
        adapter = GitHubAdapter(self.config)
        
        self.assertIsNone(adapter.token)
        self.assertEqual(adapter.rate_limit_info.requests_per_minute, 10)
        self.assertEqual(adapter.rate_limit_info.requests_per_hour, 60)
        self.assertNotIn('Authorization', adapter.session.headers)
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token'})
    @patch('requests.Session.get')
    def test_authenticate_success_with_token(self, mock_get):
        """Test successful authentication with token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        adapter = GitHubAdapter(self.config)
        result = adapter.authenticate()
        
        self.assertTrue(result)
        mock_get.assert_called_once_with("https://api.github.com/user")
    
    @patch.dict(os.environ, {})
    @patch('requests.Session.get')
    def test_authenticate_success_without_token(self, mock_get):
        """Test successful authentication without token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        adapter = GitHubAdapter(self.config)
        result = adapter.authenticate()
        
        self.assertTrue(result)
        mock_get.assert_called_once_with("https://api.github.com/rate_limit")
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token'})
    @patch('requests.Session.get')
    def test_authenticate_failure(self, mock_get):
        """Test authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        adapter = GitHubAdapter(self.config)
        result = adapter.authenticate()
        
        self.assertFalse(result)
    
    @patch('time.sleep')
    @patch('time.time')
    def test_rate_limiting(self, mock_time, mock_sleep):
        """Test rate limiting functionality."""
        mock_time.side_effect = [0, 0.5, 1.0]
        
        adapter = GitHubAdapter(self.config)
        adapter.last_request_time = 0
        adapter.rate_limit_info.delay_seconds = 1.0
        
        adapter._handle_rate_limiting()
        
        mock_sleep.assert_called_once_with(0.5)
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token'})
    @patch('requests.Session.get')
    @patch('time.time')
    def test_make_request_success(self, mock_time, mock_get):
        """Test successful API request."""
        mock_time.return_value = 1000
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {
            'X-RateLimit-Remaining': '4999',
            'X-RateLimit-Reset': '1234567890'
        }
        mock_get.return_value = mock_response
        
        adapter = GitHubAdapter(self.config)
        result = adapter._make_request("test/endpoint", {'param': 'value'})
        
        self.assertEqual(result, {'data': 'test'})
        mock_get.assert_called_once_with(
            "https://api.github.com/test/endpoint",
            params={'param': 'value'}
        )
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token'})
    @patch('requests.Session.get')
    @patch('time.time')
    def test_make_request_rate_limit(self, mock_time, mock_get):
        """Test API request with rate limit response."""
        mock_time.return_value = 1000
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        adapter = GitHubAdapter(self.config)
        result = adapter._make_request("test/endpoint", {})
        
        self.assertIsNone(result)
    
    def test_get_user_details(self):
        """Test user details retrieval."""
        adapter = GitHubAdapter(self.config)
        
        mock_response = {
            'login': 'testuser',
            'name': 'Test User',
            'email': 'test@example.com',
            'bio': 'Software Engineer at TechCorp',
            'company': '@TechCorp',
            'location': 'San Francisco, CA',
            'blog': 'https://testuser.dev',
            'twitter_username': 'testuser',
            'public_repos': 50,
            'followers': 1000,
            'following': 500,
            'created_at': '2020-01-01T00:00:00Z',
            'updated_at': '2023-01-01T00:00:00Z',
            'html_url': 'https://github.com/testuser',
            'avatar_url': 'https://avatars.githubusercontent.com/u/123',
            'hireable': True
        }
        
        with patch.object(adapter, '_make_request', return_value=mock_response):
            result = adapter._get_user_details('testuser')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['username'], 'testuser')
        self.assertEqual(result['name'], 'Test User')
        self.assertEqual(result['email'], 'test@example.com')
        self.assertEqual(result['company'], '@TechCorp')
        self.assertTrue(result['hireable'])
    
    def test_search_repositories(self):
        """Test repository search functionality."""
        adapter = GitHubAdapter(self.config)
        
        mock_search_response = {
            'items': [
                {
                    'full_name': 'testuser/testrepo',
                    'name': 'testrepo',
                    'html_url': 'https://github.com/testuser/testrepo',
                    'description': 'A test repository',
                    'stargazers_count': 100,
                    'language': 'Python',
                    'owner': {
                        'login': 'testuser'
                    }
                }
            ]
        }
        
        mock_contributors = [
            {
                'username': 'contributor1',
                'name': 'Contributor One',
                'contributions': 50
            }
        ]
        
        mock_owner = {
            'username': 'testuser',
            'name': 'Test User'
        }
        
        with patch.object(adapter, '_make_request', return_value=mock_search_response) as mock_request, \
             patch.object(adapter, '_get_repository_contributors', return_value=mock_contributors) as mock_contrib, \
             patch.object(adapter, '_get_user_details', return_value=mock_owner) as mock_user:
            
            results = adapter._search_repositories("test query", {})
        
        self.assertEqual(len(results), 2)  # 1 contributor + 1 owner
        mock_contrib.assert_called_once_with('testuser', 'testrepo', 5)
        mock_user.assert_called_once_with('testuser')
    
    def test_search_users(self):
        """Test user search functionality."""
        adapter = GitHubAdapter(self.config)
        
        mock_search_response = {
            'items': [
                {
                    'login': 'testuser1'
                },
                {
                    'login': 'testuser2'
                }
            ]
        }
        
        mock_user_details = {
            'username': 'testuser1',
            'name': 'Test User 1'
        }
        
        with patch.object(adapter, '_make_request', return_value=mock_search_response), \
             patch.object(adapter, '_get_user_details', return_value=mock_user_details):
            
            results = adapter._search_users("test query", {})
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['search_context'], 'direct_user_search')
    
    def test_search_organizations(self):
        """Test organization search functionality."""
        adapter = GitHubAdapter(self.config)
        
        mock_search_response = {
            'items': [
                {
                    'login': 'testorg',
                    'html_url': 'https://github.com/testorg'
                }
            ]
        }
        
        mock_members = [
            {
                'username': 'member1',
                'name': 'Member One'
            }
        ]
        
        with patch.object(adapter, '_make_request', return_value=mock_search_response), \
             patch.object(adapter, '_get_organization_members', return_value=mock_members):
            
            results = adapter._search_organizations("test query", {})
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['organization_context']['org_name'], 'testorg')
    
    def test_extract_prospects(self):
        """Test prospect extraction from GitHub data."""
        adapter = GitHubAdapter(self.config)
        
        github_results = [
            {
                'username': 'johndoe',
                'name': 'John Doe',
                'email': 'john@example.com',
                'bio': 'Senior Software Engineer building awesome things',
                'company': '@TechCorp',
                'location': 'San Francisco, CA',
                'blog': 'https://johndoe.dev',
                'twitter_username': 'johndoe',
                'public_repos': 75,
                'followers': 2000,
                'following': 800,
                'created_at': '2018-01-01T00:00:00Z',
                'updated_at': '2023-01-01T12:00:00Z',
                'html_url': 'https://github.com/johndoe',
                'avatar_url': 'https://avatars.githubusercontent.com/u/123',
                'hireable': True,
                'repository_context': {
                    'repo_name': 'johndoe/awesome-project',
                    'repo_url': 'https://github.com/johndoe/awesome-project',
                    'repo_stars': 500,
                    'role': 'owner'
                }
            }
        ]
        
        prospects = adapter.extract_prospects(github_results)
        
        self.assertEqual(len(prospects), 1)
        prospect = prospects[0]
        
        self.assertEqual(prospect.name, 'John Doe')
        self.assertEqual(prospect.title, 'Senior Software Engineer')
        self.assertEqual(prospect.company, 'TechCorp')
        self.assertEqual(prospect.email, 'john@example.com')
        self.assertEqual(prospect.github_url, 'https://github.com/johndoe')
        self.assertEqual(prospect.twitter_url, 'https://twitter.com/johndoe')
        self.assertEqual(prospect.website, 'https://johndoe.dev')
        self.assertEqual(prospect.location, 'San Francisco, CA')
        self.assertEqual(prospect.source_platform, 'github')
        self.assertGreater(prospect.engagement_score, 0)
        self.assertIsNotNone(prospect.last_activity)
        self.assertTrue(prospect.additional_data['hireable'])
        self.assertEqual(prospect.additional_data['public_repos'], 75)
    
    def test_extract_title_from_bio(self):
        """Test title extraction from bio."""
        adapter = GitHubAdapter(self.config)
        
        # Test engineer pattern
        title = adapter._extract_title_from_bio("Senior Software Engineer at Google")
        self.assertIn("Software Engineer", title)
        
        # Test founder pattern
        title = adapter._extract_title_from_bio("Co-founder of StartupXYZ")
        self.assertIn("Co-founder", title)
        
        # Test developer pattern
        title = adapter._extract_title_from_bio("Full-stack developer passionate about React")
        self.assertIn("developer", title)
        
        # Test empty bio
        title = adapter._extract_title_from_bio("")
        self.assertIsNone(title)
        
        # Test bio without title keywords
        title = adapter._extract_title_from_bio("I love coding and coffee")
        self.assertIsNone(title)
    
    def test_search_integration(self):
        """Test the main search method integration."""
        adapter = GitHubAdapter(self.config)
        
        # Mock all search methods
        with patch.object(adapter, '_search_repositories', return_value=[{'type': 'repo'}]) as mock_repos, \
             patch.object(adapter, '_search_users', return_value=[{'type': 'user'}]) as mock_users, \
             patch.object(adapter, '_search_organizations', return_value=[{'type': 'org'}]) as mock_orgs:
            
            results = adapter.search("test query", {})
            
            self.assertEqual(len(results), 3)
            mock_repos.assert_called_once_with("test query", {})
            mock_users.assert_called_once_with("test query", {})
            mock_orgs.assert_called_once_with("test query", {})
    
    def test_get_repository_contributors(self):
        """Test repository contributors retrieval."""
        adapter = GitHubAdapter(self.config)
        
        mock_contributors_response = [
            {
                'login': 'contributor1',
                'contributions': 100
            },
            {
                'login': 'contributor2',
                'contributions': 50
            }
        ]
        
        mock_user_details = {
            'username': 'contributor1',
            'name': 'Contributor One'
        }
        
        with patch.object(adapter, '_make_request', return_value=mock_contributors_response), \
             patch.object(adapter, '_get_user_details', return_value=mock_user_details):
            
            contributors = adapter._get_repository_contributors('owner', 'repo', 5)
        
        self.assertEqual(len(contributors), 2)
        self.assertEqual(contributors[0]['contributions'], 100)
    
    def test_get_organization_members(self):
        """Test organization members retrieval."""
        adapter = GitHubAdapter(self.config)
        
        mock_members_response = [
            {
                'login': 'member1'
            },
            {
                'login': 'member2'
            }
        ]
        
        mock_user_details = {
            'username': 'member1',
            'name': 'Member One'
        }
        
        with patch.object(adapter, '_make_request', return_value=mock_members_response), \
             patch.object(adapter, '_get_user_details', return_value=mock_user_details):
            
            members = adapter._get_organization_members('testorg', 10)
        
        self.assertEqual(len(members), 2)
    
    def test_get_rate_limits(self):
        """Test rate limit info retrieval."""
        adapter = GitHubAdapter(self.config)
        
        rate_limits = adapter.get_rate_limits()
        
        self.assertIsInstance(rate_limits.requests_per_minute, int)
        self.assertIsInstance(rate_limits.requests_per_hour, int)
        self.assertEqual(rate_limits.current_usage, 0)


if __name__ == '__main__':
    unittest.main()