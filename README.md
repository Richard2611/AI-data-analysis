# AI Data Analysis App

A Streamlit-based data analysis application that allows users to upload CSV or Excel datasets, automatically clean the data, generate executive insights, and analyze the dataset using natural-language questions.

The project is designed around a consulting-style workflow: **data preparation → analysis → visualization → business insight → recommendation**.

---

## Project Overview

Business analysts often spend significant time cleaning datasets and writing repetitive analysis code before they can answer business questions.

This application provides a single workflow where a user can:

1. Upload a CSV or Excel dataset
2. Automatically clean and standardize the data
3. Review a detailed cleaning report
4. Generate an executive-style summary
5. Ask analytical questions in natural language
6. Execute generated pandas/Plotly analysis
7. View tables and visualizations
8. Export the cleaned dataset to Excel

---

## Key Features

### 1. Data Upload

Supports:

- CSV
- XLSX
- XLS

The application automatically detects the file type and loads the dataset using pandas.

### 2. Automated Data Cleaning

The cleaning pipeline handles:

- Completely empty rows
- Completely empty columns
- Duplicate records
- Missing values
- Column-name standardization

A cleaning report shows the impact of each operation.

### 3. Executive Summary

The application calculates consulting-style business insights directly from the dataset.

Examples include:

- Total sales
- Average sales
- Total profit
- Profit margin
- Negative-profit records
- Leading categories
- Sales concentration
- Business recommendations

The summary is calculated directly from the dataframe rather than relying on an LLM to invent numerical results.

### 4. Natural-Language Data Analysis

Users can ask questions such as:

> What are the top 10 products by profit?

or:

> Which region has the highest sales?

The application uses an LLM to translate the question into pandas/Plotly analysis code.

Only dataset metadata and a small sample of rows are provided to the model rather than the complete dataset.

### 5. Restricted Code Execution

Generated Python code is validated using Python's Abstract Syntax Tree (AST) before execution.

The execution layer restricts:

- Available Python operations
- Accessible names
- Functions
- Attributes
- Imports
- System access
- File access
- Network access

This provides a controlled environment for executing generated analytical code.

> Note: AST validation is a safety layer, not a perfect security sandbox. A production deployment handling untrusted users should additionally isolate code execution using containers or another dedicated sandboxing mechanism.

### 6. Excel Export

After cleaning, users can download the processed dataset as:

`cleaned_data.xlsx`

---

## Architecture

```text
                 ┌─────────────────────┐
                 │     CSV / Excel      │
                 │       Upload         │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    Data Cleaning    │
                 │                     │
                 │ • Empty rows        │
                 │ • Empty columns     │
                 │ • Duplicates        │
                 │ • Missing values    │
                 │ • Column names      │
                 └──────────┬──────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
      ┌────────────┐ ┌────────────┐ ┌──────────────┐
      │ Executive  │ │   Natural  │ │    Excel     │
      │  Summary   │ │  Language  │ │    Export    │
      │            │ │  Analysis  │ │              │
      └────────────┘ └─────┬──────┘ └──────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ LLM generates │
                   │ pandas/Plotly │
                   │     code      │
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ AST Security  │
                   │  Validation   │
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │    Execute    │
                   │  Analysis     │
                   └───────┬───────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │ Table / Metric /    │
                 │ Plotly Visualization│
                 └─────────────────────┘