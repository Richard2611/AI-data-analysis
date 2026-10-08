import streamlit as st
import pandas as pd

from src.cleaning import clean_data
from src.llm import generate_analysis_code
from src.executor import execute_analysis
from src.insights import generate_executive_summary
from src.export import create_excel_export


# ---------------------------------------------------------
# Page setup
# ---------------------------------------------------------

st.set_page_config(
    page_title="AI Data Analysis App",
    layout="wide"
)

st.title("AI Data Analysis App")

st.write(
    "Upload a CSV or Excel file and analyze it using "
    "natural language."
)


# ---------------------------------------------------------
# File upload
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload your data",
    type=["csv", "xlsx", "xls"]
)


if uploaded_file is not None:

    # -----------------------------------------------------
    # Load data
    # -----------------------------------------------------

    try:

        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)

        else:
            df = pd.read_excel(uploaded_file)

    except Exception as e:

        st.error(
            f"Could not read the file: {e}"
        )

        st.stop()


    # -----------------------------------------------------
    # Clean data
    # -----------------------------------------------------

    cleaned_df, report = clean_data(df)


    # -----------------------------------------------------
    # Cleaning Report
    # -----------------------------------------------------

    st.subheader("Cleaning Report")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Original Rows",
        report["original_rows"]
    )

    col2.metric(
        "Final Rows",
        report["final_rows"]
    )

    col3.metric(
        "Duplicates Removed",
        report["duplicates_removed"]
    )

    col4.metric(
        "Missing Values",
        f"{report['missing_values_found']} → "
        f"{report['missing_values_remaining']}"
    )


    # -----------------------------------------------------
    # Cleaning Actions
    # -----------------------------------------------------

    with st.expander("View Cleaning Actions"):

        st.write(
            f"- Removed {report['empty_rows_removed']} "
            f"completely empty rows"
        )

        st.write(
            f"- Removed {report['duplicates_removed']} "
            f"duplicate rows"
        )

        st.write(
            f"- Removed {report['empty_columns_removed']} "
            f"completely empty columns"
        )

        st.write(
            f"- Detected {report['missing_values_found']} "
            f"missing values"
        )

        st.write(
            f"- Remaining missing values: "
            f"{report['missing_values_remaining']}"
        )

        st.write(
            "- Standardized column names"
        )


    # -----------------------------------------------------
    # Data Preview
    # -----------------------------------------------------

    st.subheader("Data Preview")

    st.dataframe(
        cleaned_df.head(10),
        use_container_width=True
    )


    # -----------------------------------------------------
    # Executive Summary
    # -----------------------------------------------------

    st.divider()

    st.subheader("Executive Summary")

    if st.button("Generate Executive Summary"):

        summary = generate_executive_summary(
            cleaned_df
        )

        st.markdown("### Key Insights")

        for insight in summary["insights"]:

            st.write(
                f"• {insight}"
            )

        st.markdown("### Recommendation")

        st.info(
            summary["recommendation"]
        )


    # -----------------------------------------------------
    # Excel Export
    # -----------------------------------------------------

    st.divider()

    st.subheader("Export")

    excel_file = create_excel_export(
        cleaned_df
    )

    st.download_button(
        label="Download Cleaned Excel File",
        data=excel_file,
        file_name="cleaned_data.xlsx",
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )


    # -----------------------------------------------------
    # AI Analysis
    # -----------------------------------------------------

    st.divider()

    st.subheader("Ask Your Data")

    question = st.text_input(
        "Ask a question about your dataset",
        placeholder=(
            "Example: What are the top 10 products by profit?"
        )
    )


    if st.button(
        "Analyze",
        type="primary"
    ):

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "AI is analyzing your data..."
            ):

                last_error = None
                analysis = None
                result = None
                fig = None


                # Three total attempts
                for attempt in range(3):

                    try:

                        analysis = generate_analysis_code(
                            cleaned_df,
                            question,
                            previous_error=last_error
                        )

                        result, fig = execute_analysis(
                            analysis["code"],
                            cleaned_df
                        )

                        last_error = None

                        break

                    except Exception as error:

                        last_error = str(error)


                # -------------------------------------------------
                # Failure
                # -------------------------------------------------

                if last_error is not None:

                    st.error(
                        "The AI could not successfully "
                        "answer the question."
                    )

                    with st.expander(
                        "Technical Error"
                    ):

                        st.code(
                            last_error,
                            language="text"
                        )

                    st.stop()


                # -------------------------------------------------
                # Explanation
                # -------------------------------------------------

                st.subheader("Analysis")

                st.write(
                    analysis["explanation"]
                )


                # -------------------------------------------------
                # Result
                # -------------------------------------------------

                st.subheader("Result")


                if isinstance(
                    result,
                    pd.DataFrame
                ):

                    st.dataframe(
                        result,
                        use_container_width=True
                    )

                elif isinstance(
                    result,
                    pd.Series
                ):

                    st.dataframe(
                        result.to_frame(),
                        use_container_width=True
                    )

                elif isinstance(
                    result,
                    dict
                ):

                    st.json(result)

                else:

                    st.metric(
                        "Answer",
                        str(result)
                    )


                # -------------------------------------------------
                # Chart
                # -------------------------------------------------

                if fig is not None:

                    st.subheader(
                        "Visualization"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )


                # -------------------------------------------------
                # Generated Code
                # -------------------------------------------------

                with st.expander(
                    "View Generated Python Code"
                ):

                    st.code(
                        analysis["code"],
                        language="python"
                    )