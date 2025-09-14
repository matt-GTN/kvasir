from langchain_core.prompts import ChatPromptTemplate

generate_icp_prompt = ChatPromptTemplate.from_template(
    """
    You are a world-class B2B Go-To-Market strategist. Your task is to analyze the following product description and generate a structured, actionable Ideal Customer Profile (ICP) in JSON format.

    Focus on identifying firmographic, technographic, and persona-based details that can be used for targeted prospecting.

    **Product Description:**
    {product_description}

    **Instructions:**
    1.  **Firmographics:** Identify the industry, company size (employee count), and potential geographic locations.
    2.  **Technographics:** What specific technologies must the company be using to be a good fit? (e.g., cloud providers, specific software, code repositories).
    3.  **Key Personas:** Identify at least two key job titles/roles. For each persona, detail their primary pain points that the product solves and potential buying triggers (events or signals that indicate they need a solution now).

    **Don't format for markdown, don't add backticks or json keyword, output the result as a single, clean JSON object. Do not include any other text or explanation before or after the JSON. '**

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

generate_queries_prompt = ChatPromptTemplate.from_template(
     """
    You are a Lead Generation Specialist who is an expert in using advanced search operators (Google Dorks) to find qualified prospects. Your task is to generate a list of 5 diverse and effective Google search queries based on the provided Ideal Customer Profile (ICP).

    **Ideal Customer Profile (ICP):**
    {icp}

    **Instructions:**
    1.  Create queries specifically designed to find individuals on LinkedIn. Use the `site:linkedin.com/in/` operator.
    2.  Combine persona titles with industry keywords and company signals (like hiring or funding).
    3.  Create at least one query to find company blogs or engineering blogs that discuss the persona's pain points.
    4.  The queries should be creative and aim for high-quality, relevant results.
    5.  Don't format for markdown, output the result as a clean, single JSON list of strings. Do not include any other text.

    **Example Output:**
    ["query 1", "query 2", "query 3", "query 4", "query 5"]
    """   
)