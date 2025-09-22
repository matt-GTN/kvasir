"""
Intelligent source selection engine that analyzes ICP to determine optimal platforms.
"""
from typing import Dict, List, Any, Set
from .interfaces import SourceSelectionEngine
from .models import SourceConfig, SearchStrategy, SourcePlatform


class IntelligentSourceSelector(SourceSelectionEngine):
    """
    Analyzes ICP characteristics to automatically select and prioritize 
    the most relevant lead generation sources.
    """
    
    def __init__(self):
        self.platform_performance = {}  # Track performance for dynamic adjustment
        self._initialize_platform_mappings()
    
    def _initialize_platform_mappings(self):
        """Initialize mappings between ICP characteristics and optimal platforms."""
        
        # Industry-specific platform preferences
        self.industry_platforms = {
            'technology': [
                SourcePlatform.GITHUB, SourcePlatform.STACK_OVERFLOW, 
                SourcePlatform.HACKER_NEWS, SourcePlatform.TWITTER,
                SourcePlatform.PRODUCT_HUNT
            ],
            'software': [
                SourcePlatform.GITHUB, SourcePlatform.STACK_OVERFLOW,
                SourcePlatform.TWITTER, SourcePlatform.PRODUCT_HUNT,
                SourcePlatform.HACKER_NEWS
            ],
            'saas': [
                SourcePlatform.TWITTER, SourcePlatform.PRODUCT_HUNT,
                SourcePlatform.CRUNCHBASE, SourcePlatform.HACKER_NEWS,
                SourcePlatform.GITHUB
            ],
            'ecommerce': [
                SourcePlatform.TWITTER, SourcePlatform.REDDIT,
                SourcePlatform.YOUTUBE, SourcePlatform.CRUNCHBASE
            ],
            'healthcare': [
                SourcePlatform.TWITTER, SourcePlatform.MEDIUM,
                SourcePlatform.EVENTBRITE, SourcePlatform.MEETUP
            ],
            'finance': [
                SourcePlatform.TWITTER, SourcePlatform.MEDIUM,
                SourcePlatform.HACKER_NEWS, SourcePlatform.CRUNCHBASE
            ],
            'marketing': [
                SourcePlatform.TWITTER, SourcePlatform.MEDIUM,
                SourcePlatform.YOUTUBE, SourcePlatform.PRODUCT_HUNT
            ],
            'consulting': [
                SourcePlatform.TWITTER, SourcePlatform.MEDIUM,
                SourcePlatform.EVENTBRITE, SourcePlatform.MEETUP
            ]
        }
        
        # Role-specific platform preferences
        self.role_platforms = {
            'developer': [
                SourcePlatform.GITHUB, SourcePlatform.STACK_OVERFLOW,
                SourcePlatform.HACKER_NEWS, SourcePlatform.TWITTER
            ],
            'engineer': [
                SourcePlatform.GITHUB, SourcePlatform.STACK_OVERFLOW,
                SourcePlatform.TWITTER, SourcePlatform.HACKER_NEWS
            ],
            'founder': [
                SourcePlatform.TWITTER, SourcePlatform.CRUNCHBASE,
                SourcePlatform.PRODUCT_HUNT, SourcePlatform.HACKER_NEWS
            ],
            'cto': [
                SourcePlatform.TWITTER, SourcePlatform.GITHUB,
                SourcePlatform.HACKER_NEWS, SourcePlatform.STACK_OVERFLOW
            ],
            'marketing': [
                SourcePlatform.TWITTER, SourcePlatform.MEDIUM,
                SourcePlatform.YOUTUBE, SourcePlatform.PRODUCT_HUNT
            ],
            'sales': [
                SourcePlatform.TWITTER, SourcePlatform.CRUNCHBASE,
                SourcePlatform.EVENTBRITE, SourcePlatform.MEETUP
            ]
        }
        
        # Company size preferences
        self.company_size_platforms = {
            'startup': [
                SourcePlatform.CRUNCHBASE, SourcePlatform.ANGELLIST,
                SourcePlatform.PRODUCT_HUNT, SourcePlatform.HACKER_NEWS,
                SourcePlatform.TWITTER
            ],
            'small': [
                SourcePlatform.TWITTER, SourcePlatform.MEETUP,
                SourcePlatform.EVENTBRITE, SourcePlatform.CRUNCHBASE
            ],
            'enterprise': [
                SourcePlatform.TWITTER, SourcePlatform.EVENTBRITE,
                SourcePlatform.CRUNCHBASE, SourcePlatform.JOB_BOARDS
            ]
        }
    
    def analyze_icp_for_sources(self, icp: Dict[str, Any]) -> List[SourceConfig]:
        """
        Analyze ICP and return prioritized list of sources to use.
        
        Requirements: 8.1, 8.2 - Automatically determine relevant lead sources
        """
        platform_scores = {}
        
        # Extract ICP characteristics
        industry = self._extract_industry(icp)
        roles = self._extract_roles(icp)
        company_size = self._extract_company_size(icp)
        
        # Score platforms based on industry match
        if industry:
            industry_platforms = self.industry_platforms.get(industry.lower(), [])
            for platform in industry_platforms:
                platform_scores[platform] = platform_scores.get(platform, 0) + 3
        
        # Score platforms based on role match
        for role in roles:
            role_platforms = self.role_platforms.get(role.lower(), [])
            for platform in role_platforms:
                platform_scores[platform] = platform_scores.get(platform, 0) + 2
        
        # Score platforms based on company size
        if company_size:
            size_platforms = self.company_size_platforms.get(company_size.lower(), [])
            for platform in size_platforms:
                platform_scores[platform] = platform_scores.get(platform, 0) + 1
        
        # Always include Google Search as baseline
        platform_scores[SourcePlatform.GOOGLE_SEARCH] = platform_scores.get(SourcePlatform.GOOGLE_SEARCH, 0) + 2
        
        # Apply performance adjustments
        for platform in platform_scores:
            performance_multiplier = self.platform_performance.get(platform.value, 1.0)
            platform_scores[platform] *= performance_multiplier
        
        # Convert scores to SourceConfig objects
        source_configs = []
        for platform, score in sorted(platform_scores.items(), key=lambda x: x[1], reverse=True):
            priority = min(10, max(1, int(score)))
            max_results = self._get_max_results_for_platform(platform)
            rate_limit_delay = self._get_rate_limit_delay(platform)
            
            config = SourceConfig(
                platform=platform,
                priority=priority,
                max_results=max_results,
                rate_limit_delay=rate_limit_delay,
                enabled=True
            )
            source_configs.append(config)
        
        # Limit to top 8 sources to avoid overwhelming the system
        return source_configs[:8]
    
    def get_source_strategies(self, sources: List[str], icp: Dict[str, Any]) -> Dict[str, SearchStrategy]:
        """
        Return platform-specific search strategies.
        
        Requirements: 8.1 - Platform-specific search strategies
        """
        strategies = {}
        
        # Extract key terms from ICP for query generation
        industry_terms = self._extract_industry_terms(icp)
        role_terms = self._extract_role_terms(icp)
        company_terms = self._extract_company_terms(icp)
        
        for source in sources:
            if source == 'twitter':
                strategies[source] = self._create_twitter_strategy(industry_terms, role_terms)
            elif source == 'github':
                strategies[source] = self._create_github_strategy(industry_terms, role_terms)
            elif source == 'reddit':
                strategies[source] = self._create_reddit_strategy(industry_terms, role_terms)
            elif source == 'stack_overflow':
                strategies[source] = self._create_stackoverflow_strategy(industry_terms, role_terms)
            elif source == 'product_hunt':
                strategies[source] = self._create_producthunt_strategy(industry_terms, role_terms)
            elif source == 'crunchbase':
                strategies[source] = self._create_crunchbase_strategy(industry_terms, company_terms)
            elif source == 'google_search':
                strategies[source] = self._create_google_strategy(industry_terms, role_terms, company_terms)
            else:
                # Default strategy
                strategies[source] = SearchStrategy(
                    primary_queries=industry_terms + role_terms,
                    fallback_queries=industry_terms,
                    result_limit=50
                )
        
        return strategies
    
    def adjust_source_priority(self, platform: str, performance_score: float):
        """
        Dynamically adjust source priority based on performance.
        
        Requirements: 8.4 - Automatic deprioritization of poor-performing sources
        """
        # Update performance tracking
        current_performance = self.platform_performance.get(platform, 1.0)
        
        # Use exponential moving average to smooth performance changes
        alpha = 0.3  # Learning rate
        new_performance = alpha * performance_score + (1 - alpha) * current_performance
        
        self.platform_performance[platform] = new_performance
        
        print(f"Updated performance for {platform}: {new_performance:.3f}")
    
    def _extract_industry(self, icp: Dict[str, Any]) -> str:
        """Extract primary industry from ICP."""
        # Look for industry in various possible fields
        for field in ['industry', 'sector', 'vertical', 'market']:
            if field in icp and icp[field]:
                return str(icp[field]).lower()
        
        # Try to infer from description or other fields
        description = icp.get('description', '').lower()
        if 'software' in description or 'saas' in description:
            return 'software'
        elif 'tech' in description:
            return 'technology'
        elif 'ecommerce' in description or 'e-commerce' in description:
            return 'ecommerce'
        
        return ''
    
    def _extract_roles(self, icp: Dict[str, Any]) -> List[str]:
        """Extract target roles from ICP."""
        roles = []
        
        # Look for roles in various fields
        for field in ['roles', 'titles', 'job_titles', 'target_roles']:
            if field in icp and icp[field]:
                if isinstance(icp[field], list):
                    roles.extend([str(role).lower() for role in icp[field]])
                else:
                    roles.append(str(icp[field]).lower())
        
        # Try to infer from description
        description = icp.get('description', '').lower()
        if 'developer' in description or 'engineer' in description:
            roles.append('developer')
        if 'founder' in description or 'ceo' in description:
            roles.append('founder')
        if 'cto' in description:
            roles.append('cto')
        
        return list(set(roles))  # Remove duplicates
    
    def _extract_company_size(self, icp: Dict[str, Any]) -> str:
        """Extract company size preference from ICP."""
        size_field = icp.get('company_size', '').lower()
        if size_field:
            if 'startup' in size_field or 'early' in size_field:
                return 'startup'
            elif 'small' in size_field or 'medium' in size_field:
                return 'small'
            elif 'enterprise' in size_field or 'large' in size_field:
                return 'enterprise'
        
        return ''
    
    def _extract_industry_terms(self, icp: Dict[str, Any]) -> List[str]:
        """Extract industry-related search terms."""
        terms = []
        industry = self._extract_industry(icp)
        if industry:
            terms.append(industry)
            
            # Add related terms
            if industry == 'technology':
                terms.extend(['tech', 'software', 'digital'])
            elif industry == 'saas':
                terms.extend(['software', 'cloud', 'platform'])
            elif industry == 'ecommerce':
                terms.extend(['retail', 'online', 'marketplace'])
        
        return terms
    
    def _extract_role_terms(self, icp: Dict[str, Any]) -> List[str]:
        """Extract role-related search terms."""
        roles = self._extract_roles(icp)
        terms = []
        
        for role in roles:
            terms.append(role)
            if role == 'developer':
                terms.extend(['engineer', 'programmer', 'dev'])
            elif role == 'founder':
                terms.extend(['ceo', 'entrepreneur', 'startup'])
        
        return terms
    
    def _extract_company_terms(self, icp: Dict[str, Any]) -> List[str]:
        """Extract company-related search terms."""
        terms = []
        company_size = self._extract_company_size(icp)
        
        if company_size == 'startup':
            terms.extend(['startup', 'early-stage', 'seed'])
        elif company_size == 'enterprise':
            terms.extend(['enterprise', 'corporation', 'large'])
        
        return terms
    
    def _get_max_results_for_platform(self, platform: SourcePlatform) -> int:
        """Get appropriate max results for each platform."""
        platform_limits = {
            SourcePlatform.TWITTER: 100,
            SourcePlatform.GITHUB: 50,
            SourcePlatform.REDDIT: 75,
            SourcePlatform.STACK_OVERFLOW: 50,
            SourcePlatform.PRODUCT_HUNT: 30,
            SourcePlatform.CRUNCHBASE: 25,
            SourcePlatform.GOOGLE_SEARCH: 50
        }
        return platform_limits.get(platform, 50)
    
    def _get_rate_limit_delay(self, platform: SourcePlatform) -> float:
        """Get appropriate rate limit delay for each platform."""
        platform_delays = {
            SourcePlatform.TWITTER: 2.0,
            SourcePlatform.GITHUB: 1.0,
            SourcePlatform.REDDIT: 1.5,
            SourcePlatform.STACK_OVERFLOW: 1.0,
            SourcePlatform.PRODUCT_HUNT: 1.5,
            SourcePlatform.CRUNCHBASE: 3.0,
            SourcePlatform.GOOGLE_SEARCH: 1.0
        }
        return platform_delays.get(platform, 1.0)
    
    # Platform-specific strategy creation methods
    def _create_twitter_strategy(self, industry_terms: List[str], role_terms: List[str]) -> SearchStrategy:
        """Create Twitter-specific search strategy."""
        primary_queries = []
        for role in role_terms[:3]:  # Limit to top 3 roles
            for industry in industry_terms[:2]:  # Limit to top 2 industries
                primary_queries.append(f"{role} {industry}")
        
        fallback_queries = industry_terms + role_terms
        
        return SearchStrategy(
            primary_queries=primary_queries,
            fallback_queries=fallback_queries,
            filters={'verified': True, 'min_followers': 100},
            result_limit=100
        )
    
    def _create_github_strategy(self, industry_terms: List[str], role_terms: List[str]) -> SearchStrategy:
        """Create GitHub-specific search strategy."""
        primary_queries = []
        for industry in industry_terms:
            primary_queries.append(f"language:{industry}")
            primary_queries.append(f"topic:{industry}")
        
        return SearchStrategy(
            primary_queries=primary_queries,
            fallback_queries=role_terms,
            filters={'sort': 'stars', 'order': 'desc'},
            result_limit=50
        )
    
    def _create_reddit_strategy(self, industry_terms: List[str], role_terms: List[str]) -> SearchStrategy:
        """Create Reddit-specific search strategy."""
        primary_queries = []
        for term in industry_terms + role_terms:
            primary_queries.append(f"subreddit:{term}")
        
        return SearchStrategy(
            primary_queries=primary_queries,
            fallback_queries=industry_terms,
            filters={'sort': 'hot', 'time': 'month'},
            result_limit=75
        )
    
    def _create_stackoverflow_strategy(self, industry_terms: List[str], role_terms: List[str]) -> SearchStrategy:
        """Create Stack Overflow-specific search strategy."""
        primary_queries = []
        for term in industry_terms:
            primary_queries.append(f"[{term}]")
        
        return SearchStrategy(
            primary_queries=primary_queries,
            fallback_queries=role_terms,
            filters={'sort': 'votes', 'min_reputation': 1000},
            result_limit=50
        )
    
    def _create_producthunt_strategy(self, industry_terms: List[str], role_terms: List[str]) -> SearchStrategy:
        """Create Product Hunt-specific search strategy."""
        return SearchStrategy(
            primary_queries=industry_terms,
            fallback_queries=role_terms,
            filters={'featured': True},
            result_limit=30
        )
    
    def _create_crunchbase_strategy(self, industry_terms: List[str], company_terms: List[str]) -> SearchStrategy:
        """Create Crunchbase-specific search strategy."""
        primary_queries = []
        for industry in industry_terms:
            for size in company_terms:
                primary_queries.append(f"{industry} {size}")
        
        return SearchStrategy(
            primary_queries=primary_queries,
            fallback_queries=industry_terms,
            filters={'funding_stage': 'seed,series-a,series-b'},
            result_limit=25
        )
    
    def _create_google_strategy(self, industry_terms: List[str], role_terms: List[str], company_terms: List[str]) -> SearchStrategy:
        """Create Google Search-specific strategy."""
        primary_queries = []
        for role in role_terms[:2]:
            for industry in industry_terms[:2]:
                primary_queries.append(f'"{role}" "{industry}" site:linkedin.com')
        
        fallback_queries = [f'"{term}" site:linkedin.com' for term in industry_terms + role_terms]
        
        return SearchStrategy(
            primary_queries=primary_queries,
            fallback_queries=fallback_queries,
            result_limit=50
        )