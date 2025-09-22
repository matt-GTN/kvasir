"""
Test script to verify the core multi-source infrastructure.
"""
import json
from multi_source import (
    IntelligentSourceSelector, SourcePlatform, Prospect, 
    config_manager
)


def test_source_selection():
    """Test the intelligent source selection engine."""
    print("=== Testing Source Selection Engine ===")
    
    # Create a sample ICP for a SaaS company targeting developers
    sample_icp = {
        "industry": "technology",
        "roles": ["developer", "engineer", "cto"],
        "company_size": "startup",
        "description": "AI-powered development tools for software engineers"
    }
    
    # Initialize source selector
    selector = IntelligentSourceSelector()
    
    # Test source analysis
    print("\n1. Analyzing ICP for optimal sources...")
    source_configs = selector.analyze_icp_for_sources(sample_icp)
    
    print(f"Selected {len(source_configs)} sources:")
    for config in source_configs:
        print(f"  - {config.platform.value}: priority={config.priority}, max_results={config.max_results}")
    
    # Test strategy generation
    print("\n2. Generating search strategies...")
    source_names = [config.platform.value for config in source_configs[:5]]  # Top 5
    strategies = selector.get_source_strategies(source_names, sample_icp)
    
    for platform, strategy in strategies.items():
        print(f"\n{platform.upper()} Strategy:")
        print(f"  Primary queries: {strategy.primary_queries[:3]}...")  # Show first 3
        print(f"  Result limit: {strategy.result_limit}")
        if strategy.filters:
            print(f"  Filters: {strategy.filters}")


def test_prospect_model():
    """Test the standardized prospect data model."""
    print("\n=== Testing Prospect Data Model ===")
    
    # Create a sample prospect
    prospect = Prospect(
        name="John Smith",
        title="Senior Software Engineer",
        company="TechCorp Inc",
        email="john.smith@techcorp.com",
        linkedin_url="https://linkedin.com/in/johnsmith",
        github_url="https://github.com/johnsmith",
        bio="Full-stack developer with 8 years experience in Python and React",
        location="San Francisco, CA",
        industry="technology",
        source_platform="github",
        source_url="https://github.com/johnsmith",
        engagement_score=0.8,
        relevance_score=0.9,
        additional_data={"repositories": 25, "followers": 150}
    )
    
    print("Created prospect:")
    print(f"  Name: {prospect.name}")
    print(f"  Title: {prospect.title}")
    print(f"  Company: {prospect.company}")
    print(f"  Source: {prospect.source_platform}")
    print(f"  Engagement Score: {prospect.engagement_score}")
    print(f"  Relevance Score: {prospect.relevance_score}")
    
    # Test conversion to dict
    prospect_dict = prospect.to_dict()
    print(f"\nConverted to dict with {len(prospect_dict)} fields")
    
    return prospect


def test_config_manager():
    """Test the source configuration manager."""
    print("\n=== Testing Configuration Manager ===")
    
    # Test getting configurations
    print("\n1. Available source configurations:")
    enabled_configs = config_manager.get_enabled_configs()
    print(f"Found {len(enabled_configs)} enabled sources:")
    
    for config in enabled_configs[:5]:  # Show first 5
        print(f"  - {config.platform.value}: priority={config.priority}")
    
    # Test getting specific config
    print("\n2. GitHub configuration:")
    github_config = config_manager.get_config(SourcePlatform.GITHUB)
    if github_config:
        print(f"  Priority: {github_config.priority}")
        print(f"  Max results: {github_config.max_results}")
        print(f"  Rate limit delay: {github_config.rate_limit_delay}s")
        print(f"  Enabled: {github_config.enabled}")
        print(f"  Search parameters: {github_config.search_parameters}")


def test_performance_adjustment():
    """Test dynamic performance adjustment."""
    print("\n=== Testing Performance Adjustment ===")
    
    selector = IntelligentSourceSelector()
    
    # Simulate performance feedback
    print("\n1. Adjusting performance scores...")
    selector.adjust_source_priority("github", 0.9)  # High performance
    selector.adjust_source_priority("twitter", 0.3)  # Low performance
    selector.adjust_source_priority("reddit", 0.7)   # Medium performance
    
    print("Performance adjustments applied")
    
    # Test how this affects source selection
    sample_icp = {
        "industry": "technology",
        "roles": ["developer"],
        "company_size": "startup"
    }
    
    print("\n2. Re-analyzing sources with performance adjustments...")
    adjusted_configs = selector.analyze_icp_for_sources(sample_icp)
    
    print("Updated source priorities:")
    for config in adjusted_configs[:5]:
        platform_name = config.platform.value
        performance = selector.platform_performance.get(platform_name, 1.0)
        print(f"  - {platform_name}: priority={config.priority}, performance={performance:.3f}")


def main():
    """Run all tests."""
    print("Testing Multi-Source Lead Generation Core Infrastructure")
    print("=" * 60)
    
    try:
        test_source_selection()
        test_prospect_model()
        test_config_manager()
        test_performance_adjustment()
        
        print("\n" + "=" * 60)
        print("✅ All core infrastructure tests passed!")
        print("\nCore infrastructure is ready for platform adapter implementation.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()