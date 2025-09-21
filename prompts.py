from langchain_core.prompts import ChatPromptTemplate

generate_icp_prompt = ChatPromptTemplate.from_template(
    """
    You are a world-class B2B Go-To-Market strategist. Your task is to analyze the following product description and generate a structured, actionable Ideal Customer Profile (ICP) in JSON format.

    Focus on identifying firmographic, technographic, and persona-based details that can be used for targeted prospecting.

    **Product Context:**
    {product_context}

    **Instructions:**
    1.  **Firmographics:** Identify the industry, company size (employee count), and potential geographic locations.
    2.  **Technographics:** What specific technologies must the company be using to be a good fit? (e.g., cloud providers, specific software, code repositories).
    3.  **Key Personas:** Identify at least two key job titles/roles. For each persona, detail their primary pain points that the product solves and potential buying triggers (events or signals that indicate they need a solution now).
    
    **Match the **Product Context** language and output the result as a single, clean JSON object. Do not include any other text or explanation before or after the JSON. '**

    **JSON Schema:**
    {{
      "summary": "A brief, one-sentence summary of the ICP.",
      "firmographics": {{
        "industries": ["...", "..."],
        "company_size_employees": [min, max],
        "geography": ["..."]
      }},
      "technographics": {{
        "required": ["..."],
        "preferred": ["..."]
      }},
      "key_personas": [
        {{
          "title": "...",
          "department": "...",
          "pain_points": [
            "...",
            "..."
          ],
          "buying_triggers": [
            "Recent security incident or data breach.",
            "Company is scaling its engineering team rapidly.",
            "Preparing for compliance audits like SOC 2."
          ]
        }}
      ]
    }}
    """
)

strategy_selection_prompt = ChatPromptTemplate.from_template(
    """
    You are a master Go-To-Market strategist. Your task is to analyze an Ideal Customer Profile (ICP) and determine the most effective prospecting strategy.

    **Available Strategies:**

    1.  **"PERSON_FIRST_LINKEDIN":** This strategy is best when the key personas are easily identifiable by their job titles on professional networks. It focuses on searching LinkedIn directly. Use this for well-defined corporate roles (e.g., "VP of Engineering", "Marketing Manager") in industries like Tech, SaaS, Finance, etc.
    
    2.  **"COMPANY_FIRST_LOCAL":** This strategy is best when the target is small, local businesses that may not have a strong LinkedIn presence. The goal is to find the businesses first (boutiques, agencies, workshops) using general web search, and then find the people within them. Use this for local services, retail, hospitality, etc.

    **Ideal Customer Profile (ICP):**
    {icp}

    **Your Task:**
    1.  Analyze the ICP and choose the single most appropriate strategy from the list above.
    2.  Provide a brief rationale for your choice, matching the **Ideal Customer Profile (ICP)** language.
    3.  Output the result as a single, clean JSON object.

    **JSON Schema:**
    {{
      "strategy_name": "...",
      "rationale": "..."
    }}
    """
)

generate_queries_prompt = ChatPromptTemplate.from_template(
    """
    You are a lead generation expert who crafts perfect Google search queries.
    Your task is to generate a list of 5 search queries based on the provided strategy, Ideal Customer Profile (ICP), and Product Context.

    **Chosen Strategy:** {strategy_name}
    **Ideal Customer Profile (ICP):** {icp}
    **Product Context:** {product_context}

    ---
    **Feedback on Previous Attempt (if any):**
    {error_message}
    ---

    **Instructions:**
    - The queries should be designed to find potential direct sales channels, distributors, partners, or end-users.
    - **If feedback is provided above, you MUST generate a completely new and different set of queries to avoid repeating the previous failure.** Think about using different keywords, broader industries, or alternative job titles.
    - **IF the strategy is "PERSON_FIRST_LINKEDIN"**: Generate queries that use the `site:linkedin.com/in/` operator...
    - **IF the strategy is "COMPANY_FIRST_LOCAL"**: Generate general web search queries...
    - Ensure queries are precise enough to target commercial entities...

    Output the result as a clean JSON array of strings.
    """
)

