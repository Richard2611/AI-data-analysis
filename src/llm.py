import json
import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables from .env
load_dotenv()


# Create OpenAI client
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY was not found. "
        "Make sure your .env file contains your API key."
    )

client = OpenAI(api_key=api_key)


# Model can be changed through .env
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


# ---------------------------------------------------------
# Build dataset context
# ---------------------------------------------------------

def build_data_context(df):
    """
    Create a small description of the dataset for the LLM.

    The full dataset is NEVER sent to the API.
    Only column names, data types, and 5 sample rows are included.
    """

    columns = []

    for column in df.columns:
        columns.append(
            {
                "name": str(column),
                "dtype": str(df[column].dtype),
            }
        )

    sample = (
        df.head(5)
        .astype(object)
        .where(pd.notna(df.head(5)), None)
        .to_dict(orient="records")
    )

    context = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "sample_rows": sample,
    }

    return json.dumps(context, default=str, indent=2)


# ---------------------------------------------------------
# Generate analysis code
# ---------------------------------------------------------

def generate_analysis_code(df, question, previous_error=None):
    """
    Ask the LLM to convert a natural-language question
    into pandas/Plotly analysis code.
    """

    data_context = build_data_context(df)

    error_context = ""

    if previous_error:
        error_context = f"""
The previous generated code failed with this error:

{previous_error}

Fix the code so that the error does not occur again.
"""


    system_prompt = """
You are the analysis engine for an AI Data Analyst application.

Your job is to translate a user's natural-language data question
into safe pandas and Plotly code.

The dataframe is already loaded into a variable called `df`.

Available libraries:

- pandas as pd
- plotly.express as px
- plotly.graph_objects as go

IMPORTANT RULES:

1. Use ONLY the dataframe `df`.
2. Do not load files.
3. Do not access the internet.
4. Do not use requests, urllib, subprocess, os, sys, pathlib,
   socket, shutil, importlib, or any other external module.
5. Do not read or write files.
6. Do not execute shell commands.
7. Do not define functions.
8. Do not use classes.
9. Do not use eval() or exec().
10. Do not access environment variables.
11. Do not access the filesystem.
12. Do not modify the original dataframe.
13. Create calculations using pandas.
14. For charts, use Plotly Express or Plotly Graph Objects.
15. The final analysis result must be stored in a variable called `result`.
16. If a chart is appropriate, store it in a variable called `fig`.
17. If no chart is needed, set `fig = None`.
18. Keep the generated code short and readable.
19. Never invent columns that are not present in the dataset.
20. Use the exact column names supplied in the dataset context.
21. If a column name contains spaces or special characters,
    use df["column name"] rather than df.column_name.
22. Return a useful result even when the user asks a simple question.
23. For numeric questions, calculate the answer from the data.
24. Do not guess or manually invent numerical results.

The code should generally follow this pattern:

result = ...
fig = ...

The `result` variable may be:
- a pandas DataFrame
- a pandas Series
- a numeric value
- a string
- a dictionary

If the user asks for a chart, create an appropriate Plotly figure.

The explanation must describe what the generated analysis does,
not fabricate findings that were not calculated.
"""


    user_prompt = f"""
DATASET INFORMATION:

{data_context}

USER QUESTION:

{question}

{error_context}

Generate the pandas/Plotly analysis required to answer the question.
"""


    # Structured output schema
    response_schema = {
        "type": "json_schema",
        "name": "analysis_code",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code that analyzes df."
                },
                "explanation": {
                    "type": "string",
                    "description": "Short explanation of what the code does."
                },
                "needs_chart": {
                    "type": "boolean",
                    "description": "Whether the analysis should display a chart."
                },
            },
            "required": [
                "code",
                "explanation",
                "needs_chart",
            ],
            "additionalProperties": False,
        },
    }


    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        text={
            "format": response_schema
        },
    )


    result = json.loads(response.output_text)

    return result