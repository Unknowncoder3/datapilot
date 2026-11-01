import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns


def _resolve_mapping(df: pd.DataFrame, mapping: dict | None) -> dict:
    return mapping or map_business_columns(df)["mapping"]


def _revenue_series(df: pd.DataFrame, mapping: dict) -> pd.Series:
    revenue_role = mapping.get("revenue")
    if isinstance(revenue_role, dict) and revenue_role.get("type") == "derived":
        quantity_col, price_col = revenue_role.get("depends_on", [None, None])
        if quantity_col not in df.columns or price_col not in df.columns:
            raise ValueError("Revenue mapping references missing columns.")
        quantity = pd.to_numeric(df[quantity_col], errors="coerce")
        price = pd.to_numeric(df[price_col], errors="coerce")
        return quantity * price
    if isinstance(revenue_role, str) and revenue_role in df.columns:
        return pd.to_numeric(df[revenue_role], errors="coerce")
    raise ValueError("Sales analysis requires a revenue field or quantity and unit price.")


def _date_series(df: pd.DataFrame, mapping: dict) -> pd.Series:
    column = mapping.get("date")
    if not isinstance(column, str) or column not in df.columns:
        raise ValueError("Sales trends require a mapped transaction date column.")
    return pd.to_datetime(df[column], errors="coerce")


def _base_sales_frame(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    frame = pd.DataFrame(index=df.index)
    frame["revenue"] = _revenue_series(df, mapping)
    frame["date"] = _date_series(df, mapping)
    order_col = mapping.get("order_id")
    if isinstance(order_col, str) and order_col in df.columns:
        frame["order_id"] = df[order_col]
        frame["is_cancelled"] = df[order_col].astype(str).str.upper().str.startswith("C")
    else:
        frame["order_id"] = None
        frame["is_cancelled"] = False
    quantity_col = mapping.get("quantity")
    if isinstance(quantity_col, str) and quantity_col in df.columns:
        frame["quantity"] = pd.to_numeric(df[quantity_col], errors="coerce")
    else:
        frame["quantity"] = None
    return frame


def get_sales_trends(
    df: pd.DataFrame,
    frequency: str = "month",
    mapping: dict | None = None,
) -> dict:
    """Aggregate signed sales by month or day and calculate comparable-period growth."""
    _validate_dataframe(df)
    if frequency not in {"month", "day"}:
        raise ValueError("Frequency must be 'month' or 'day'.")
    resolved = _resolve_mapping(df, mapping)
    frame = _base_sales_frame(df, resolved).dropna(subset=["date"])
    if frame.empty:
        raise ValueError("No valid transaction dates were found.")

    frame["period"] = (
        frame["date"].dt.to_period("M").astype(str)
        if frequency == "month"
        else frame["date"].dt.strftime("%Y-%m-%d")
    )
    grouped = frame.groupby("period", sort=True).agg(
        revenue=("revenue", "sum"),
        invoice_count=("order_id", "nunique"),
        transaction_rows=("revenue", "size"),
        cancelled_rows=("is_cancelled", "sum"),
        units=("quantity", "sum"),
    ).reset_index()

    results = []
    previous = None
    for row in grouped.to_dict(orient="records"):
        value = float(row["revenue"]) if pd.notna(row["revenue"]) else 0.0
        growth = None
        if previous is not None and previous > 0:
            growth = round(((value - previous) / previous) * 100, 2)
        results.append({
            "period": row["period"],
            "revenue": round(value, 2),
            "invoice_count": int(row["invoice_count"]),
            "transaction_rows": int(row["transaction_rows"]),
            "cancelled_rows": int(row["cancelled_rows"]),
            "units": round(float(row["units"]), 2) if pd.notna(row["units"]) else None,
            "growth_percent": growth,
        })
        previous = value

    return {
        "frequency": frequency,
        "periods": len(results),
        "results": results,
        "notes": [
            "Revenue is signed: negative quantities and values reduce net revenue.",
            "Cancelled invoice rows are identified by invoice numbers beginning with C; they remain included in revenue totals.",
            "Growth is omitted when the previous period has zero or negative revenue.",
        ],
    }


def get_sales_by_country(
    df: pd.DataFrame,
    limit: int = 20,
    mapping: dict | None = None,
) -> dict:
    _validate_dataframe(df)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("Limit must be an integer between 1 and 100.")
    resolved = _resolve_mapping(df, mapping)
    country_col = resolved.get("country")
    if not isinstance(country_col, str) or country_col not in df.columns:
        raise ValueError("Country performance requires a mapped country column.")
    frame = pd.DataFrame({
        "country": df[country_col].fillna("Unknown").astype(str),
        "revenue": _revenue_series(df, resolved),
    })
    grouped = frame.groupby("country", dropna=False).agg(
        revenue=("revenue", "sum"),
        transaction_rows=("revenue", "size"),
    ).sort_values("revenue", ascending=False).head(limit)
    results = [
        {"country": country, "revenue": round(float(row["revenue"]), 2),
         "transaction_rows": int(row["transaction_rows"])}
        for country, row in grouped.iterrows()
    ]
    return {"group_by": country_col, "returned_groups": len(results), "results": results}


def get_top_products(
    df: pd.DataFrame,
    limit: int = 20,
    mapping: dict | None = None,
) -> dict:
    _validate_dataframe(df)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("Limit must be an integer between 1 and 100.")
    resolved = _resolve_mapping(df, mapping)
    product_col = resolved.get("product_id")
    if not isinstance(product_col, str) or product_col not in df.columns:
        raise ValueError("Product performance requires a mapped product identifier.")
    name_col = resolved.get("product_name")
    frame = pd.DataFrame({
        "product_id": df[product_col].astype(str),
        "revenue": _revenue_series(df, resolved),
        "quantity": pd.to_numeric(df[resolved["quantity"]], errors="coerce")
        if isinstance(resolved.get("quantity"), str) and resolved["quantity"] in df.columns
        else 0,
    })
    if isinstance(name_col, str) and name_col in df.columns:
        frame["product_name"] = df[name_col].astype(str)
    else:
        frame["product_name"] = frame["product_id"]
    grouped = frame.groupby("product_id", dropna=False).agg(
        revenue=("revenue", "sum"),
        quantity=("quantity", "sum"),
        product_name=("product_name", "first"),
    ).sort_values("revenue", ascending=False).head(limit)
    results = [
        {"product_id": product_id, "product_name": row["product_name"],
         "revenue": round(float(row["revenue"]), 2),
         "quantity": round(float(row["quantity"]), 2)}
        for product_id, row in grouped.iterrows()
    ]
    return {"returned_products": len(results), "results": results}
