"""
Base interfaces for multi-source lead generation system.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import Prospect, SourceConfig, SearchStrategy, RateLimitInfo, SourceMetrics


class PlatformAdapter(ABC):
    """Base interface for all platform adapters."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.metrics = SourceMetrics()
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Handle platform authentication. Returns True if successful."""
        pass
    
    @abstractmethod
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute search with platform-specific parameters.
        
        Args:
            query: Search query string
            filters: Platform-specific filters
            
        Returns:
            List of raw results from the platform
        """
        pass
    
    @abstractmethod
    def extract_prospects(self, results: List[Dict[str, Any]]) -> List[Prospect]:
        """
        Convert platform results to standardized prospect format.
        
        Args:
            results: Raw results from platform search
            
        Returns:
            List of standardized Prospect objects
        """
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> RateLimitInfo:
        """Return current rate limit status for the platform."""
        pass
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return self.config.platform.value
    
    def is_enabled(self) -> bool:
        """Check if the platform adapter is enabled."""
        return self.config.enabled
    
    def update_metrics(self, prospects_found: int, execution_time: float, success: bool):
        """Update performance metrics for this adapter."""
        self.metrics.total_queries += 1
        if success:
            self.metrics.successful_queries += 1
        else:
            self.metrics.error_count += 1
        
        self.metrics.total_prospects += prospects_found
        self.metrics.execution_time += execution_time
        
        if self.metrics.total_prospects > 0:
            # This would be updated with actual relevance scores in real implementation
            self.metrics.average_relevance_score = 0.7  # Placeholder


class SourceSelectionEngine(ABC):
    """Interface for intelligent source selection based on ICP analysis."""
    
    @abstractmethod
    def analyze_icp_for_sources(self, icp: Dict[str, Any]) -> List[SourceConfig]:
        """
        Analyze ICP and return prioritized list of sources to use.
        
        Args:
            icp: Ideal Customer Profile data
            
        Returns:
            List of SourceConfig objects prioritized for the ICP
        """
        pass
    
    @abstractmethod
    def get_source_strategies(self, sources: List[str], icp: Dict[str, Any]) -> Dict[str, SearchStrategy]:
        """
        Return platform-specific search strategies.
        
        Args:
            sources: List of platform names to generate strategies for
            icp: Ideal Customer Profile data
            
        Returns:
            Dictionary mapping platform names to SearchStrategy objects
        """
        pass
    
    @abstractmethod
    def adjust_source_priority(self, platform: str, performance_score: float):
        """
        Dynamically adjust source priority based on performance.
        
        Args:
            platform: Platform name
            performance_score: Recent performance score (0.0 to 1.0)
        """
        pass


class DataNormalizer(ABC):
    """Interface for normalizing data from different platforms."""
    
    @abstractmethod
    def normalize_prospect_data(self, raw_data: Dict[str, Any], platform: str) -> Prospect:
        """
        Convert platform-specific data to standardized Prospect format.
        
        Args:
            raw_data: Raw prospect data from platform
            platform: Source platform name
            
        Returns:
            Standardized Prospect object
        """
        pass
    
    @abstractmethod
    def validate_prospect_data(self, prospect: Prospect) -> bool:
        """
        Validate prospect data quality and completeness.
        
        Args:
            prospect: Prospect object to validate
            
        Returns:
            True if prospect data is valid and complete enough
        """
        pass


class LeadScoringEngine(ABC):
    """Interface for scoring and ranking prospects."""
    
    @abstractmethod
    def calculate_icp_match_score(self, prospect: Prospect, icp: Dict[str, Any]) -> float:
        """Calculate how well prospect matches ICP (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def calculate_engagement_score(self, prospect: Prospect) -> float:
        """Calculate prospect engagement level (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def calculate_accessibility_score(self, prospect: Prospect) -> float:
        """Calculate likelihood of successful outreach (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def detect_buying_signals(self, prospect: Prospect) -> float:
        """Detect buying signals from prospect activity (0.0 to 1.0)."""
        pass
    
    def calculate_overall_score(self, prospect: Prospect, icp: Dict[str, Any]) -> float:
        """Calculate overall prospect score using weighted algorithm."""
        icp_score = self.calculate_icp_match_score(prospect, icp)
        engagement_score = self.calculate_engagement_score(prospect)
        accessibility_score = self.calculate_accessibility_score(prospect)
        buying_signals = self.detect_buying_signals(prospect)
        
        # Weighted scoring as per design (40%, 25%, 20%, 15%)
        overall_score = (
            icp_score * 0.40 +
            engagement_score * 0.25 +
            accessibility_score * 0.20 +
            buying_signals * 0.15
        )
        
        return min(1.0, max(0.0, overall_score))


class DeduplicationEngine(ABC):
    """Interface for deduplicating prospects from multiple sources."""
    
    @abstractmethod
    def find_duplicates(self, prospects: List[Prospect]) -> List[List[int]]:
        """
        Find duplicate prospects and return groups of indices.
        
        Args:
            prospects: List of prospects to check for duplicates
            
        Returns:
            List of lists, where each inner list contains indices of duplicate prospects
        """
        pass
    
    @abstractmethod
    def merge_prospects(self, duplicate_prospects: List[Prospect]) -> Prospect:
        """
        Merge duplicate prospects into a single consolidated prospect.
        
        Args:
            duplicate_prospects: List of duplicate prospects to merge
            
        Returns:
            Single merged Prospect object
        """
        pass
    
    def deduplicate_prospects(self, prospects: List[Prospect]) -> List[Prospect]:
        """
        Remove duplicates and return consolidated list.
        
        Args:
            prospects: List of prospects potentially containing duplicates
            
        Returns:
            Deduplicated list of prospects
        """
        duplicate_groups = self.find_duplicates(prospects)
        
        # Create a set to track which prospects have been processed
        processed_indices = set()
        deduplicated_prospects = []
        
        # Process duplicate groups
        for group in duplicate_groups:
            if not any(idx in processed_indices for idx in group):
                # Merge this group of duplicates
                duplicate_prospects = [prospects[idx] for idx in group]
                merged_prospect = self.merge_prospects(duplicate_prospects)
                deduplicated_prospects.append(merged_prospect)
                processed_indices.update(group)
        
        # Add non-duplicate prospects
        for idx, prospect in enumerate(prospects):
            if idx not in processed_indices:
                deduplicated_prospects.append(prospect)
        
        return deduplicated_prospects