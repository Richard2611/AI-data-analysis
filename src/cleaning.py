import pandas as pd


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

    # Handle missing values
    for column in cleaned_df.columns:

        if cleaned_df[column].dtype.kind in "biufc":
            cleaned_df[column] = cleaned_df[column].fillna(
                cleaned_df[column].median()
            )

        elif cleaned_df[column].dtype == "object":
            cleaned_df[column] = cleaned_df[column].fillna("Unknown")

    # Standardize column names
    cleaned_df.columns = (
        cleaned_df.columns
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
    }

    return cleaned_df, report