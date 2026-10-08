import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.executor import execute_analysis


DATA_FILE = PROJECT_ROOT / "data" / "sample_-_superstore.xls"


def load_data():
    """Load the Superstore dataset."""

    df = pd.read_excel(DATA_FILE)

    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    df = df.drop_duplicates()

    return df


def compare_values(actual, expected):
    """Compare common pandas/Python result types."""

    if isinstance(expected, pd.DataFrame):
        if not isinstance(actual, pd.DataFrame):
            return False

        return actual.reset_index(drop=True).equals(
            expected.reset_index(drop=True)
        )

    if isinstance(expected, pd.Series):
        if isinstance(actual, pd.DataFrame):
            actual = actual.squeeze()

        if not isinstance(actual, pd.Series):
            return False

        return actual.reset_index(drop=True).equals(
            expected.reset_index(drop=True)
        )

    if isinstance(expected, float):
        try:
            return abs(float(actual) - expected) < 0.01
        except Exception:
            return False

    if isinstance(expected, int):
        try:
            return int(actual) == expected
        except Exception:
            return False

    return actual == expected


def run_test(df, number, question, code, expected):

    try:
        actual, fig = execute_analysis(code, df)

        passed = compare_values(actual, expected)

        status = "PASS" if passed else "FAIL"

        print(f"{number:02d}. {status} - {question}")

        if not passed:
            print(f"    Expected: {expected}")
            print(f"    Actual:   {actual}")

        return passed

    except Exception as error:

        print(f"{number:02d}. ERROR - {question}")
        print(f"    {error}")

        return False


