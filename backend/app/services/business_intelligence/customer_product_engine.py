import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns


def _resolve_mapping(df: pd.DataFrame, mapping: dict | None) -> dict:
    return mapping or map_business_columns(df)["mapping"]


def _revenue_series(df: pd.DataFrame, mapping: dict) -> pd.Series:
    role = mapping.get("revenue")
    if isinstance(role, dict) and role.get("type") == "derived":
        quantity_col, price_col = role.get("depends_on", [None, None])
        if quantity_col not in df.columns or price_col not in df.columns:
            raise ValueError("Revenue mapping references missing columns.")
        return (
            pd.to_numeric(df[quantity_col], errors="coerce")
            * pd.to_numeric(df[price_col], errors="coerce")
        )
    if isinstance(role, str) and role in df.columns:
        return pd.to_numeric(df[role], errors="coerce")
    raise ValueError("Customer and product analysis requires revenue or quantity and unit price.")


def _require_column(df: pd.DataFrame, mapping: dict, role: str, label: str) -> str:
    column = mapping.get(role)
    if not isinstance(column, str) or column not in df.columns:
        raise ValueError(f"{label} requires a mapped {role.replace('_', ' ')} column.")
    return column


def get_customer_intelligence(
    df: pd.DataFrame, limit: int = 20, mapping: dict | None = None
) -> dict:
    """Rank customers by signed revenue and summarize their transaction behavior."""
    _validate_dataframe(df)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("Limit must be an integer between 1 and 100.")
    resolved = _resolve_mapping(df, mapping)
    customer_col = _require_column(df, resolved, "customer_id", "Customer intelligence")
    order_col = resolved.get("order_id")
    frame = pd.DataFrame({
        "customer_id": df[customer_col].astype("string"),
        "revenue": _revenue_series(df, resolved),
    })
    if isinstance(order_col, str) and order_col in df.columns:
        frame["order_id"] = df[order_col]
    else:
        frame["order_id"] = None
    frame = frame.dropna(subset=["customer_id"])
    grouped = frame.groupby("customer_id", dropna=False).agg(
        revenue=("revenue", "sum"),
        order_count=("order_id", "nunique"),
        transaction_rows=("revenue", "size"),
    )
    grouped["average_order_value"] = grouped.apply(
        lambda row: row["revenue"] / row["order_count"] if row["order_count"] else None,
        axis=1,
    )
    grouped = grouped.sort_values("revenue", ascending=False).head(limit)
    results = []
    for customer_id, row in grouped.iterrows():
        results.append({
            "customer_id": str(customer_id),
            "revenue": round(float(row["revenue"]), 2),
            "order_count": int(row["order_count"]),
            "transaction_rows": int(row["transaction_rows"]),
            "average_order_value": (
                round(float(row["average_order_value"]), 2)
                if pd.notna(row["average_order_value"]) else None
            ),
        })
    return {
        "unique_customers": int(frame["customer_id"].nunique()),
        "returned_customers": len(results),
        "results": results,
        "notes": [
            "Revenue is signed and includes negative return or cancellation rows.",
            "Order count uses distinct mapped order identifiers; it is zero when no order identifier is available.",
        ],
    }


