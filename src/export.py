import io
import pandas as pd


def create_excel_export(df):
    """
    Create an Excel file containing the cleaned dataset.
    """

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Cleaned Data"
        )

    output.seek(0)

    return output.getvalue()