def main():

    print("=" * 70)
    print("AI DATA ANALYSIS APP - EVALUATION")
    print("=" * 70)

    df = load_data()

    print(f"\nDataset: {DATA_FILE.name}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print()

    tests = [

        # =====================================================
        # BASIC DATASET QUESTIONS
        # =====================================================

        (
            "How many rows are in the dataset?",
            "result = len(df)",
            len(df),
        ),

        (
            "How many columns are in the dataset?",
            "result = len(df.columns)",
            len(df.columns),
        ),

        (
            "How many unique customers are there?",
            "result = df['Customer ID'].nunique()",
            int(df["Customer ID"].nunique()),
        ),

        (
            "How many unique products are there?",
            "result = df['Product ID'].nunique()",
            int(df["Product ID"].nunique()),
        ),

        (
            "How many orders are there?",
            "result = df['Order ID'].nunique()",
            int(df["Order ID"].nunique()),
        ),

        # =====================================================
        # OVERALL METRICS
        # =====================================================

        (
            "What is the total sales?",
            "result = df['Sales'].sum()",
            float(df["Sales"].sum()),
        ),

        (
            "What is the total profit?",
            "result = df['Profit'].sum()",
            float(df["Profit"].sum()),
        ),

        (
            "What is the average sales per record?",
            "result = df['Sales'].mean()",
            float(df["Sales"].mean()),
        ),

        (
            "What is the average profit per record?",
            "result = df['Profit'].mean()",
            float(df["Profit"].mean()),
        ),

        (
            "What is the total quantity sold?",
            "result = df['Quantity'].sum()",
            int(df["Quantity"].sum()),
        ),

        (
            "What is the average discount?",
            "result = df['Discount'].mean()",
            float(df["Discount"].mean()),
        ),

        (
            "What is the average quantity per record?",
            "result = df['Quantity'].mean()",
            float(df["Quantity"].mean()),
        ),

        (
            "What is the overall profit margin?",
            "result = (df['Profit'].sum() / df['Sales'].sum()) * 100",
            float((df["Profit"].sum() / df["Sales"].sum()) * 100),
        ),

        (
            "How many records have negative profit?",
            "result = int((df['Profit'] < 0).sum())",
            int((df["Profit"] < 0).sum()),
        ),

        # =====================================================
        # CATEGORY ANALYSIS
        # =====================================================

        (
            "Which category has the highest sales?",
            "result = df.groupby('Category')['Sales'].sum().idxmax()",
            df.groupby("Category")["Sales"].sum().idxmax(),
        ),

        (
            "Which category has the highest profit?",
            "result = df.groupby('Category')['Profit'].sum().idxmax()",
            df.groupby("Category")["Profit"].sum().idxmax(),
        ),

        (
            "What is the total sales for Technology?",
            "result = df.loc[df['Category'] == 'Technology', 'Sales'].sum()",
            float(
                df.loc[
                    df["Category"] == "Technology",
                    "Sales"
                ].sum()
            ),
        ),

        (
            "What is the total profit for Technology?",
            "result = df.loc[df['Category'] == 'Technology', 'Profit'].sum()",
            float(
                df.loc[
                    df["Category"] == "Technology",
                    "Profit"
                ].sum()
            ),
        ),

        (
            "What is the total sales for Furniture?",
            "result = df.loc[df['Category'] == 'Furniture', 'Sales'].sum()",
            float(
                df.loc[
                    df["Category"] == "Furniture",
                    "Sales"
                ].sum()
            ),
        ),

        (
            "What is the total profit for Furniture?",
            "result = df.loc[df['Category'] == 'Furniture', 'Profit'].sum()",
            float(
                df.loc[
                    df["Category"] == "Furniture",
                    "Profit"
                ].sum()
            ),
        ),

        # =====================================================
        # REGION ANALYSIS
        # =====================================================

        (
            "Which region has the highest sales?",
            "result = df.groupby('Region')['Sales'].sum().idxmax()",
            df.groupby("Region")["Sales"].sum().idxmax(),
        ),

        (
            "Which region has the highest profit?",
            "result = df.groupby('Region')['Profit'].sum().idxmax()",
            df.groupby("Region")["Profit"].sum().idxmax(),
        ),

        (
            "What is the total sales in the West region?",
            "result = df.loc[df['Region'] == 'West', 'Sales'].sum()",
            float(
                df.loc[
                    df["Region"] == "West",
                    "Sales"
                ].sum()
            ),
        ),

        (
            "What is the total profit in the West region?",
            "result = df.loc[df['Region'] == 'West', 'Profit'].sum()",
            float(
                df.loc[
                    df["Region"] == "West",
                    "Profit"
                ].sum()
            ),
        ),

        (
            "What is the total sales in the East region?",
            "result = df.loc[df['Region'] == 'East', 'Sales'].sum()",
            float(
                df.loc[
                    df["Region"] == "East",
                    "Sales"
                ].sum()
            ),
        ),

        (
            "What is the total profit in the East region?",
            "result = df.loc[df['Region'] == 'East', 'Profit'].sum()",
            float(
                df.loc[
                    df["Region"] == "East",
                    "Profit"
                ].sum()
            ),
        ),

        # =====================================================
        # SEGMENT ANALYSIS
        # =====================================================

        (
            "Which segment has the highest sales?",
            "result = df.groupby('Segment')['Sales'].sum().idxmax()",
            df.groupby("Segment")["Sales"].sum().idxmax(),
        ),

        (
            "Which segment has the highest profit?",
            "result = df.groupby('Segment')['Profit'].sum().idxmax()",
            df.groupby("Segment")["Profit"].sum().idxmax(),
        ),

        (
            "What is the total sales for the Consumer segment?",
            "result = df.loc[df['Segment'] == 'Consumer', 'Sales'].sum()",
            float(
                df.loc[
                    df["Segment"] == "Consumer",
                    "Sales"
                ].sum()
            ),
        ),

        (
            "What is the total profit for the Consumer segment?",
            "result = df.loc[df['Segment'] == 'Consumer', 'Profit'].sum()",
            float(
                df.loc[
                    df["Segment"] == "Consumer",
                    "Profit"
                ].sum()
            ),
        ),

        # =====================================================
        # SUB-CATEGORY ANALYSIS
        # =====================================================

        (
            "What is the most profitable sub-category?",
            "result = df.groupby('Sub-Category')['Profit'].sum().idxmax()",
            df.groupby("Sub-Category")["Profit"].sum().idxmax(),
        ),

        (
            "Which sub-category has the highest sales?",
            "result = df.groupby('Sub-Category')['Sales'].sum().idxmax()",
            df.groupby("Sub-Category")["Sales"].sum().idxmax(),
        ),

        (
            "Which sub-category has the lowest profit?",
            "result = df.groupby('Sub-Category')['Profit'].sum().idxmin()",
            df.groupby("Sub-Category")["Profit"].sum().idxmin(),
        ),

        # =====================================================
        # PRODUCT ANALYSIS
        # =====================================================

        (
            "Which product has the highest total sales?",
            "result = df.groupby('Product Name')['Sales'].sum().idxmax()",
            df.groupby("Product Name")["Sales"].sum().idxmax(),
        ),

        (
            "Which product has the highest total profit?",
            "result = df.groupby('Product Name')['Profit'].sum().idxmax()",
            df.groupby("Product Name")["Profit"].sum().idxmax(),
        ),

        # =====================================================
        # BUSINESS / PROFITABILITY QUESTIONS
        # =====================================================

        (
            "Which category has the lowest total profit?",
            "result = df.groupby('Category')['Profit'].sum().idxmin()",
            df.groupby("Category")["Profit"].sum().idxmin(),
        ),

        (
            "Which region has the lowest total profit?",
            "result = df.groupby('Region')['Profit'].sum().idxmin()",
            df.groupby("Region")["Profit"].sum().idxmin(),
        ),

        (
            "Which segment has the lowest total profit?",
            "result = df.groupby('Segment')['Profit'].sum().idxmin()",
            df.groupby("Segment")["Profit"].sum().idxmin(),
        ),

        (
            "What is the total sales from the Consumer segment in the West region?",
            "result = df.loc[(df['Segment'] == 'Consumer') & (df['Region'] == 'West'), 'Sales'].sum()",
            float(
                df.loc[
                    (df["Segment"] == "Consumer")
                    & (df["Region"] == "West"),
                    "Sales"
                ].sum()
            ),
        ),

        (
            "What is the total profit from the Consumer segment in the West region?",
            "result = df.loc[(df['Segment'] == 'Consumer') & (df['Region'] == 'West'), 'Profit'].sum()",
            float(
                df.loc[
                    (df["Segment"] == "Consumer")
                    & (df["Region"] == "West"),
                    "Profit"
                ].sum()
            ),
        ),

        # =====================================================
        # DATE ANALYSIS
        # =====================================================

        (
            "What year has the highest sales?",
            "result = df.groupby(df['Order Date'].dt.year)['Sales'].sum().idxmax()",
            df.groupby(
                df["Order Date"].dt.year
            )["Sales"].sum().idxmax(),
        ),

        (
            "What year has the highest profit?",
            "result = df.groupby(df['Order Date'].dt.year)['Profit'].sum().idxmax()",
            df.groupby(
                df["Order Date"].dt.year
            )["Profit"].sum().idxmax(),
        ),

    ]

    passed = 0

    for number, (question, code, expected) in enumerate(
        tests,
        start=1
    ):

        if run_test(
            df,
            number,
            question,
            code,
            expected
        ):
            passed += 1

    total = len(tests)
    accuracy = (passed / total) * 100

    print()
    print("=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)

    print(f"Passed:   {passed}/{total}")
    print(f"Failed:   {total - passed}/{total}")
    print(f"Accuracy: {accuracy:.1f}%")

    print("=" * 70)


if __name__ == "__main__":
    main()