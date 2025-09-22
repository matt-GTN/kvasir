"""
Example integration of multi-source infrastructure with existing agent system.
This demonstrates how the new multi-source system can replace the existing 
strategy selection node.
"""
from typing import Dict, Any, List
from multi_source import IntelligentSourceSelector, Prospect, SourcePlatform


class MultiSourceLeadGenerator:
    """
    Enhanced lead generator that uses multiple sources instead of just Google search.
    This class demonstrates how to integrate the new infrastructure with the existing agent.
    """
    
    def __init__(self):
        self.source_selector = IntelligentSourceSelector()
        self.platform_adapters = {}  # Will be populated with actual adapters in future tasks
    
    def analyze_icp_and_select_sources(self, icp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Replace the existing strategy_selection_node with intelligent source selection.
        
        This method demonstrates how the new system integrates with the existing workflow.
        """
        print("--- ENHANCED NODE: Multi-Source Selection ---")
        
        # Use intelligent source selection instead of hardcoded strategies
        source_configs = self.source_selector.analyze_icp_for_sources(icp)
        
        # Generate platform-specific search strategies
        source_names = [config.platform.value for config in source_configs]
        strategies = self.source_selector.get_source_strategies(source_names, icp)
        
        # Format for compatibility with existing agent state
        multi_source_strategy = {
            "strategy_name": "MULTI_SOURCE_INTELLIGENT",
            "selected_sources": source_names,
            "source_configs": [config.to_dict() for config in source_configs],
            "search_strategies": {name: {
                "primary_queries": strategy.primary_queries,
                "fallback_queries": strategy.fallback_queries,
                "filters": strategy.filters,
                "result_limit": strategy.result_limit
            } for name, strategy in strategies.items()},
            "rationale": f"Intelligently selected {len(source_configs)} sources based on ICP analysis"
        }
        
        print(f"Selected {len(source_configs)} optimal sources for this ICP:")
        for config in source_configs[:5]:  # Show top 5
            print(f"  - {config.platform.value} (priority: {config.priority})")
        
        return multi_source_strategy
    
    def generate_multi_source_queries(self, strategy: Dict[str, Any], icp: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate platform-specific queries for each selected source.
        This replaces the generate_company_search_queries_node for multi-source.
        """
        print("--- ENHANCED NODE: Multi-Source Query Generation ---")
        
        all_queries = {}
        search_strategies = strategy.get("search_strategies", {})
        
        for platform, platform_strategy in search_strategies.items():
            queries = platform_strategy["primary_queries"]
            if not queries:  # Fallback if primary queries are empty
                queries = platform_strategy["fallback_queries"]
            
            all_queries[platform] = queries[:3]  # Limit to top 3 queries per platform
            print(f"{platform}: {len(queries)} queries generated")
        
        return all_queries
    
    def simulate_multi_source_search(self, queries: Dict[str, List[str]]) -> List[Prospect]:
        """
        Simulate multi-source search execution.
        In the actual implementation, this would call real platform adapters.
        """
        print("--- ENHANCED NODE: Multi-Source Search Execution ---")
        
        # Simulate prospects from different sources
        simulated_prospects = []
        
        for platform, platform_queries in queries.items():
            print(f"Searching {platform} with {len(platform_queries)} queries...")
            
            # Simulate finding prospects (in real implementation, this would call platform adapters)
            for i, query in enumerate(platform_queries):
                prospect = Prospect(
                    name=f"Prospect {i+1} from {platform}",
                    title=f"Role related to: {query}",
                    company=f"Company found via {platform}",
                    source_platform=platform,
                    source_url=f"https://{platform}.com/prospect{i+1}",
                    relevance_score=0.7 + (i * 0.1),
                    engagement_score=0.6 + (i * 0.1)
                )
                simulated_prospects.append(prospect)
        
        print(f"Found {len(simulated_prospects)} prospects across {len(queries)} platforms")
        return simulated_prospects
    
    def demonstrate_integration(self, product_context: str):
        """
        Demonstrate how the multi-source system integrates with existing workflow.
        """
        print("=" * 60)
        print("MULTI-SOURCE LEAD GENERATION INTEGRATION DEMO")
        print("=" * 60)
        
        # Simulate ICP generation (this would come from existing generate_icp_node)
        print("\n1. ICP Analysis (from existing node):")
        simulated_icp = {
            "industry": "technology",
            "roles": ["developer", "engineer", "cto"],
            "company_size": "startup",
            "description": product_context
        }
        print(f"   Industry: {simulated_icp['industry']}")
        print(f"   Target roles: {simulated_icp['roles']}")
        print(f"   Company size: {simulated_icp['company_size']}")
        
        # Step 2: Enhanced source selection (replaces strategy_selection_node)
        print("\n2. Enhanced Source Selection:")
        strategy = self.analyze_icp_and_select_sources(simulated_icp)
        
        # Step 3: Multi-source query generation
        print("\n3. Multi-Source Query Generation:")
        queries = self.generate_multi_source_queries(strategy, simulated_icp)
        
        # Step 4: Multi-source search execution
        print("\n4. Multi-Source Search Execution:")
        prospects = self.simulate_multi_source_search(queries)
        
        # Step 5: Show results that would go to existing parsing/personalization nodes
        print("\n5. Results for Existing Pipeline:")
        print(f"   Total prospects found: {len(prospects)}")
        print(f"   Sources used: {list(queries.keys())}")
        print(f"   Average relevance score: {sum(p.relevance_score for p in prospects) / len(prospects):.2f}")
        
        # Convert to format compatible with existing agent state
        legacy_format_prospects = []
        for prospect in prospects[:5]:  # Show first 5
            legacy_format_prospects.append({
                'name': prospect.name,
                'title': prospect.title,
                'company': prospect.company,
                'url': prospect.source_url,
                'snippet': f"Found via {prospect.source_platform} - {prospect.title}"
            })
        
        print("\n6. Sample prospects in legacy format for existing nodes:")
        for i, prospect in enumerate(legacy_format_prospects, 1):
            print(f"   {i}. {prospect['name']} - {prospect['title']}")
        
        return {
            'strategy': strategy,
            'prospects': legacy_format_prospects,
            'multi_source_prospects': prospects
        }


def main():
    """Demonstrate the integration."""
    
    # Sample product context (would come from user input)
    product_context = """
    I am a freelance developer offering AI, automation, and web development services.
    I specialize in LangGraph, LLM APIs, React, FastAPI, and Next.js.
    I'm targeting US clients who need AI-powered solutions and automation.
    """
    
    # Create and run the demo
    generator = MultiSourceLeadGenerator()
    results = generator.demonstrate_integration(product_context)
    
    print("\n" + "=" * 60)
    print("✅ Integration demonstration complete!")
    print("\nThis shows how the multi-source infrastructure can enhance")
    print("the existing agent workflow with minimal changes to the")
    print("current node structure.")


if __name__ == "__main__":
    main()