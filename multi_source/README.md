# Multi-Source Lead Generation Infrastructure

This package provides the core infrastructure for discovering leads across multiple platforms beyond Google search. It implements an intelligent source selection system that automatically determines the best lead generation platforms based on ICP analysis.

## Core Components

### 1. Data Models (`core/models.py`)

- **`Prospect`**: Standardized prospect data model supporting multi-source information
- **`SourceConfig`**: Configuration for individual lead generation platforms  
- **`SearchStrategy`**: Platform-specific search strategies and parameters
- **`SourceMetrics`**: Performance tracking for each platform
- **`MultiSourceResult`**: Aggregated results from multiple sources

### 2. Base Interfaces (`core/interfaces.py`)

- **`PlatformAdapter`**: Base interface for all platform-specific adapters
- **`SourceSelectionEngine`**: Interface for intelligent source selection
- **`DataNormalizer`**: Interface for normalizing data across platforms
- **`LeadScoringEngine`**: Interface for scoring and ranking prospects
- **`DeduplicationEngine`**: Interface for removing duplicate prospects

### 3. Intelligent Source Selection (`core/source_selection.py`)

The `IntelligentSourceSelector` automatically analyzes ICP characteristics to:

- **Industry Mapping**: Maps industries to optimal platforms (e.g., technology → GitHub, Stack Overflow)
- **Role Targeting**: Selects platforms based on target roles (e.g., developers → GitHub, founders → Crunchbase)
- **Company Size**: Adjusts platform selection based on company size preferences
- **Performance Learning**: Dynamically adjusts source priorities based on results quality

### 4. Configuration Management (`config/source_config.py`)

- **`SourceConfigManager`**: Manages platform configurations and settings
- **Default Configurations**: Pre-configured settings for all supported platforms
- **Dynamic Updates**: Runtime configuration changes and performance adjustments

## Supported Platforms

### Currently Implemented
- **Google Search** (existing platform)
- **Twitter/X** - Social media prospecting
- **GitHub** - Developer and tech company discovery
- **Reddit** - Community-based lead discovery
- **Stack Overflow** - Technical professional identification
- **Hacker News** - Startup and tech community
- **Product Hunt** - Startup founders and early adopters
- **Crunchbase** - Company and funding data
- **Medium** - Thought leaders and content creators
- **Eventbrite** - Event organizers and attendees
- **Meetup** - Community organizers and members
- **Job Boards** - Hiring companies and managers

### Platform Adapters (To Be Implemented)
Each platform will have a dedicated adapter implementing the `PlatformAdapter` interface with:
- Authentication handling
- Rate limiting and retry logic
- Platform-specific search functionality
- Data extraction and normalization

## Integration with Existing Agent

The multi-source infrastructure integrates with the existing lead generation agent by:

1. **Replacing Strategy Selection**: The `IntelligentSourceSelector` replaces the hardcoded strategy selection node
2. **Enhanced Query Generation**: Platform-specific query strategies instead of generic Google queries
3. **Parallel Execution**: Multiple sources searched simultaneously for better coverage
4. **Unified Results**: All prospects normalized to standard format for existing parsing/personalization nodes

## Usage Example

```python
from multi_source import IntelligentSourceSelector, config_manager

# Initialize source selector
selector = IntelligentSourceSelector()

# Analyze ICP for optimal sources
icp = {
    "industry": "technology",
    "roles": ["developer", "engineer"],
    "company_size": "startup"
}

source_configs = selector.analyze_icp_for_sources(icp)
print(f"Selected {len(source_configs)} optimal sources")

# Generate platform-specific strategies
source_names = [config.platform.value for config in source_configs]
strategies = selector.get_source_strategies(source_names, icp)

# Access configuration
github_config = config_manager.get_config(SourcePlatform.GITHUB)
```

## Requirements Addressed

This core infrastructure addresses the following requirements from the specification:

- **Requirement 8.1**: Automatic determination of relevant lead sources based on ICP analysis
- **Requirement 8.2**: Dynamic source selection and priority adjustment based on performance
- **Requirement 6.3**: Standardized prospect data model with multi-source support
- **Requirement 7.1**: Rate limiting and platform-specific handling infrastructure

## Next Steps

The core infrastructure is now ready for:

1. **Platform Adapter Implementation**: Individual adapters for each supported platform
2. **Search Orchestration**: Parallel execution system for multi-source searches
3. **Data Normalization**: Platform-specific data parsing and standardization
4. **Lead Scoring**: Multi-factor scoring algorithm implementation
5. **Deduplication**: Advanced prospect merging and duplicate detection

## Testing

Run the test suite to verify the infrastructure:

```bash
python test_core_infrastructure.py
```

View the integration example:

```bash
python multi_source_integration_example.py
```