def get_customer_rfm(
    df: pd.DataFrame, mapping: dict | None = None
) -> dict:
    """Calculate dataset-relative RFM scores; recency is measured from latest dataset date."""
    _validate_dataframe(df)
    resolved = _resolve_mapping(df, mapping)
    customer_col = _require_column(df, resolved, "customer_id", "RFM analysis")
    date_col = _require_column(df, resolved, "date", "RFM analysis")
    order_col = _require_column(df, resolved, "order_id", "RFM analysis")
    frame = pd.DataFrame({
        "customer_id": df[customer_col],
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "order_id": df[order_col],
        "revenue": _revenue_series(df, resolved),
    }).dropna(subset=["customer_id", "date"])
    if frame.empty:
        raise ValueError("RFM analysis requires valid customer dates.")
    reference_date = frame["date"].max()
    grouped = frame.groupby("customer_id").agg(
        last_purchase=("date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("revenue", "sum"),
    )
    grouped["recency_days"] = (reference_date.normalize() - grouped["last_purchase"].dt.normalize()).dt.days
    # Rank-based scoring handles tied values and small datasets without qcut failures.
    recency_pct = grouped["recency_days"].rank(method="average", ascending=False, pct=True)
    frequency_pct = grouped["frequency"].rank(method="average", pct=True)
    monetary_pct = grouped["monetary"].rank(method="average", pct=True)
    grouped["r_score"] = (recency_pct * 5).apply(lambda value: min(5, max(1, int(value + 0.999999))))
    grouped["f_score"] = (frequency_pct * 5).apply(lambda value: min(5, max(1, int(value + 0.999999))))
    grouped["m_score"] = (monetary_pct * 5).apply(lambda value: min(5, max(1, int(value + 0.999999))))
    grouped["rfm_score"] = grouped[["r_score", "f_score", "m_score"]].sum(axis=1)
    results = []
    for customer_id, row in grouped.sort_values(
        ["rfm_score", "monetary"], ascending=False
    ).iterrows():
        results.append({
            "customer_id": str(customer_id),
            "recency_days": int(row["recency_days"]),
            "frequency": int(row["frequency"]),
            "monetary": round(float(row["monetary"]), 2),
            "r_score": int(row["r_score"]),
            "f_score": int(row["f_score"]),
            "m_score": int(row["m_score"]),
            "rfm_score": int(row["rfm_score"]),
        })
    return {
        "reference_date": reference_date.date().isoformat(),
        "customer_count": len(results),
        "results": results,
        "notes": [
            "Recency is measured relative to the latest valid transaction date in this dataset, not today's date.",
            "RFM scores are rank-based from 1 to 5; higher scores indicate better relative standing.",
            "Monetary values use signed revenue, including returns and cancellations.",
        ],
    }


def get_product_intelligence(
    df: pd.DataFrame, limit: int = 20, mapping: dict | None = None
) -> dict:
    """Rank products by signed revenue and summarize quantity and optional category."""
    _validate_dataframe(df)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("Limit must be an integer between 1 and 100.")
    resolved = _resolve_mapping(df, mapping)
    product_col = _require_column(df, resolved, "product_id", "Product intelligence")
    name_col = resolved.get("product_name")
    category_col = resolved.get("category")
    quantity_col = resolved.get("quantity")
    frame = pd.DataFrame({
        "product_id": df[product_col].astype("string"),
        "revenue": _revenue_series(df, resolved),
        "quantity": pd.to_numeric(df[quantity_col], errors="coerce")
        if isinstance(quantity_col, str) and quantity_col in df.columns else 0,
        "product_name": df[name_col].astype("string")
        if isinstance(name_col, str) and name_col in df.columns else df[product_col].astype("string"),
    }).dropna(subset=["product_id"])
    if isinstance(category_col, str) and category_col in df.columns:
        frame["category"] = df[category_col].astype("string")
    grouped = frame.groupby("product_id", dropna=False).agg(
        revenue=("revenue", "sum"),
        quantity=("quantity", "sum"),
        product_name=("product_name", "first"),
    )
    if "category" in frame.columns:
        grouped["category"] = frame.groupby("product_id")["category"].first()
    grouped = grouped.sort_values("revenue", ascending=False).head(limit)
    results = []
    for product_id, row in grouped.iterrows():
        item = {
            "product_id": str(product_id),
            "product_name": str(row["product_name"]),
            "revenue": round(float(row["revenue"]), 2),
            "quantity": round(float(row["quantity"]), 2),
        }
        if "category" in grouped.columns:
            item["category"] = (
                str(row["category"]) if pd.notna(row["category"]) else None
            )
        results.append(item)
    return {
        "unique_products": int(frame["product_id"].nunique()),
        "returned_products": len(results),
        "results": results,
        "notes": [
            "Products are ranked by signed revenue; negative return values reduce net revenue.",
            "Category is included only when a category column is confidently mapped.",
        ],
    }
