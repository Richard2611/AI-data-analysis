# AI Data Analysis App

A Streamlit app where you upload a CSV or Excel file, it cleans the data automatically, writes an executive summary, and lets you ask questions about the data in plain English.

The workflow follows how a consultant works: **prepare the data → analyse → visualise → insight → recommendation**.

---

## What it does

1. **Upload** a CSV, XLSX or XLS file (or click **Try it with sample data** to see it work first).
2. **Clean** it automatically and review a before/after cleaning report.
3. **Summarise** it: key numbers and one recommendation, calculated directly from your data.
4. **Ask questions** in plain English and get a table, a chart and the Python code behind the answer.
5. **Download** the cleaned file as Excel, and any answer as CSV or an interactive chart.

---

## Features

### Upload
CSV, XLSX and XLS files. CSV files saved by Excel in a Windows encoding, or with `;` between columns, are read correctly.

### Automatic cleaning
- Removes completely empty rows and columns
- Removes duplicate rows
- Fills missing numbers with the column median and missing text with `Unknown`
- Standardises column names (`Order Date` becomes `order_date`)
- **Turns date text into real dates.** A text column is converted only when almost all of its values look like dates and almost all of them can be read. Day-first (`14/03/2025`) and month-first (`03/14/2025`) files are told apart when the data makes it clear. This is what lets questions like "sales over time" work.

### Executive summary
Calculated from the dataframe, not by the AI, so the numbers are never made up: totals, averages, profit margin, negative-profit records, the leading category, and a recommendation.

### Ask Your Data
- Type a question or click a **suggestion** built from your own column names.
- **Follow-up switch:** turn it on to build on the last answer ("now only for Dubai").
- Every answer is kept in the session. The newest is open, older ones fold away.
- If the generated code fails, the app retries up to 3 times, giving the AI the error each time.
- Each answer can be downloaded: the table as **CSV**, the chart as an **HTML** file (it loads Plotly from the internet, so open it while online).
- Only column names, column types and the **first 5 rows** are sent to the AI, plus your question (and, for a follow-up, the previous question and its code). The full dataset is never sent.

### Large files
Above 50,000 rows the Excel file is built only when you click **Prepare Excel file**, so the page stays fast. Files with 200,000 or more rows also show a notice that tables preview the first rows only and questions can take longer.

### Works without the AI
If no API key is set, the Ask tab explains how to add one. Upload, cleaning, summary and Excel download still work.

---

## Safe execution of AI-written code

The AI writes Python, and the app runs it. That code is checked and limited in layers:

1. **Code check before running.** Only a small set of Python operations is allowed. No imports, no function definitions, no dunder (`__x__`) access.
2. **Only safe parts of pandas and Plotly.** `pd`, `px` and `go` expose only data-analysis functions. Anything that reads or writes files (`read_*`, `to_csv`, `write_html` ...), evaluates text as code (`eval`, `query`) or reaches other modules (`pd.io`, `.format`) is blocked.
3. **Runtime guard.** While generated code runs, starting programs, opening network connections and writing or deleting files are refused, even if something got past the first two layers.
4. **Time limit.** Code that runs longer than 30 seconds is stopped. Stacked powers like `9 ** 9 ** 9` and huge whole-number powers are refused.

Because `df.query(...)` is blocked, the AI sometimes writes it first and then fixes itself on the retry.

**Limits.** This is a restricted execution layer, not a full sandbox. The time limit stops runaway Python loops, but cannot interrupt a single huge calculation that never returns to Python. If you host this for people you do not trust, also run the analysis in a separate container or process with CPU and memory limits.

This matters most for files from other people: the first 5 rows go to the AI, so text inside a file could try to steer it. The layers above are what keep that harmless.

---

## Setup

You need Python 3.10 or newer and a free [Groq API key](https://console.groq.com/keys).

```bash
# 1. install
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. add your key
cp .env.example .env             # Windows: copy .env.example .env
# open .env and replace your_key_here with your real key

# 3. run
streamlit run app_new.py
```

Optional: set `GROQ_MODEL` in `.env` to use a different Groq model.

### Deploying on Streamlit Community Cloud
1. Push the project to GitHub. `.env` is already in `.gitignore`, so your key stays private.
2. Create the app and set the main file to `app_new.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "your_key_here"
   ```

---

## Project structure

```text
app_new.py            the interface (tabs, chat, downloads)
src/
  cleaning.py         cleaning pipeline and date detection
  insights.py         executive summary (calculated, no AI)
  llm.py              asks Groq to write the analysis code
  executor.py         checks and runs the AI-written code
  export.py           builds the cleaned Excel file
.streamlit/
  config.toml         dark theme, hides the Deploy button
requirements.txt
.env.example          copy to .env and add your key
```

## How it fits together

```text
        CSV / Excel upload   (or sample data)
                  │
                  ▼
            Data cleaning
   empty rows · empty columns · duplicates
   missing values · column names · dates
                  │
      ┌───────────┼─────────────┐
      ▼           ▼             ▼
 Executive     Ask Your       Excel
  summary        Data        download
                  │
                  ▼
        AI writes pandas / Plotly code
        (sees column names + 5 rows only)
                  │
                  ▼
   Code check → runtime guard → 30 s limit
                  │
                  ▼
     Table · metric · chart · CSV / HTML download
```
