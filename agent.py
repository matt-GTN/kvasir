# Environment variables
from dotenv import load_dotenv
import os
load_dotenv()

# Utilities
from typing import List, Dict, TypedDict, Literal
from typing_extensions import TypedDict, Annotated
import json
import operator
from utils import remove_json_blocks
from concurrent.futures import ThreadPoolExecutor

# Langchain
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableParallel
    
# Tools
from tools import google_search_tool, scrape_webpage_tool, parse_linkedin_search_results

# Prompts
from prompts import generate_icp_prompt, strategy_selection_prompt, generate_queries_prompt, filter_search_results_prompt, parse_results_prompt, personalization_prompt

llm = init_chat_model(
    "gemini-2.5-flash-lite",
    model_provider='google_genai',
    temperature=0
)

class AgentState(TypedDict):
    product_context: str
    icp: Dict  # Ideal Customer Profile
    strategy: Dict
    search_queries: List[str]
    raw_search_results: List[Dict]  # Results from Google API
    prospects: List[Dict]  # Structured prospect data (name, title, company, url)
    personalized_outreach: List[Dict]  # Final output
    messages: Annotated[list[AnyMessage], operator.add]  # Add messages to your state
    llm_calls: int
    search_attempts: int  # To count how many times we've tried to search
    error_message: str    # To provide feedback on what went wrong



# Noeud 1
def generate_icp_node(state: AgentState):
    """
    Takes product_context from the state and generates an Ideal Customer Profile based on that.
    """
    print('-'*50)
    print('\n')
    print(state['product_context'])
    print('\n')
    print("--- NODE: Generating ICP Profile ---")
    print('\n')
    
    # Call LLM with a prompt to create the ICP from state['product_context']
    icp_content = llm.invoke(generate_icp_prompt.format_messages(product_context=state['product_context'])).content
    output = remove_json_blocks(icp_content)
    print(output)
    return {"icp": output}

# Noeud 2
def strategy_selection_node(state: AgentState):
    """
    Analyzes the ICP to decide on a prospecting strategy.
    """
    print('-'*50)
    print("\n--- NODE: Selecting Strategy ---")
    icp = state['icp']

    response_content = llm.invoke(
        strategy_selection_prompt.format_messages(icp=icp)
    ).content
    
    llm_output = remove_json_blocks(response_content)

    try:
        strategy_data = json.loads(llm_output)
        print(f"--- Strategy Selected: {strategy_data.get('strategy_name')} ---")
        print(f"--- Rationale: {strategy_data.get('rationale')} ---")
        return {"strategy": strategy_data}
    except json.JSONDecodeError:
        print(f"--- ERROR: Failed to parse strategy JSON: {response_content} ---")
        return {"strategy": {"strategy_name": "PERSON_FIRST_LINKEDIN"}}

# Noeud 3
def generate_queries_node(state: AgentState):
    """
    Generates search queries. If it's a retry, it uses the error_message
    to generate a different set of queries.
    """
    print('-'*50)
    print("\n--- NODE: Generating Queries ---")

    # Increment the attempt counter each time this node runs
    attempts = state.get('search_attempts', 0) + 1
    print(f"--- Search Attempt: {attempts} ---")

    response_content = llm.invoke(
        generate_queries_prompt.format_messages(
            icp=state['icp'],
            strategy_name=state['strategy']['strategy_name'],
            product_context=state['product_context'],
            # Pass the error message to the prompt
            error_message=state.get('error_message', '')
        )
    ).content
    llm_output = remove_json_blocks(response_content)

    try:
        queries_list = json.loads(llm_output)
        print(f"--- Successfully generated and parsed {len(queries_list)} queries. ---")
        for query in queries_list:
            print(query)
        
        # Update state with the new queries and the incremented attempt count
        # Also, clear the error message so it's not used in the next loop if this one succeeds
        return {"search_queries": queries_list, "search_attempts": attempts, "error_message": ""}
    except json.JSONDecodeError:
        print(f"--- ERROR: Failed to parse queries JSON: {response_content} ---")
        return {"search_queries": [], "search_attempts": attempts}



# Noeud 4
def execute_search_node(state: AgentState):
    """
    Takes the search_queries from the state, executes them using the
    google_search_tool, and populates the raw_search_results.
    """
    print('-'*50)
    print('\n')
    print(state['search_queries'])
    print("--- NODE: Executing Web Search ---")
    print('\n')
    search_queries = state['search_queries']
    all_results = []
    
    for query in search_queries:
        # Call the tool for each query
        search_results = google_search_tool.invoke({"query": query})
        all_results.extend(search_results)
    
    print(f'Résultats de la recherche : ', all_results)
    print('\n')

    return {"raw_search_results": all_results}

