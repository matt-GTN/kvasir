"""
Multi-source lead generation system.

This package provides infrastructure for discovering leads across multiple platforms
including social media, professional communities, content platforms, business directories,
and event platforms.
"""
from .core import (
    Prospect, SourceConfig, SearchStrategy, SourceMetrics, 
    MultiSourceResult, RateLimitInfo, SourcePlatform,
    PlatformAdapter, SourceSelectionEngine, DataNormalizer,
    LeadScoringEngine, DeduplicationEngine, IntelligentSourceSelector
)
from .config import SourceConfigManager, config_manager

__version__ = "1.0.0"

__all__ = [
    # Core models
    'Prospect',
    'SourceConfig', 
    'SearchStrategy',
    'SourceMetrics',
    'MultiSourceResult',
    'RateLimitInfo',
    'SourcePlatform',
    
    # Core interfaces
    'PlatformAdapter',
    'SourceSelectionEngine',
    'DataNormalizer',
    'LeadScoringEngine', 
    'DeduplicationEngine',
    
    # Implementations
    'IntelligentSourceSelector',
    
    # Configuration
    'SourceConfigManager',
    'config_manager'
]