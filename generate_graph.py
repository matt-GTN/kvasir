#!/usr/bin/env python3
"""
Standalone script to generate LangGraph workflow diagrams.
Usage: python generate_graph.py
"""

def generate_workflow_graph(agent, filename="agent_graph.png", xray=True):
    """
    Generate a visual representation of the LangGraph workflow.
    
    Args:
        agent: The compiled LangGraph agent
        filename: Output filename for the PNG image
        xray: Whether to show internal node details
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Try the API method first (faster if available)
        print("--- Attempting to generate workflow diagram via API... ---")
        img_bytes = agent.get_graph(xray=xray).draw_mermaid_png()
        
        with open(filename, "wb") as f:
            f.write(img_bytes)
        print(f"--- Workflow diagram saved as {filename} (API method) ---")
        return True
        
    except Exception as api_error:
        print(f"--- API method failed: {api_error} ---")
        
        try:
            # Fallback to Pyppeteer (local browser rendering)
            print("--- Attempting local browser rendering... ---")
            from langchain_core.runnables.graph_mermaid import MermaidDrawMethod
            
            img_bytes = agent.get_graph(xray=xray).draw_mermaid_png(
                draw_method=MermaidDrawMethod.PYPPETEER
            )
            
            with open(filename, "wb") as f:
                f.write(img_bytes)
            print(f"--- Workflow diagram saved as {filename} (Pyppeteer method) ---")
            return True
            
        except ImportError:
            print("--- Pyppeteer not installed. Install with: pip install pyppeteer ---")
            return False
            
        except Exception as local_error:
            print(f"--- Local rendering failed: {local_error} ---")
            
            try:
                # Final fallback: save as text-based mermaid syntax
                print("--- Saving as Mermaid text syntax... ---")
                mermaid_syntax = agent.get_graph(xray=xray).draw_mermaid()
                
                text_filename = filename.replace('.png', '.mmd')
                with open(text_filename, "w") as f:
                    f.write(mermaid_syntax)
                print(f"--- Mermaid syntax saved as {text_filename} ---")
                print("--- You can paste this into https://mermaid.live/ to view the diagram ---")
                return True
                
            except Exception as final_error:
                print(f"--- All methods failed: {final_error} ---")
                return False


if __name__ == "__main__":
    # Import the agent from your main file
    try:
        from agent import agent
        
        print("Generating workflow diagram...")
        success = generate_workflow_graph(agent, "agent_graph.png", xray=True)
        
        if success:
            print("✅ Workflow diagram generated successfully!")
        else:
            print("❌ Failed to generate workflow diagram")
            
    except ImportError as e:
        print(f"❌ Could not import agent: {e}")
        print("Make sure agent.py is in the same directory and the agent is properly defined.")