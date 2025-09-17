import os
from langchain_core.tools import tool
from googleapiclient.discovery import build
import re
import requests
from bs4 import BeautifulSoup

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
    
@tool
def parse_linkedin_title(title_string: str) -> dict:
    """
    Parses a LinkedIn title string to extract name and title.
    Returns a dictionary with 'name' and 'title' or None if it fails.
    """
    # Pattern: (Anything before the dash) - (Anything after the dash until a | or the end)
    match = re.search(r'^(.*?) - (.*?)(?: \| LinkedIn)?$', title_string.strip())
    
    if match:
        name = match.group(1).strip()
        title = match.group(2).strip()
        # Clean up trailing dots often added by Google
        if title.endswith('...'):
            title = title[:-3].strip()
        return {"name": name, "title": title}
    return None

@tool
def scrape_webpage_tool(url: str) -> str:
    """
    Fetches the clean text content from a given URL.
    Use this to get the content of a LinkedIn profile, a blog post,
    or a news article for personalization research.
    """
    print(f"--- TOOL: Scraping URL: '{url}' ---")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # A simple way to get clean text from a webpage
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Return the first 4000 characters to avoid huge token counts
        return clean_text[:4000]
        
    except requests.RequestException as e:
        return f"Error fetching URL: {e}"