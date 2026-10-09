
import hashlib
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.cleaning import clean_data
from src.llm import generate_analysis_code
from src.executor import execute_analysis
from src.insights import generate_executive_summary
from src.export import create_excel_export


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Insight | Data Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "page": "Overview",
    "file_hash": None,
    "raw_df": None,
    "cleaned_df": None,
    "cleaning_report": None,
    "filename": None,
    "executive_summary": None,
    "analysis_history": [],
    "analysis_result": None,
    "analysis_code": None,
    "analysis_question": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


PAGES = [
    "Overview",
    "Export & Data",
    "Executive Summary",
    "Ask Your Data",
]


# ============================================================
# NAVIGATION FIX
# ============================================================

def set_page(page):
    """Update the active page and sidebar selection together."""
    st.session_state.page = page
    st.session_state.workspace_navigation = page


def on_page_change():
    """Update the active page when the sidebar radio changes."""
    st.session_state.page = st.session_state.workspace_navigation


def render_other_page_options(current_page):
    """Show shortcuts to the other analysis pages in homepage order."""
    page_options = [
        ("Export & Data", "Export Data", "nav_export_from_page"),
        ("Executive Summary", "Executive Summary", "nav_summary_from_page"),
        ("Ask Your Data", "Ask Your Data", "nav_ask_from_page"),
    ]
    available = [item for item in page_options if item[0] != current_page]

    if not available:
        return

    st.divider()
    st.markdown("### Continue your analysis")
    st.caption("Move to another part of your workspace.")

    for target_page, label, key in available:
        st.button(
            label,
            key=f"{key}_{current_page.replace(' ', '_').replace('&', 'and')}",
            type="primary",
            use_container_width=True,
            on_click=set_page,
            args=(target_page,),
        )


if "workspace_navigation" not in st.session_state:
    st.session_state.workspace_navigation = st.session_state.page


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F7F9FC;
        color: #172033;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }

    h1, h2, h3, h4 {
        color: #101828 !important;
        font-weight: 700 !important;
    }

    p, label, li {
        color: #344054;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E4E7EC;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #101828 !important;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 12px;
        padding: 18px;
    }

    [data-testid="stMetricLabel"] {
        color: #344054 !important;
    }

    [data-testid="stMetricLabel"] p {
        color: #344054 !important;
    }

    [data-testid="stMetricValue"] {
        color: #101828 !important;
    }

    [data-testid="stMetricDelta"] {
        color: #475467 !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #000000 !important;
        border-radius: 8px !important;
        min-height: 44px;
        font-weight: 600;
    }

    div[data-testid="stButton"] > button[kind="primary"] p,
    div[data-testid="stButton"] > button[kind="primary"] span {
        color: #FFFFFF !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #262626 !important;
        border-color: #262626 !important;
    }

    div[data-testid="stButton"] > button[kind="secondary"] {
        border-radius: 8px !important;
    }

    [data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 1px dashed #98A2B3;
        border-radius: 12px;
        padding: 12px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #E4E7EC;
        border-radius: 8px;
    }

    [data-testid="stExpander"] {
        background-color: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 8px;
    }

    .hero-card {
        background-color: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 22px;
    }

    .hero-eyebrow {
        color: #175CD3;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    .hero-title {
        color: #101828;
        font-size: 36px;
        line-height: 1.2;
        font-weight: 750;
        margin-bottom: 14px;
    }

    .hero-description {
        color: #475467;
        font-size: 16px;
        line-height: 1.7;
        max-width: 760px;
    }

    .section-caption {
        color: #667085;
        font-size: 14px;
    }

    .sidebar-footer {
        color: #667085;
        font-size: 12px;
        padding-top: 20px;
    }

    /* Keep typed questions readable in the Ask Your Data input. */
    div[data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important;
        color: #101828 !important;
        -webkit-text-fill-color: #101828 !important;
        caret-color: #101828 !important;
        border: 1px solid #D0D5DD !important;
        border-radius: 8px !important;
    }

    div[data-testid="stTextArea"] textarea::placeholder {
        color: #667085 !important;
        -webkit-text-fill-color: #667085 !important;
        opacity: 1 !important;
    }

    div[data-testid="stTextArea"] textarea:focus {
        border: 1px solid #175CD3 !important;
        box-shadow: 0 0 0 1px #175CD3 !important;
    }


    /* Consistent high-contrast buttons, including form submit buttons. */
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stButton"] button[kind="primary"] {
        background: #111827 !important;
        color: #FFFFFF !important;
        border: 1px solid #111827 !important;
        border-radius: 9px !important;
        min-height: 44px;
        font-weight: 600 !important;
        transition: background 0.15s ease-in-out;
    }

    div[data-testid="stFormSubmitButton"] button p,
    div[data-testid="stFormSubmitButton"] button span,
    div[data-testid="stButton"] button[kind="primary"] p,
    div[data-testid="stButton"] button[kind="primary"] span {
        color: #FFFFFF !important;
    }

    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #344054 !important;
        border-color: #344054 !important;
    }

    /* Give results a cleaner, more structured visual hierarchy. */
    [data-testid="stMetric"] {
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }

    [data-testid="stAlert"] {
        border-radius: 10px !important;
    }

    div[data-testid="stCode"] {
        border-radius: 10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA HELPERS
# ============================================================

def normalize_generated_code(response):
    """Extract Python code from common AI response formats."""
    import json
    import re

    if isinstance(response, dict):
        response = (
            response.get("code")
            or response.get("python_code")
            or response.get("analysis_code")
            or response.get("content")
            or ""
        )

    if not isinstance(response, str):
        raise ValueError(
            f"Expected Python code as text, received {type(response).__name__}."
        )

    response = response.strip()

    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict):
            response = (
                parsed.get("code")
                or parsed.get("python_code")
                or parsed.get("analysis_code")
                or parsed.get("content")
                or response
            )
    except (json.JSONDecodeError, ValueError):
        pass

    if not isinstance(response, str):
        raise ValueError("The AI response did not contain Python code as text.")

    response = response.strip()
    response = re.sub(
        r"^\s*```(?:python|py)?\s*", "", response, flags=re.IGNORECASE
    )
    response = re.sub(r"\s*```\s*$", "", response).strip()

    if not response:
        raise ValueError("The AI returned an empty code response.")

    return response


