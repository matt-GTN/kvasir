"""
Source configuration management system.
"""
import json
import os
from typing import Dict, List, Any, Optional
from ..core.models import SourceConfig, SourcePlatform


class SourceConfigManager:
    """Manages configuration for all lead generation sources."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "multi_source_config.json"
        self.configs = {}
        self.load_config()
    
    def load_config(self):
        """Load source configurations from file or create defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self._parse_config_data(data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading config file: {e}. Using defaults.")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def save_config(self):
        """Save current configurations to file."""
        data = {
            'sources': {
                platform.value: config.to_dict() 
                for platform, config in self.configs.items()
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_config(self, platform: SourcePlatform) -> Optional[SourceConfig]:
        """Get configuration for a specific platform."""
        return self.configs.get(platform)
    
    def get_enabled_configs(self) -> List[SourceConfig]:
        """Get all enabled source configurations."""
        return [config for config in self.configs.values() if config.enabled]
    
    def update_config(self, platform: SourcePlatform, **kwargs):
        """Update configuration for a specific platform."""
        if platform in self.configs:
            config = self.configs[platform]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self.save_config()
    
    def enable_source(self, platform: SourcePlatform):
        """Enable a specific source."""
        self.update_config(platform, enabled=True)
    
    def disable_source(self, platform: SourcePlatform):
        """Disable a specific source."""
        self.update_config(platform, enabled=False)
    
    def _parse_config_data(self, data: Dict[str, Any]):
        """Parse configuration data from file."""
        sources_data = data.get('sources', {})
        
        for platform_name, config_data in sources_data.items():
            try:
                platform = SourcePlatform(platform_name)
                config = SourceConfig(
                    platform=platform,
                    priority=config_data.get('priority', 5),
                    max_results=config_data.get('max_results', 50),
                    search_parameters=config_data.get('search_parameters', {}),
                    rate_limit_delay=config_data.get('rate_limit_delay', 1.0),
                    enabled=config_data.get('enabled', True)
                )
                self.configs[platform] = config
            except ValueError:
                print(f"Unknown platform in config: {platform_name}")
    
    def _create_default_config(self):
        """Create default configurations for all platforms."""
        default_configs = {
            SourcePlatform.GOOGLE_SEARCH: SourceConfig(
                platform=SourcePlatform.GOOGLE_SEARCH,
                priority=8,
                max_results=50,
                rate_limit_delay=1.0,
                enabled=True
            ),
            SourcePlatform.TWITTER: SourceConfig(
                platform=SourcePlatform.TWITTER,
                priority=7,
                max_results=100,
                rate_limit_delay=2.0,
                enabled=True,
                search_parameters={'verified_only': False, 'min_followers': 50}
            ),
            SourcePlatform.GITHUB: SourceConfig(
                platform=SourcePlatform.GITHUB,
                priority=6,
                max_results=50,
                rate_limit_delay=1.0,
                enabled=True,
                search_parameters={'sort': 'stars', 'order': 'desc'}
            ),
            SourcePlatform.REDDIT: SourceConfig(
                platform=SourcePlatform.REDDIT,
                priority=5,
                max_results=75,
                rate_limit_delay=1.5,
                enabled=True,
                search_parameters={'sort': 'hot', 'time_filter': 'month'}
            ),
            SourcePlatform.STACK_OVERFLOW: SourceConfig(
                platform=SourcePlatform.STACK_OVERFLOW,
                priority=6,
                max_results=50,
                rate_limit_delay=1.0,
                enabled=True,
                search_parameters={'min_reputation': 500, 'sort': 'votes'}
            ),
            SourcePlatform.HACKER_NEWS: SourceConfig(
                platform=SourcePlatform.HACKER_NEWS,
                priority=5,
                max_results=40,
                rate_limit_delay=1.0,
                enabled=True
            ),
            SourcePlatform.PRODUCT_HUNT: SourceConfig(
                platform=SourcePlatform.PRODUCT_HUNT,
                priority=4,
                max_results=30,
                rate_limit_delay=1.5,
                enabled=True,
                search_parameters={'featured_only': False}
            ),
            SourcePlatform.CRUNCHBASE: SourceConfig(
                platform=SourcePlatform.CRUNCHBASE,
                priority=6,
                max_results=25,
                rate_limit_delay=3.0,
                enabled=True,
                search_parameters={'funding_stages': ['seed', 'series-a', 'series-b']}
            ),
            SourcePlatform.MEDIUM: SourceConfig(
                platform=SourcePlatform.MEDIUM,
                priority=4,
                max_results=40,
                rate_limit_delay=1.5,
                enabled=True
            ),
            SourcePlatform.EVENTBRITE: SourceConfig(
                platform=SourcePlatform.EVENTBRITE,
                priority=3,
                max_results=30,
                rate_limit_delay=2.0,
                enabled=True
            ),
            SourcePlatform.MEETUP: SourceConfig(
                platform=SourcePlatform.MEETUP,
                priority=3,
                max_results=30,
                rate_limit_delay=2.0,
                enabled=True
            ),
            SourcePlatform.YOUTUBE: SourceConfig(
                platform=SourcePlatform.YOUTUBE,
                priority=4,
                max_results=40,
                rate_limit_delay=1.5,
                enabled=False  # Disabled by default due to complexity
            ),
            SourcePlatform.DISCORD: SourceConfig(
                platform=SourcePlatform.DISCORD,
                priority=3,
                max_results=25,
                rate_limit_delay=2.0,
                enabled=False  # Disabled by default due to API limitations
            ),
            SourcePlatform.SUBSTACK: SourceConfig(
                platform=SourcePlatform.SUBSTACK,
                priority=3,
                max_results=30,
                rate_limit_delay=1.5,
                enabled=False  # Disabled by default
            ),
            SourcePlatform.ANGELLIST: SourceConfig(
                platform=SourcePlatform.ANGELLIST,
                priority=4,
                max_results=25,
                rate_limit_delay=2.0,
                enabled=False  # Disabled by default due to API changes
            ),
            SourcePlatform.JOB_BOARDS: SourceConfig(
                platform=SourcePlatform.JOB_BOARDS,
                priority=5,
                max_results=50,
                rate_limit_delay=3.0,
                enabled=True,
                search_parameters={'boards': ['linkedin', 'indeed', 'glassdoor']}
            )
        }
        
        self.configs = default_configs
        self.save_config()


# Global configuration manager instance
config_manager = SourceConfigManager()