filter_search_results_prompt = ChatPromptTemplate.from_template(
    """
    You are a meticulous filter for B2B lead generation. Your task is to review a list of raw Google search results and identify only those that represent **direct commercial entities or partnership opportunities** relevant to the `Product Context` and `Ideal Customer Profile (ICP)`.

    **Product Context:**
    {product_context}

    **Ideal Customer Profile (ICP):**
    {icp}

    **Input Search Results (a list of JSON objects, each with 'title', 'link', 'snippet'):**
    {raw_search_results}

    **Instructions:**
    1.  For each search result, critically evaluate if the entity's *primary business function* aligns with the `Product Context` and `ICP`.
    2.  **Explicitly INCLUDE only:**
        *   Businesses whose core operation is selling, distributing, integrating, or providing services directly related to the `Product Context`.
        *   Commercial entities that directly fit the industry types, company size, and geographical focus defined in the `ICP`.
        *   Companies where a direct commercial relationship (e.g., as a reseller, partner, or client) for the product/service is clearly viable based on their offering.
    3.  **Strictly and Absolutely EXCLUDE:**
        *   **Any governmental, regional support organization, chamber of commerce, business development agency, or non-profit organization.**
        *   **Tourism boards, local guides, news articles, general blogs, forums, social media posts that are not the primary business profile of a relevant commercial entity, or purely informational websites.** Do NOT include these even if they mention suitable businesses; focus only on the actual businesses' direct sites.
        *   **Personal profiles or individual social media accounts not clearly representing a commercial entity relevant to the ICP.**
        *   **Generic listing platforms or broad directories** unless the ICP specifically targets these as a direct sales/partnership channel. Focus on finding the individual businesses themselves.

    4.  Output *only* a JSON array containing the 'title', 'link' (use 'url' as the key for consistency with later nodes), and 'snippet' of the **qualifying and relevant** search results. Do not add any other text or explanation.

    **JSON Schema for output (only relevant results):**
    [
      {{
        "title": "Search Result Title",
        "url": "https://www.companywebsite.com/",
        "snippet": "Descriptive text from the search result."
      }}
    ]
    """
)

parse_results_prompt = ChatPromptTemplate.from_template(
    """
    You are a data extraction expert. Your task is to accurately extract specific details from the provided search results into a structured list of prospects. These search results have already been filtered for relevance; your sole focus is on precise data extraction.

    **Input Search Results (a list of JSON objects, already filtered for relevance):**
    {search_results}

    **Instructions:**
    1.  For each search result in the input list, extract the 'name', 'title', 'url', and 'snippet'.
    2.  The 'name' should be the clear and concise company or entity name found in the search result.
    3.  The 'title' should be the exact search result title.
    4.  The 'url' should be the exact link provided.
    5.  The 'snippet' should be the exact descriptive text from the search result.
    6.  All extracted data (name, title, snippet) should match the language of the original input.
    7.  Output the final result as a single, clean JSON array of dictionaries. Do not add any other text or explanation before or after the JSON.

    **JSON Schema:**
    [
      {{
        "name": "Company Name",
        "title": "Search Result Title (e.g., Company Name - Product Type)",
        "url": "https://www.companywebsite.com/",
        "snippet": "Short descriptive text from the search result."
      }}
    ]
    """
)

