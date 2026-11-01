import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns


def _numeric_series(df: pd.DataFrame, column: str | None) -> pd.Series | None:
    if not column or column not in df.columns:
        return None
    return pd.to_numeric(df[column], errors="coerce")


def _metric(value, available: bool, description: str, source=None) -> dict:
    return {
        "value": value,
        "available": available,
        "description": description,
        "source": source,
    }


def calculate_business_kpis(df: pd.DataFrame, mapping: dict | None = None) -> dict:
    """Calculate core business KPIs only when the mapped source fields support them."""
    _validate_dataframe(df)
    mapping = mapping or map_business_columns(df)["mapping"]

    revenue_role = mapping.get("revenue")
    revenue = None
    revenue_source = None

    if isinstance(revenue_role, dict) and revenue_role.get("type") == "derived":
        quantity_column, price_column = revenue_role.get("depends_on", [None, None])
        quantity = _numeric_series(df, quantity_column)
        unit_price = _numeric_series(df, price_column)
        if quantity is not None and unit_price is not None:
            revenue = quantity * unit_price
            revenue_source = f"Derived from {quantity_column} × {price_column}"
    elif isinstance(revenue_role, str):
        revenue = _numeric_series(df, revenue_role)
        revenue_source = revenue_role

    total_revenue = (
        round(float(revenue.sum()), 2)
        if revenue is not None and revenue.notna().any()
        else None
    )

    order_column = mapping.get("order_id")
    order_count = (
        int(df[order_column].nunique(dropna=True))
        if isinstance(order_column, str) and order_column in df.columns
        else None
    )

    customer_column = mapping.get("customer_id")
    customer_count = (
        int(df[customer_column].nunique(dropna=True))
        if isinstance(customer_column, str) and customer_column in df.columns
        else None
    )

    product_column = mapping.get("product_id")
    product_count = (
        int(df[product_column].nunique(dropna=True))
        if isinstance(product_column, str) and product_column in df.columns
        else None
    )

    quantity_column = mapping.get("quantity")
    quantity = _numeric_series(df, quantity_column if isinstance(quantity_column, str) else None)
    total_units = (
        round(float(quantity.sum()), 2)
        if quantity is not None and quantity.notna().any()
        else None
    )

    average_order_value = (
        round(total_revenue / order_count, 2)
        if total_revenue is not None and order_count is not None and order_count > 0
        else None
    )

    unit_price_column = mapping.get("unit_price")
    unit_prices = _numeric_series(
        df, unit_price_column if isinstance(unit_price_column, str) else None
    )
    average_unit_price = (
        round(float(unit_prices.mean()), 2)
        if unit_prices is not None and unit_prices.notna().any()
        else None
    )

    profit_column = mapping.get("profit")
    profit_values = _numeric_series(
        df, profit_column if isinstance(profit_column, str) else None
    )
    total_profit = (
        round(float(profit_values.sum()), 2)
        if profit_values is not None and profit_values.notna().any()
        else None
    )

    metrics = {
        "total_revenue": _metric(
            total_revenue, total_revenue is not None,
            "Sum of the mapped revenue field or quantity multiplied by unit price.",
            revenue_source,
        ),
        "total_orders": _metric(
            order_count, order_count is not None,
            "Distinct non-null order or invoice identifiers.", order_column,
        ),
        "average_order_value": _metric(
            average_order_value, average_order_value is not None,
            "Total revenue divided by distinct orders.",
            "total_revenue / total_orders",
        ),
        "total_units_sold": _metric(
            total_units, total_units is not None,
            "Sum of the mapped quantity field.", quantity_column,
        ),
        "unique_customers": _metric(
            customer_count, customer_count is not None,
            "Distinct non-null customer identifiers.", customer_column,
        ),
        "unique_products": _metric(
            product_count, product_count is not None,
            "Distinct non-null product identifiers.", product_column,
        ),
        "average_unit_price": _metric(
            average_unit_price, average_unit_price is not None,
            "Mean of the mapped unit-price field.", unit_price_column,
        ),
        "total_profit": _metric(
            total_profit, total_profit is not None,
            "Sum of an explicitly mapped profit field. Profit is not inferred from cost.",
            profit_column,
        ),
    }

    unavailable = [
        name for name, metric in metrics.items() if not metric["available"]
    ]

    return {
        "row_count": int(len(df)),
        "metrics": metrics,
        "unavailable_metrics": unavailable,
        "mapping": mapping,
        "notes": [
            "Order count uses distinct identifiers, not row count.",
            "Profit is reported only when an explicit profit field is available.",
        ],
    }