def read_uploaded_file(uploaded_file):
    """Read a supported CSV or Excel file into a DataFrame."""
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    if filename.endswith(".csv"):
        try:
            return pd.read_csv(BytesIO(file_bytes))
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(file_bytes), encoding="latin-1")

    if filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(file_bytes))

    raise ValueError("Unsupported file type. Upload a CSV or Excel file.")


def load_dataset(uploaded_file):
    """Load and clean a new dataset, storing it in session state."""
    file_bytes = uploaded_file.getvalue()
    current_hash = hashlib.md5(file_bytes).hexdigest()

    if current_hash == st.session_state.file_hash:
        return False

    raw_df = read_uploaded_file(uploaded_file)

    if raw_df.empty and len(raw_df.columns) == 0:
        raise ValueError("The uploaded file does not contain any data.")

    cleaned_df, cleaning_report = clean_data(raw_df.copy())

    st.session_state.file_hash = current_hash
    st.session_state.raw_df = raw_df
    st.session_state.cleaned_df = cleaned_df
    st.session_state.cleaning_report = cleaning_report
    st.session_state.filename = uploaded_file.name
    st.session_state.executive_summary = None
    st.session_state.analysis_history = []
    st.session_state.analysis_result = None
    st.session_state.analysis_code = None
    st.session_state.analysis_question = ""

    return True


def report_value(report, key, default=0):
    """Safely read a value from the cleaning report."""
    if isinstance(report, dict):
        return report.get(key, default)
    return default


def display_cleaning_report(report):
    """Display available cleaning statistics."""
    if not isinstance(report, dict):
        st.info("Cleaning report is unavailable.")
        return

    preferred_labels = {
        "rows_removed": "Rows removed",
        "empty_rows_removed": "Empty rows removed",
        "duplicates_removed": "Duplicates removed",
        "missing_values_found": "Missing values found",
        "missing_values_remaining": "Missing values remaining",
    }

    available_items = [
        (label, report[key])
        for key, label in preferred_labels.items()
        if key in report
    ]

    if available_items:
        columns = st.columns(min(4, len(available_items)))

        for index, (label, value) in enumerate(available_items):
            with columns[index % len(columns)]:
                st.metric(label, value)

    with st.expander("View complete cleaning report"):
        st.json(report)


def show_dataset_required():
    """Show a consistent message when a page needs an uploaded dataset."""
    st.info(
        "Upload a CSV or Excel dataset from the Overview page to use this feature."
    )

    if st.button(
        "Go to Overview",
        key="go_overview_empty",
        type="primary",
    ):
        set_page("Overview")
        st.rerun()


