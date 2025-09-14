import os
from langchain_core.tools import tool
from googleapiclient.discovery import build

@tool
def google_search_tool(query: str) -> list[dict]:
    """
    Performs a Google search using the Custom Search JSON API and returns a list of search results.
    Each result is a dictionary containing 'title', 'link', and 'snippet'.
    Use this to find people, companies, articles, and other information on the public web.
    """
    print(f"--- TOOL: Searching Google for: '{query}' ---")
    try:
        # Get credentials from environment variables
        api_key = os.environ["GOOGLE_CSE_API_KEY"]
        cse_id = os.environ["GOOGLE_CSE_ID"]

        # Build the service object
        service = build("customsearch", "v1", developerKey=api_key)

        # Execute the search
        # We ask for the top 5 results by setting num=5
        result = service.cse().list(q=query, cx=cse_id, num=5).execute()

        # Extract the items or return an empty list if no results
        return result.get("items", [])

    except Exception as e:
        print(f"Error during Google search: {e}")
        return [{"error": f"An error occurred: {e}"}]