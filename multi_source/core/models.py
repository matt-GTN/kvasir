"""
Core data models for multi-source lead generation system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SourcePlatform(Enum):
    """Enumeration of supported lead generation platforms."""
    TWITTER = "twitter"
    REDDIT = "reddit"
    GITHUB = "github"
    YOUTUBE = "youtube"
    STACK_OVERFLOW = "stack_overflow"
    HACKER_NEWS = "hacker_news"
    DISCORD = "discord"
    MEDIUM = "medium"
    SUBSTACK = "substack"
    PRODUCT_HUNT = "product_hunt"
    CRUNCHBASE = "crunchbase"
    ANGELLIST = "angellist"
    JOB_BOARDS = "job_boards"
    EVENTBRITE = "eventbrite"
    MEETUP = "meetup"
    GOOGLE_SEARCH = "google_search"  # Existing platform


@dataclass
class Prospect:
    """Standardized prospect data model with multi-source support."""
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    source_platform: str = ""
    source_url: str = ""
    engagement_score: float = 0.0
    relevance_score: float = 0.0
    last_activity: Optional[datetime] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prospect to dictionary format."""
        return {
            'name': self.name,
            'title': self.title,
            'company': self.company,
            'email': self.email,
            'linkedin_url': self.linkedin_url,
            'twitter_url': self.twitter_url,
            'github_url': self.github_url,
            'website': self.website,
            'bio': self.bio,
            'location': self.location,
            'industry': self.industry,
            'source_platform': self.source_platform,
            'source_url': self.source_url,
            'engagement_score': self.engagement_score,
            'relevance_score': self.relevance_score,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'additional_data': self.additional_data
        }


@dataclass
class SourceConfig:
    """Configuration for a specific lead generation source."""
    platform: SourcePlatform
    priority: int  # 1-10, higher is more important
    max_results: int
    search_parameters: Dict[str, Any] = field(default_factory=dict)
    rate_limit_delay: float = 1.0
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert source config to dictionary format."""
        return {
            'platform': self.platform.value,
            'priority': self.priority,
            'max_results': self.max_results,
            'search_parameters': self.search_parameters,
            'rate_limit_delay': self.rate_limit_delay,
            'enabled': self.enabled
        }


@dataclass
class SearchStrategy:
    """Search strategy for a specific platform."""
    primary_queries: List[str]
    fallback_queries: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    result_limit: int = 50
    quality_threshold: float = 0.5


@dataclass
class SourceMetrics:
    """Performance metrics for a source platform."""
    total_queries: int = 0
    successful_queries: int = 0
    total_prospects: int = 0
    average_relevance_score: float = 0.0
    execution_time: float = 0.0
    error_count: int = 0
    last_updated: Optional[datetime] = None


@dataclass
class MultiSourceResult:
    """Result from multi-source lead generation."""
    prospects: List[Prospect]
    source_performance: Dict[str, SourceMetrics]
    total_execution_time: float
    successful_sources: List[str]
    failed_sources: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            'prospects': [p.to_dict() for p in self.prospects],
            'source_performance': {k: v.__dict__ for k, v in self.source_performance.items()},
            'total_execution_time': self.total_execution_time,
            'successful_sources': self.successful_sources,
            'failed_sources': self.failed_sources
        }


@dataclass
class RateLimitInfo:
    """Rate limiting information for a platform."""
    requests_per_minute: int
    requests_per_hour: int
    current_usage: int
    reset_time: Optional[datetime] = None
    delay_seconds: float = 1.0