def display_analysis_result(result, question=""):
    """Render analysis output as readable results rather than raw Python objects."""
    if result is None:
        st.warning("The analysis did not return a result.")
        return

    # The executor commonly returns (result, figure). Render each part separately.
    if isinstance(result, tuple):
        value = result[0] if len(result) > 0 else None
        figure = result[1] if len(result) > 1 else None

        if value is not None:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if any(word in question.lower() for word in ("percent", "percentage", "%")):
                    display_value = f"{value:,.2f}%"
                    label = "Result"
                else:
                    display_value = f"{value:,.2f}"
                    label = "Result"
                st.metric(label, display_value)
            else:
                display_analysis_result(value, question)

        if figure is not None:
            if hasattr(figure, "to_plotly_json"):
                st.plotly_chart(figure, use_container_width=True)
            else:
                st.write(figure)
        return

    if isinstance(result, pd.DataFrame):
        st.dataframe(result, use_container_width=True)
        return

    if isinstance(result, pd.Series):
        st.dataframe(result.to_frame(), use_container_width=True)
        return

    if isinstance(result, (int, float)) and not isinstance(result, bool):
        if any(word in question.lower() for word in ("percent", "percentage", "%")):
            st.metric("Result", f"{result:,.2f}%")
        else:
            st.metric("Result", f"{result:,.2f}")
        return

    if isinstance(result, bool):
        st.write("Yes" if result else "No")
        return

    if isinstance(result, dict):
        for key, value in result.items():
            st.markdown(f"**{key.replace('_', ' ').title()}**")
            st.write(value)
        return

    if isinstance(result, list):
        for item in result:
            st.write(item)
        return

    if hasattr(result, "to_plotly_json"):
        st.plotly_chart(result, use_container_width=True)
        return

    st.write(result)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0 24px 0;">
            <div style="font-size: 27px; font-weight: 800; color: #101828;">
                Insight<span style="color: #175CD3;">.</span>
            </div>
            <div style="font-size: 12px; color: #667085;">
                AI-powered data analysis
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### WORKSPACE")

    st.radio(
        "Workspace navigation",
        PAGES,
        label_visibility="collapsed",
        key="workspace_navigation",
        format_func=lambda page: {
            "Overview": "◉  Overview",
            "Export & Data": "▤  Export Data",
            "Executive Summary": "↗  Executive Summary",
            "Ask Your Data": "⌕  Ask Your Data",
        }[page],
        on_change=on_page_change,
    )

    st.divider()

    if st.session_state.cleaned_df is not None:
        st.markdown("#### CURRENT DATASET")
        st.caption(st.session_state.filename or "Uploaded dataset")
        st.caption(
            f"{len(st.session_state.cleaned_df):,} rows · "
            f"{len(st.session_state.cleaned_df.columns):,} columns"
        )
        st.success("Dataset ready")
    else:
        st.markdown("#### CURRENT DATASET")
        st.caption("No dataset uploaded")
        st.info("Upload a dataset to get started.")

    st.markdown(
        """
        <div class="sidebar-footer">
            Insight · Data Analysis Workspace
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# OVERVIEW PAGE
# ============================================================

if st.session_state.page == "Overview":

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">DATA ANALYSIS WORKSPACE</div>
            <div class="hero-title">Turn your data into decisions.</div>
            <div class="hero-description">
                Upload a spreadsheet, automatically clean your data,
                ask questions in plain English, and generate insights
                without writing analysis code yourself.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.cleaned_df is None:

        st.markdown("### Start with your dataset")
        st.caption(
            "Upload a CSV or Excel file to begin your analysis."
        )

        uploaded_file = st.file_uploader(
            "Choose your dataset",
            type=["csv", "xlsx", "xls"],
            key="main_page_uploader",
            help="Supported formats: CSV, XLSX and XLS.",
        )

        if uploaded_file is not None:
            try:
                with st.spinner("Loading and cleaning your dataset..."):
                    load_dataset(uploaded_file)

                st.success("Dataset uploaded and cleaned successfully.")
                st.rerun()

            except Exception as error:
                st.error(f"Could not process this file: {error}")

        st.markdown("### What you can do")

        feature1, feature2, feature3 = st.columns(3)

        with feature1:
            st.markdown("#### Ask questions")
            st.caption(
                "Explore your data using natural-language questions."
            )

        with feature2:
            st.markdown("#### Generate insights")
            st.caption(
                "Create an executive summary of important findings."
            )

        with feature3:
            st.markdown("#### Export results")
            st.caption(
                "Download your cleaned dataset as an Excel file."
            )

    else:

        df = st.session_state.cleaned_df

        st.markdown("### Dataset overview")
        st.caption(
            f"Currently analysing: **{st.session_state.filename}**"
        )

        metric1, metric2, metric3, metric4 = st.columns(4)

        with metric1:
            st.metric("Rows", f"{len(df):,}")

        with metric2:
            st.metric("Columns", f"{len(df.columns):,}")

        with metric3:
            st.metric(
                "Duplicates removed",
                report_value(
                    st.session_state.cleaning_report,
                    "duplicates_removed",
                    0,
                ),
            )

        with metric4:
            st.metric(
                "Missing values found",
                report_value(
                    st.session_state.cleaning_report,
                    "missing_values_found",
                    0,
                ),
            )

        st.markdown("### Data preview")
        st.dataframe(
            df.head(10),
            use_container_width=True,
            height=350,
        )

        with st.expander("Cleaning report"):
            display_cleaning_report(st.session_state.cleaning_report)

        st.divider()

        st.markdown("### Continue your analysis")
        st.caption("Choose what you want to do next.")

        st.button(
            "1. Export Data",
            key="continue_export",
            type="primary",
            use_container_width=True,
            on_click=set_page,
            args=("Export & Data",),
        )

        st.button(
            "2. Executive Summary",
            key="continue_summary",
            type="primary",
            use_container_width=True,
            on_click=set_page,
            args=("Executive Summary",),
        )

        st.button(
            "3. Ask Your Data",
            key="continue_ask",
            type="primary",
            use_container_width=True,
            on_click=set_page,
            args=("Ask Your Data",),
        )

        with st.expander("Upload a different dataset"):
            replacement_file = st.file_uploader(
                "Choose another CSV or Excel file",
                type=["csv", "xlsx", "xls"],
                key="replacement_uploader",
            )

            if replacement_file is not None:
                try:
                    replacement_hash = hashlib.md5(
                        replacement_file.getvalue()
                    ).hexdigest()

                    if replacement_hash != st.session_state.file_hash:
                        with st.spinner(
                            "Loading and cleaning the new dataset..."
                        ):
                            load_dataset(replacement_file)

                        st.success("Dataset replaced successfully.")
                        st.rerun()

                except Exception as error:
                    st.error(f"Could not process this file: {error}")


# ============================================================
# ASK YOUR DATA PAGE
# ============================================================

elif st.session_state.page == "Ask Your Data":

    st.title("Ask Your Data")
    st.caption(
        "Ask a question in plain English and let AI generate the analysis."
    )

    if st.session_state.cleaned_df is None:
        show_dataset_required()

    else:
        df = st.session_state.cleaned_df

        with st.expander("Explore available columns"):
            st.write(list(df.columns))
            st.dataframe(df.head(5), use_container_width=True)

        with st.form("analysis_form"):
            question = st.text_area(
                "What would you like to find out?",
                value=st.session_state.analysis_question,
                placeholder=(
                    "Examples:\n"
                    "- Which products generate the highest profit?\n"
                    "- Show sales by region as a bar chart.\n"
                    "- Which category has the lowest profit?"
                ),
                height=120,
                key="analysis_question_input",
            )

            submitted = st.form_submit_button(
                "Analyse data",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not question.strip():
                st.warning("Please enter a question first.")

            else:
                # Save the question before calling the model so it remains visible
                # even if code generation or execution fails.
                st.session_state.analysis_question = question.strip()
                code = None
                result = None
                last_error = None
                success = False

                with st.spinner(
                    "Generating and running your analysis..."
                ):
                    for attempt in range(3):
                        try:
                            response = generate_analysis_code(
                                df,
                                question.strip(),
                                previous_error=last_error,
                            )
                            code = normalize_generated_code(response)
                            result = execute_analysis(code, df)
                            success = True
                            break

                        except Exception as error:
                            last_error = str(error)

                if success:
                    st.session_state.analysis_result = result
                    st.session_state.analysis_code = code

                    st.session_state.analysis_history.append(
                        {
                            "question": question.strip(),
                            "code": code,
                        }
                    )

                    st.success("Analysis completed.")

                else:
                    st.error("The analysis failed after three attempts.")
                    if last_error:
                        st.markdown("**Last error:**")
                        st.code(str(last_error))

        if st.session_state.analysis_result is not None:
            st.divider()
            st.markdown("### Analysis result")
            st.markdown(
                f"**Question:** {st.session_state.analysis_question}"
            )

            display_analysis_result(
                st.session_state.analysis_result,
                st.session_state.analysis_question,
            )

            with st.expander("View generated Python code"):
                st.code(
                    st.session_state.analysis_code or "",
                    language="python",
                )

        if st.session_state.analysis_history:
            with st.expander("Previous questions"):
                for index, item in enumerate(
                    reversed(st.session_state.analysis_history),
                    start=1,
                ):
                    st.markdown(
                        f"**{index}.** {item['question']}"
                    )

    render_other_page_options("Ask Your Data")


# ============================================================
# EXECUTIVE SUMMARY PAGE
# ============================================================

elif st.session_state.page == "Executive Summary":

    st.title("Executive Summary")
    st.caption(
        "Generate a concise overview of the key findings in your dataset."
    )

    if st.session_state.cleaned_df is None:
        show_dataset_required()

    else:
        df = st.session_state.cleaned_df

        st.markdown("### Dataset at a glance")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Records", f"{len(df):,}")

        with col2:
            st.metric("Fields", f"{len(df.columns):,}")

        with col3:
            st.metric(
                "Numeric fields",
                len(df.select_dtypes(include="number").columns),
            )

        if st.button(
            "Generate executive summary",
            key="generate_executive_summary",
            type="primary",
            use_container_width=True,
        ):
            try:
                with st.spinner("Generating your executive summary..."):
                    st.session_state.executive_summary = generate_executive_summary(df)
            except Exception as error:
                st.error(f"Could not generate the summary: {error}")

        if st.session_state.executive_summary is not None:
            import json

            st.divider()
            st.markdown("### Key findings")
            summary = st.session_state.executive_summary

            if isinstance(summary, str):
                try:
                    parsed = json.loads(summary)
                    if isinstance(parsed, (dict, list)):
                        summary = parsed
                except (json.JSONDecodeError, ValueError):
                    pass

            if isinstance(summary, dict):
                insights = summary.get("insights", [])
                recommendation = summary.get("recommendation", "")

                if isinstance(insights, list):
                    for i, insight in enumerate(insights, start=1):
                        st.markdown(f"**{i}.** {insight}")
                elif insights:
                    st.markdown(str(insights))

                if recommendation:
                    st.markdown("### Recommended next step")
                    st.info(str(recommendation))

                if not insights and not recommendation:
                    st.write(summary)

            elif isinstance(summary, list):
                for i, insight in enumerate(summary, start=1):
                    st.markdown(f"**{i}.** {insight}")
            else:
                st.markdown(str(summary))

    render_other_page_options("Executive Summary")

# ============================================================
# EXPORT & DATA PAGE
# ============================================================

elif st.session_state.page == "Export & Data":

    st.title("Export & Data")
    st.caption(
        "Review the cleaned dataset and download it for further analysis."
    )

    if st.session_state.cleaned_df is None:
        show_dataset_required()

    else:
        df = st.session_state.cleaned_df

        st.markdown("### Cleaned dataset")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Rows", f"{len(df):,}")

        with col2:
            st.metric("Columns", f"{len(df.columns):,}")

        with col3:
            st.metric(
                "Missing values remaining",
                int(df.isna().sum().sum()),
            )

        st.dataframe(
            df,
            use_container_width=True,
            height=450,
        )

        st.markdown("### Download")

        st.caption(
            "Export the cleaned dataset to an Excel workbook."
        )

        try:
            excel_file = create_excel_export(df)

            if isinstance(excel_file, bytes):
                download_data = excel_file
            elif hasattr(excel_file, "getvalue"):
                download_data = excel_file.getvalue()
            else:
                download_data = excel_file

            st.download_button(
                label="Download cleaned Excel file",
                data=download_data,
                file_name="cleaned_dataset.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                type="primary",
                use_container_width=True,
            )

        except Exception as error:
            st.error(f"Could not prepare the Excel export: {error}")

        st.divider()
        st.markdown("### Cleaning report")
        display_cleaning_report(st.session_state.cleaning_report)


    render_other_page_options("Export & Data")