personalization_prompt = ChatPromptTemplate.from_template(
    """
    You are a world-class sales development representative fluent in many languages. Your task is to write 3 distinct, hyper-personalized opening lines for a cold email based on deep research. The lines will have to match the language of the **PRODUCT CONTEXT**.

    **PRODUCT CONTEXT:**
    {product_context}

    **PROSPECT INFORMATION:**
    - Name: {prospect_name}
    - Title: {prospect_title}
    - URL: {prospect_url}

    **RESEARCHED CONTENT FROM THEIR URL:**
    ---
    {researched_content}
    ---

    **YOUR TASK:**
    Write 3 unique and compelling opening lines for an email to {prospect_name}. Each opener must be based on a different angle. The tone should be respectful, observant, and focused on providing value to the prospect's business. Do NOT write the full email, only the opening lines.

    1.  **Angle 1 (The "Shared Vision/Aesthetic" Angle):** Identify a core aesthetic, value, or mission from the `product_context` (e.g., craftsmanship, innovation, sustainability, unique design, problem-solving) and connect it to something specific you observed in the `researched_content` of the prospect's business (e.g., their product selection, brand identity, customer testimonials, recent initiatives).
    2.  **Angle 2 (The "Strategic Alignment" Angle):** Based on the `product_context` and the `prospect_information`, find a point of strategic or operational relevance. This could be a geographic connection if the product is locally produced, a shared target audience, a complementary product category, or an alignment with their business goals. If the `product_context` mentions a specific location, leverage that for a "local connection" if relevant to the prospect.
    3.  **Angle 3 (The "Business Impact" Angle):** Frame how the product described in the `product_context` could bring concrete benefits to the prospect's business, such as attracting new customers, enhancing their existing offerings, solving a particular pain point (as inferred from the `researched_content` or general industry knowledge), or increasing revenue/differentiation.

    Output the result as a clean JSON object.

    **JSON Schema:**
    {{
      "shared_vision_aesthetic": "...",
      "strategic_alignment": "...",
      "business_impact": "..."
    }}
    """
)

generate_company_queries_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are an expert market researcher. Your task is to generate a list of 5-7 Google search queries to find lists of companies that are a perfect fit for the given Ideal Customer Profile (ICP) and product context.

**Your Goal:** Generate queries that will find articles, directories, blog posts, and market reports listing multiple potential customer companies. Do NOT generate queries to find individuals yet.

**Good Query Examples:**
- "Top US-based SaaS companies with 50-200 employees"
- "Fastest growing FinTech startups in the United States 2024"
- "List of e-commerce companies using React for their storefront"
- "Inc 5000 list technology sector"

**Bad Query Examples (DO NOT DO THIS):**
- "site:linkedin.com/in/ 'CTO' 'SaaS'"
- "CEO of tech companies"

**Instructions:**
1.  Analyze the ICP and product context.
2.  Brainstorm 5-7 creative and effective search queries to find lists of companies.
3.  Return the queries as a JSON list of strings.

**Product Context:**
{product_context}

**Ideal Customer Profile (ICP):**
{icp}
"""),
    ("user", "Please generate the company search queries based on the provided context and ICP."),
])

parse_companies_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a data parsing expert. Your task is to read through a list of Google search results and extract a clean list of company names that are relevant to the provided ICP.

**Instructions:**
1.  Carefully review each search result's title and snippet.
2.  Identify and extract the names of companies mentioned.
3.  Ignore individuals, articles without company names, and irrelevant entries.
4.  Deduplicate the list of company names.
5.  Return a single JSON object with a key "companies" containing a list of the extracted company names.

**Example Output:**
{{
  "companies": [
    "Stripe",
    "Plaid",
    "Brex",
    "Ramp"
  ]
}}

**Ideal Customer Profile (for context):**
{icp}

**Raw Google Search Results:**
{raw_search_results}
"""),
    ("user", "Please parse the search results and extract the company names."),
])

generate_person_queries_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are an expert in LinkedIn search. Your task is to generate a series of targeted Google search queries to find specific decision-makers (personas) within a given list of companies.

**Instructions:**
1.  Look at the `key_personas` from the ICP. Extract their titles (e.g., "CTO", "Head of Product").
2.  For each company in the `company_list`, create a search query for each key persona.
3.  Use boolean operators like "OR" to combine similar titles (e.g., "CTO OR 'Chief Technology Officer' OR 'VP of Engineering'").
4.  Combine all generated queries into a single JSON list of strings.

**Ideal Customer Profile (ICP):**
{icp}

**List of Target Companies:**
{company_list}
"""),
    ("user", "Please generate the person-specific LinkedIn search queries."),
])