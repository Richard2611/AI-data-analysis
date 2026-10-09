import os
import json

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


# ============================================================
# Configuration
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is not set. Add it to your .env file locally "
        "or Streamlit Secrets when deploying."
    )


client = Groq(
    api_key=GROQ_API_KEY,
    timeout=30.0,
)


# ============================================================
# Generate analysis code
# ============================================================

def generate_analysis_code(df, question, previous_error=None):

    # --------------------------------------------------------
    # Dataset schema
    # --------------------------------------------------------

    column_info = [
        {
            "name": str(column),
            "dtype": str(df[column].dtype),
        }
        for column in df.columns
    ]

    # Only send a small sample to the LLM
    sample_data = df.head(5).to_dict(orient="records")


    # --------------------------------------------------------
    # Main prompt
    # --------------------------------------------------------

    prompt = f"""
You are an expert business data analyst.

Your task is to convert the user's natural-language question
into safe, executable Python code for a pandas DataFrame.

============================================================
DATASET
============================================================

Rows:
{len(df)}

Columns:
{json.dumps(column_info, indent=2)}

Sample data:
{json.dumps(sample_data, default=str, indent=2)}

============================================================
USER QUESTION
============================================================

{question}

============================================================
CODE GENERATION RULES
============================================================

1. The DataFrame is already available as `df`.

2. Use pandas as `pd`.

3. Use Plotly Express as `px` when a visualization is useful.

4. Use Plotly Graph Objects as `go` only when necessary.

5. Do NOT load files.

6. Do NOT access the filesystem.

7. Do NOT access the network.

8. Do NOT use:
   - os
   - sys
   - subprocess
   - requests
   - pathlib
   - open
   - eval
   - exec
   - import statements
   - external libraries

9. Do NOT modify the original DataFrame.

10. ALWAYS store the final analytical answer in a variable called `result`.

11. If a visualization is useful, store the Plotly figure in `fig`.

12. If no visualization is needed, set:
    fig = None

13. `result` MUST contain the underlying analytical result.

14. The underlying result can be:
    - pandas DataFrame
    - pandas Series
    - number
    - string
    - dictionary

15. NEVER set:
    result = fig

16. NEVER use a Plotly Figure as the value of `result`.

17. When a chart is requested, create the analytical result FIRST,
    then create the Plotly figure from that result.

18. Use only columns that actually exist in the dataset.

19. Use the exact column names provided above.

20. Keep the generated code concise.

21. Prefer straightforward pandas operations.

22. The generated code will be executed by a restricted
    AST-based Python executor.

============================================================
CORRECT CHART PATTERN
============================================================

For example, if the user asks:

"Show me the top 10 customers by sales as a bar chart."

Generate code following this pattern:

result = (
    df.groupby("customer_name", as_index=False)["sales"]
    .sum()
    .sort_values("sales", ascending=False)
    .head(10)
)

fig = px.bar(
    result,
    x="customer_name",
    y="sales",
    title="Top 10 Customers by Sales"
)

The important rule is:

result = analytical data
fig = visualization

NEVER:

result = fig

============================================================
NO-CHART PATTERN
============================================================

If the user asks:

"What is the total sales?"

Use:

result = df["sales"].sum()
fig = None

============================================================
CHART PATTERN
============================================================

If the user asks for a chart:

result = <data used for the analysis>

fig = px.bar(
    result,
    ...
)

============================================================
OUTPUT
============================================================

Return valid JSON with exactly these fields:

{{
    "explanation": "Short explanation of what the analysis does.",
    "code": "Executable Python code."
}}

Do not return markdown.

Do not wrap the JSON in ```.

============================================================
"""


    # --------------------------------------------------------
    # Retry context
    # --------------------------------------------------------

    if previous_error:
        prompt += f"""

============================================================
PREVIOUS EXECUTION ERROR
============================================================

The previously generated code failed with this error:

{previous_error}

Generate corrected Python code that fixes this error.

Do not repeat the same mistake.

============================================================
"""


    # --------------------------------------------------------
    # Call Groq
    # --------------------------------------------------------

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful business data analyst. "
                        "Generate concise, executable pandas and Plotly "
                        "code using only the provided dataset schema. "
                        "Always return valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
            response_format={
                "type": "json_object"
            },
        )

    except Exception as error:

        raise RuntimeError(
            f"Groq API request failed: {error}"
        )


    # --------------------------------------------------------
    # Extract response
    # --------------------------------------------------------

    if not response.choices:

        raise RuntimeError(
            "Groq returned no choices."
        )


    content = response.choices[0].message.content


    if not content:

        raise RuntimeError(
            "Groq returned an empty response."
        )


    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        result = json.loads(content)

    except json.JSONDecodeError as error:

        raise RuntimeError(
            f"Groq returned invalid JSON: {error}"
        )


    # --------------------------------------------------------
    # Validate response structure
    # --------------------------------------------------------

    if "code" not in result:

        raise RuntimeError(
            "Groq response did not contain generated code."
        )


    if "explanation" not in result:

        result["explanation"] = (
            "Analysis generated by the AI model."
        )


    return result