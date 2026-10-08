import pandas as pd


def _find_column(df, candidates):
    """Find the first matching column."""

    lower_map = {
        str(column).lower(): column
        for column in df.columns
    }

    for candidate in candidates:

        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


def generate_executive_summary(df):
    """
    Generate a consulting-style executive summary.

    All numbers are calculated directly from the dataframe.
    No LLM/API is used.
    """

    insights = []
    recommendation = None

    # -----------------------------------------------------
    # Identify common business columns
    # -----------------------------------------------------

    sales_col = _find_column(
        df,
        [
            "sales",
            "revenue",
            "total_sales",
            "amount",
            "value"
        ]
    )

    profit_col = _find_column(
        df,
        [
            "profit",
            "net_profit",
            "gross_profit"
        ]
    )

    quantity_col = _find_column(
        df,
        [
            "quantity",
            "units",
            "units_sold",
            "volume"
        ]
    )

    discount_col = _find_column(
        df,
        [
            "discount",
            "discount_rate",
            "discount_percent"
        ]
    )

    # -----------------------------------------------------
    # Dataset overview
    # -----------------------------------------------------

    insights.append(
        f"The dataset contains {len(df):,} records "
        f"across {len(df.columns)} variables."
    )

    # -----------------------------------------------------
    # Sales
    # -----------------------------------------------------

    if sales_col:

        sales = pd.to_numeric(
            df[sales_col],
            errors="coerce"
        )

        total_sales = sales.sum()
        average_sales = sales.mean()

        insights.append(
            f"Total {sales_col.replace('_', ' ')} is "
            f"{total_sales:,.2f}, with an average of "
            f"{average_sales:,.2f} per record."
        )

    # -----------------------------------------------------
    # Profit
    # -----------------------------------------------------

    if profit_col:

        profit = pd.to_numeric(
            df[profit_col],
            errors="coerce"
        )

        total_profit = profit.sum()

        negative_records = int(
            (profit < 0).sum()
        )

        insights.append(
            f"Total {profit_col.replace('_', ' ')} is "
            f"{total_profit:,.2f}; "
            f"{negative_records:,} records have negative profit."
        )

        if sales_col:

            sales = pd.to_numeric(
                df[sales_col],
                errors="coerce"
            )

            total_sales = sales.sum()

            if total_sales != 0:

                margin = (
                    total_profit / total_sales
                ) * 100

                insights.append(
                    f"Overall profit margin is "
                    f"{margin:.2f}%."
                )

    # -----------------------------------------------------
    # Quantity
    # -----------------------------------------------------

    if quantity_col:

        quantity = pd.to_numeric(
            df[quantity_col],
            errors="coerce"
        )

        insights.append(
            f"Total recorded volume is "
            f"{quantity.sum():,.0f} units."
        )

    # -----------------------------------------------------
    # Category / segment / region
    # -----------------------------------------------------

    category_col = _find_column(
        df,
        [
            "category",
            "segment",
            "region",
            "department",
            "product_category"
        ]
    )

    if category_col:

        metric_col = sales_col or profit_col

        if metric_col:

            grouped = (
                df.groupby(category_col)[metric_col]
                .sum()
                .sort_values(ascending=False)
            )

            if len(grouped) > 0:

                top_category = grouped.index[0]
                top_value = grouped.iloc[0]

                insights.append(
                    f"{top_category} is the leading "
                    f"{category_col.replace('_', ' ')} "
                    f"by {metric_col.replace('_', ' ')} "
                    f"at {top_value:,.2f}."
                )

                if sales_col and len(grouped) > 1:

                    share = (
                        top_value / grouped.sum()
                    ) * 100

                    insights.append(
                        f"The leading category represents "
                        f"{share:.1f}% of total sales."
                    )

                recommendation = (
                    f"Prioritize analysis of {top_category} "
                    f"while investigating the performance "
                    f"of lower-performing "
                    f"{category_col.replace('_', ' ')} groups."
                )

    # -----------------------------------------------------
    # Discount
    # -----------------------------------------------------

    if discount_col:

        discount = pd.to_numeric(
            df[discount_col],
            errors="coerce"
        )

        insights.append(
            f"Average {discount_col.replace('_', ' ')} "
            f"is {discount.mean():.2%}."
        )

    # -----------------------------------------------------
    # Fallback recommendation
    # -----------------------------------------------------

    if recommendation is None:

        if profit_col:

            profit = pd.to_numeric(
                df[profit_col],
                errors="coerce"
            )

            if (profit < 0).sum() > 0:

                recommendation = (
                    "Investigate the negative-profit records "
                    "to identify the main drivers of loss."
                )

            else:

                recommendation = (
                    "Focus further analysis on the highest-value "
                    "segments and identify the factors associated "
                    "with stronger profitability."
                )

        else:

            recommendation = (
                "Segment the dataset by key categorical variables "
                "and compare performance to identify improvement "
                "opportunities."
            )

    return {
        "insights": insights[:5],
        "recommendation": recommendation
    }