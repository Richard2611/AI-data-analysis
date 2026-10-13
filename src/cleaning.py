import re

import pandas as pd


# Text that looks like a date: 2025-03-14, 14/03/2025, 3.14.25, "14 Mar 2025"
# (non-capturing groups so pandas does not warn about match groups)
DATE_PATTERN = re.compile(
    r"(?:\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})"
    r"|(?:\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b)",
    re.IGNORECASE,
)


# 14/03/2025 or 03-14-2025: first and second number, to tell day-first
# from month-first
DAY_MONTH_PATTERN = re.compile(r"^\s*(\d{1,2})[-/.](\d{1,2})[-/.]\d{2,4}")


def _guess_day_first(values):
    """
    True when the column is clearly day/month/year, False when it is
    clearly month/day/year. A column where every value could be either
    (like 03/04/2025) is read month-first, the pandas default.
    """

    first_over_12 = False
    second_over_12 = False

    for text in values.head(500):

        match = DAY_MONTH_PATTERN.match(text)

        if not match:
            continue

        if int(match.group(1)) > 12:
            first_over_12 = True

        if int(match.group(2)) > 12:
            second_over_12 = True

    return first_over_12 and not second_over_12


def _is_text_column(series):
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    )


def _standard_name(name):
    return str(name).strip().lower().replace(" ", "_")


def _convert_date_columns(cleaned_df):
    """
    Turn text columns that clearly contain dates into real datetime columns.

    A column is converted only when almost all of its values look like
    dates AND almost all of them can be parsed.
    """

    converted = []

    for column in cleaned_df.columns:

        series = cleaned_df[column]

        if not _is_text_column(series):
            continue

        values = series.dropna().astype(str).str.strip()
        values = values[values != ""]

        if values.empty:
            continue

        looks_like_date = values.head(200).str.contains(DATE_PATTERN)

        if looks_like_date.mean() < 0.9:
            continue

        day_first = _guess_day_first(values)

        try:
            parsed = pd.to_datetime(
                series,
                errors="coerce",
                format="mixed",
                dayfirst=day_first,
            )
        except (TypeError, ValueError):
            # older pandas has no format="mixed"
            parsed = pd.to_datetime(
                series, errors="coerce", dayfirst=day_first
            )

        if parsed.notna().sum() < 0.9 * len(values):
            continue

        cleaned_df[column] = parsed
        converted.append(column)

    return converted


def clean_data(df):
    cleaned_df = df.copy()

    original_rows = len(cleaned_df)
    original_columns = len(cleaned_df.columns)

    # Remove completely empty rows
    empty_rows_removed = int(cleaned_df.isna().all(axis=1).sum())
    cleaned_df = cleaned_df.dropna(axis=0, how="all")

    # Remove completely empty columns
    empty_columns_removed = int(cleaned_df.isna().all(axis=0).sum())
    cleaned_df = cleaned_df.dropna(axis=1, how="all")

    # Remove duplicate rows
    duplicates_removed = int(cleaned_df.duplicated().sum())
    cleaned_df = cleaned_df.drop_duplicates()

    # Count missing values before handling
    missing_values_found = int(cleaned_df.isna().sum().sum())

    # Convert text columns that hold dates into real dates
    # (must happen before missing text is replaced with "Unknown")
    date_columns = _convert_date_columns(cleaned_df)

    # Handle missing values
    for column in cleaned_df.columns:

        if cleaned_df[column].dtype.kind in "biufc":
            cleaned_df[column] = cleaned_df[column].fillna(
                cleaned_df[column].median()
            )

        elif _is_text_column(cleaned_df[column]):
            cleaned_df[column] = cleaned_df[column].fillna("Unknown")

    # Standardize column names
    cleaned_df.columns = (
        cleaned_df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Final report
    report = {
        "original_rows": original_rows,
        "final_rows": len(cleaned_df),
        "rows_removed": original_rows - len(cleaned_df),
        "original_columns": original_columns,
        "final_columns": len(cleaned_df.columns),
        "columns_removed": original_columns - len(cleaned_df.columns),
        "empty_rows_removed": empty_rows_removed,
        "empty_columns_removed": empty_columns_removed,
        "duplicates_removed": duplicates_removed,
        "missing_values_found": missing_values_found,
        "missing_values_remaining": int(cleaned_df.isna().sum().sum()),
        "date_columns_converted": len(date_columns),
        "date_columns": [_standard_name(c) for c in date_columns],
    }

    return cleaned_df, report
