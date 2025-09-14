# Environment variables
from dotenv import load_dotenv
import os
load_dotenv()

# Utilities
from typing import List, Dict, TypedDict
from typing_extensions import TypedDict, Annotated
import json
import operator

# Langchain
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
    
# Tools
from tools import google_search_tool

# Prompts
from prompts import generate_icp_prompt, generate_queries_prompt

llm = init_chat_model(
    "gemini-2.5-flash-lite",
    model_provider='google_genai',
    temperature=0
)

class AgentState(TypedDict):
    product_description: str
    icp: Dict  # Ideal Customer Profile
    search_queries: List[str]
    raw_search_results: List[Dict]  # Results from Google API
    prospects: List[Dict]  # Structured prospect data (name, title, company, url)
    personalized_outreach: List[Dict]  # Final output
    messages: Annotated[list[AnyMessage], operator.add]  # Add messages to your state
    llm_calls: int

def generate_icp_node(state: AgentState):
    """
    Takes product_description from the state and generates an Ideal Customer Profile based on that.
    """
    print('-'*50)
    print('\n')
    print(state['product_description'])
    print("--- NODE: Generating ICP Profile ---")
    # Call LLM with a prompt to create the ICP from state['product_description']
    icp_content = llm.invoke(generate_icp_prompt.format_messages(product_description=state['product_description'])).content
    return {"icp": icp_content}

def generate_queries_node(state: AgentState):
    """
    Takes icp from the state and generates search queries for the Google API, based on it.
    """
    print('-'*50)
    print('\n')
    print(state['icp'])
    print("--- NODE: Generating Queries ---")
    queries_content = llm.invoke(generate_queries_prompt.format_messages(icp=state['icp'])).content
    
    try:
        queries_list = json.loads(queries_content)
        print(f"--- Successfully generated and parsed {len(queries_list)} queries. ---")
        # 4. Return the clean list to be stored in the state
        return {"search_queries": queries_list}
    except json.JSONDecodeError:
        print(f"--- ERROR: Failed to parse JSON from LLM output: {queries_string} ---")
        # Return an empty list to prevent the next node from crashing
        return {"search_queries": []}

def execute_search_node(state: AgentState):
    """
    Takes the search_queries from the state, executes them using the
    google_search_tool, and populates the raw_search_results.
    """
    print('-'*50)
    print('\n')
    print(state['search_queries'])
    print("--- NODE: Executing Web Search ---")
    search_queries = state['search_queries']
    all_results = []
    
    for query in search_queries:
        # Call the tool for each query
        search_results = google_search_tool.invoke({"query": query})
        all_results.extend(search_results)

    return {"raw_search_results": all_results}

# Step 4: Define logic to determine whether to end
from typing import Literal
from langgraph.graph import StateGraph, START, END

# Step 5: Build agent
# Build workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("generate_icp_node", generate_icp_node)
workflow.add_node("generate_queries_node", generate_queries_node)
workflow.add_node("execute_search_node", execute_search_node)

# Add edges to connect nodes
workflow.add_edge(START, "generate_icp_node")
workflow.add_edge("generate_icp_node", "generate_queries_node")
workflow.add_edge("generate_queries_node", "execute_search_node")
workflow.add_edge("execute_search_node", END)

# Compile the agent
agent = workflow.compile()

# Invoke with product_description extracted from human message
human_message_content = "I'm a 52 years old woman creator in Pontchâteau, France and I create beautiful decoration pieces dreamcatchers, macramé pieces and ojo del dios. I already expose in 3 stores but I'd like to live from it."
human_message = HumanMessage(content=human_message_content)

# Create initial state with product_description from human message
initial_state = {
    "product_description": human_message_content,  # Extract product description from human message
    "messages": [human_message],
    "icp": {},
    "search_queries": {},
    "raw_search_results": [],
    "prospects": [],
    "personalized_outreach": [],
    "llm_calls": 0
}

# Invoke the agent
result = agent.invoke(initial_state)

print('-'*50)
print('\n')
for i, result in enumerate(result['raw_search_results']):
    print(f'Result number {i+1}: {result}')








