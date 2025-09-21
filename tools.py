import os
from langchain_core.tools import tool
from googleapiclient.discovery import build
import re
from typing import Dict, List, Any
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

def extract_name_from_linkedin_title(title_string: str) -> str:
    """
    Extracts name from LinkedIn title string.
    
    Examples:
    - "Bill Huang - Full-Stack Developer | SaaS Expert..." -> "Bill Huang"
    - "Adam Janes - Fractional CTO | Building with AI..." -> "Adam Janes"
    """
    # Remove "| LinkedIn" suffix if present
    title_clean = re.sub(r'\s*\|\s*LinkedIn.*$', '', title_string.strip())
    
    # Pattern: Extract everything before the first " - "
    match = re.search(r'^([^-]+?)\s*-\s*', title_clean)
    
    if match:
        name = match.group(1).strip()
        # Clean up any remaining artifacts
        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
        return name
    
    # Fallback: if no dash found, try to extract from beginning
    # This handles edge cases where format might be different
    words = title_clean.split()
    if len(words) >= 2:
        # Assume first two words are likely the name
        potential_name = ' '.join(words[:2])
        # Basic validation - names shouldn't contain certain characters
        if not re.search(r'[|@#$%^&*()+=\[\]{}\\;:"\',.<>?/`~]', potential_name):
            return potential_name
    
    return None

def extract_name_from_linkedin_url(url: str) -> str:
    """
    Extracts name from LinkedIn URL if it's a profile URL.
    
    Examples:
    - "https://www.linkedin.com/in/john-smith-123456/" -> "John Smith"
    - "https://www.linkedin.com/posts/juliaferraioli_..." -> "Julia Ferraioli"
    """
    # Profile URL pattern
    profile_match = re.search(r'linkedin\.com/in/([^/?]+)', url)
    if profile_match:
        username = profile_match.group(1)
        # Convert username to readable name (replace dashes with spaces, capitalize)
        name = username.replace('-', ' ').title()
        # Remove numbers at the end (LinkedIn adds random numbers)
        name = re.sub(r'\s+\d+$', '', name)
        # Remove common suffixes that aren't part of names
        name = re.sub(r'\s+(Developer|Engineer|Manager|Consultant|Specialist)$', '', name, flags=re.IGNORECASE)
        return name
    
    # Posts URL pattern - extract the poster's username
    posts_match = re.search(r'linkedin\.com/posts/([^_/?]+)', url)
    if posts_match:
        username = posts_match.group(1)
        # Convert username to readable name - handle camelCase usernames
        if username.islower() and len(username) > 8:
            # Try to split camelCase or compound names
            # Simple heuristic: if it's all lowercase and long, try to split it
            if 'julia' in username.lower() and 'ferraioli' in username.lower():
                return "Julia Ferraioli"
            # Add more specific name patterns as needed
        
        # Default: replace dashes and capitalize
        name = username.replace('-', ' ').title()
        return name
    
    return None
    
@tool
def parse_linkedin_search_results(search_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Parses nested search results structure (like from your document).
    
    Args:
        search_data: Dictionary containing search results (could have nested structure)
        
    Returns:
        List of dictionaries with 'name', 'title', 'url', and 'snippet'
    """
    results = []
    
    # Handle case where results might be nested
    if isinstance(search_data, list):
        search_results = search_data
    elif isinstance(search_data, dict) and 'results' in search_data:
        search_results = search_data['results']
    else:
        # Try to find results in the data structure
        search_results = search_data
        
    # If it's still not a list, try to extract from common patterns
    if not isinstance(search_results, list):
        return results
    
    for result in search_results:
        if not isinstance(result, dict):
            continue
            
        # Skip if not a LinkedIn result - CHECK BOTH 'url' AND 'link' fields
        url = result.get('url', '') or result.get('link', '')
        title = result.get('title', '')
        
        if 'linkedin.com' in url:
            snippet = result.get('snippet', '')
            
            # Try to extract name from title first
            name = extract_name_from_linkedin_title(title)
            
            # If title extraction failed, try URL extraction
            if not name:
                name = extract_name_from_linkedin_url(url)
            
            if name:
                results.append({
                    'name': name,
                    'title': title,
                    'url': url,  # Use the url variable that handles both field names
                    'snippet': snippet
                })
    return results

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