# Noeud 5
def filter_search_results_node(state: AgentState):
    """
    Filters raw_search_results to include only relevant commercial entities based on ICP and product context.
    """
    print('-'*50)
    print("\n--- NODE: Filtering Search Results ---")
    raw_results = state['raw_search_results']

    # We can pass the full raw results as they are already a list of dicts
    raw_results_str = json.dumps(raw_results, indent=2)

    response_content = llm.invoke(filter_search_results_prompt.format_messages(
                                                                       raw_search_results=raw_results_str,
                                                                       product_context=state['product_context'],
                                                                       icp=state['icp'])).content
    llm_output = remove_json_blocks(response_content)
    try:
        filtered_results_list = json.loads(llm_output)
        
        print(f"--- Successfully filtered to {len(filtered_results_list)} relevant search results. ---")
        # Overwrite raw_search_results with the filtered ones for the next step
        return {"raw_search_results": filtered_results_list} 
    except json.JSONDecodeError:
        print(f"--- ERROR: Failed to parse filtered results JSON: {response_content} ---")
        return {"raw_search_results": []}

# Routeur de stratégie
def strategy_routing(state):
    """Decide parsing node based on the strategy"""
    strategy_name = state.get("strategy", {}).get("strategy_name")
    
    if strategy_name == "PERSON_FIRST_LINKEDIN":
        return "person_first"
    elif strategy_name == "COMPANY_FIRST_LOCAL":
        return "company_first"
    else:
        # Fallback to prevent None return
        print(f"Unknown strategy: {strategy_name}, defaulting to person_first")
        return "person_first"

# Noeud 6.A   
def parse_linkedin_node(state: AgentState):
    print("\n--- NODE: Parsing Search Results (Python-Based) ---")
    
    raw_results = state['raw_search_results']
    print(f"--- Input to parsing tool: {len(raw_results)} raw results ---")
    
    # Debug: Print first result to see structure
    if raw_results:
        print(f"--- Sample raw result structure: ---")
        print(raw_results[0])
    
    prospects_list = parse_linkedin_search_results.invoke({"search_data": raw_results})
    
    print(f"--- Tool returned {len(prospects_list)} prospects ---")
    if not prospects_list:
        print("--- WARNING: Tool returned empty list - check tool implementation ---")
    
    return {"prospects": prospects_list}
    
# Noeud 6.B   
def parse_llm_node(state: AgentState):
    """
    Takes the raw_search_results for a company_first strategy and simplifies them, and uses an LLM
    to parse them into a structured list of prospects including the snippet.
    """
    print("\n--- NODE: Parsing Search Results (LLM-Based) ---")
    raw_results = state['raw_search_results']

    # We can pass the full raw results as they are already a list of dicts
    simplified_results_str = json.dumps(raw_results, indent=2)

    response_content = llm.invoke(parse_results_prompt.format_messages(search_results=simplified_results_str,
                                                                       product_context=state['product_context'],
                                                                       icp=state['icp'])).content
    llm_output = remove_json_blocks(response_content)
    try:
        prospects_list = json.loads(llm_output)
        
        
        print(f"--- Successfully parsed {len(prospects_list)} prospects. ---")
        print('\n')
        for prospect in prospects_list:
            print(prospect)
        return {"prospects": prospects_list}
    except json.JSONDecodeError:
        print(f"--- ERROR: Failed to parse prospects JSON: {response_content} ---")
        return {"prospects": []}
        
# Noeud 7
def deduplicate_prospects_node(state: AgentState):
    print("\n--- NODE: Deduplicating Prospects ---")
    unique_prospects = []
    seen_urls = set()
    for prospect in state['prospects']:
        if prospect['url'] not in seen_urls:
            unique_prospects.append(prospect)
            seen_urls.add(prospect['url'])
    print(f"--- Deduplicated to {len(unique_prospects)} unique prospects. ---")
    return {"prospects": unique_prospects}

# Noeud 8
def personalization_node(state: AgentState):
    """
    Generates personalized outreach content by scraping prospect URLs in parallel
    and then calling the LLM in a single batch operation.
    """
    print('-'*50)
    print("\n--- NODE: Generating Personalized Outreach (Optimized) ---")
    prospects = state['prospects']
    product_context = state['product_context']
    
    print(f"--- Researching {len(prospects)} prospects in parallel... ---")
    
    # We use a ThreadPoolExecutor to run the scrape_webpage_tool on multiple threads.
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Create a list of URLs to scrape
        urls_to_scrape = [prospect['url'] for prospect in prospects]
        # map() runs the tool for each URL and returns the results in the same order.
        scraped_contents = list(executor.map(lambda url: scrape_webpage_tool.invoke({"url": url}), urls_to_scrape))
    
    print("--- Preparing prompts for batch LLM call... ---")
    all_prompts = []
    for i, prospect in enumerate(prospects):
        # Match the scraped content to the correct prospect
        researched_content = scraped_contents[i]
        
        # If scraping failed for a prospect, we can skip them or use a default.
        if "Error fetching URL" in researched_content:
            print(f"--- WARNING: Skipping personalization for {prospect['name']} due to scraping error. ---")
            continue

        # Format the prompt with the successfully scraped content
        prompt = personalization_prompt.format_messages(
            product_context=product_context, 
            prospect_name=prospect['name'],
            prospect_title=prospect['title'],
            prospect_url=prospect['url'],
            researched_content=researched_content
        )
        all_prompts.append(prompt)

    # --- Step 3: Execute a single batch LLM call ---
    print(f"--- Executing batch LLM call for {len(all_prompts)} prompts... ---")
    batch_results = llm.batch(all_prompts)
    
    # --- Step 4: Process the results ---
    outreach_list = []
    for i, result in enumerate(batch_results):
        llm_output = remove_json_blocks(result.content)
        
        # We need to find the original prospect that this result corresponds to
        original_prospect = prospects[i] 
        
        try:
            recommendations = json.loads(llm_output)
            outreach_list.append({
                "prospect": original_prospect,
                "recommendations": recommendations
            })
        except json.JSONDecodeError:
            print(f"--- ERROR: Failed to parse personalization for {original_prospect['name']} ---")
            
    print(f"--- Successfully generated {len(outreach_list)} personalized outreach messages. ---")
    return {"personalized_outreach": outreach_list}

