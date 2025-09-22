"""
Platform adapters for multi-source lead generation.
"""
from .twitter_adapter import TwitterAdapter
from .reddit_adapter import RedditAdapter
from .github_adapter import GitHubAdapter

__all__ = ['TwitterAdapter', 'RedditAdapter', 'GitHubAdapter']