# Noeud 9
def prepare_for_retry_node(state: AgentState):
    """Updates the error_message in the state to guide the next query generation attempt."""
    error_message = "The previous set of search queries did not yield any viable prospects after filtering. Please generate a new and different set of queries, perhaps by targeting adjacent industries or using broader keywords."
    return {"error_message": error_message}

# Routeur d'erreurs
def should_continue_or_retry(state: AgentState):
    """Router to decide whether to continue, retry the search, or end the process."""
    if len(state['prospects']) > 0:
        print(f"--- {len(state['prospects'])} prospects found. Proceeding to personalization. ---")
        return "continue"
    else:
        # Check if we have exceeded the max number of retries
        if state.get('search_attempts', 0) >= 3:
            print("--- MAX SEARCH ATTEMPTS REACHED. ENDING RUN. ---")
            return "end"
        else:
            print("--- NO PROSPECTS FOUND. RETRYING SEARCH. ---")
            return "retry"

# Build workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("generate_icp_node", generate_icp_node)
workflow.add_node("strategy_selection_node", strategy_selection_node)
workflow.add_node("generate_queries_node", generate_queries_node)
workflow.add_node("execute_search_node", execute_search_node)
workflow.add_node("filter_search_results_node", filter_search_results_node)
workflow.add_node("parse_linkedin_node", parse_linkedin_node)
workflow.add_node("parse_llm_node", parse_llm_node)
workflow.add_node("personalization_node", personalization_node)
workflow.add_node("deduplicate_prospects_node", deduplicate_prospects_node)
workflow.add_node("prepare_for_retry_node", prepare_for_retry_node)


# Fixed part
workflow.add_edge(START, "generate_icp_node")
workflow.add_edge("generate_icp_node", "strategy_selection_node")
workflow.add_edge("strategy_selection_node", "generate_queries_node")
workflow.add_edge("generate_queries_node", "execute_search_node")
workflow.add_edge("execute_search_node", "filter_search_results_node")

# Conditional parsing
workflow.add_conditional_edges(
    "filter_search_results_node", 
    strategy_routing,    
    {
        "person_first": "parse_linkedin_node", 
        "company_first": "parse_llm_node"
    }
)
workflow.add_edge("parse_linkedin_node", "deduplicate_prospects_node")
workflow.add_edge("parse_llm_node", "deduplicate_prospects_node")



# Conditional looping
workflow.add_conditional_edges(
    "deduplicate_prospects_node",
    should_continue_or_retry,
    {
        "continue": "personalization_node",
        "retry": "prepare_for_retry_node",
        "end": END
    }
)

workflow.add_edge("personalization_node", END)

# Compile the agent
agent = workflow.compile()

# Invoke with product_context extracted from human message
# human_message_content = "Je suis une créatrice de 52 ans à Pontchâteau, Loire-Atlantique, France, et je réalise de magnifiques pièces de décoration : attrape-rêves, créations en macramé et ojo de dios. Pour le marcramé, je vends de la décoration, porte-plantes, sacs, ceintures, accessoires, porte-clés, etc... Je travaille également sur commande pour tout type de pièces originales. J’expose déjà dans une boutique, et je suis ouvert à plus de canaux de ventes."
human_message_content = "I am a starting Freelance, 28 years old. I live in France and speak English really well. I'd like to focus on US clients. I can dev websites, web apps, and most of all can offer AI, Agents and automation services. Never had a client yet. My stack : Langgraph, LLM APis, React, FastAPI, Next JS, but also Data Science : Plotly, Pandas, Scikit learn and more. I'd like to find clients that can pay for my skills, but I don't know what is the right approach"
human_message = HumanMessage(content=human_message_content)

# Create initial state with product_context from human message
initial_state = {
    "product_context": human_message_content,  # Extract product description from human message
    "messages": [human_message],
    "icp": {},
    "search_queries": {},
    "raw_search_results": [],
    "prospects": [],
    "personalized_outreach": [],
    "llm_calls": 0,
    "search_attempts": 0,
    "error_message": ""

}

# Invoke the agent
result = agent.invoke(initial_state)

print('-'*50)
print('\n')
for outreach in result['personalized_outreach']:
    print(json.dumps(outreach, indent=2))
    print('\n')
    print('-'*50)
    print('\n')








