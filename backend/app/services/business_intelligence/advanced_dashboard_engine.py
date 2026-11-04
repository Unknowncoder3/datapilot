import pandas as pd
from app.services.business_intelligence.column_mapper import map_business_columns


def build_advanced_dashboard(df: pd.DataFrame, country: str | None = None,
                             start_date: str | None = None, end_date: str | None = None,
                             product: str | None = None, quarter: str | None = None,
                             weekday: str | None = None) -> dict:
    mapping = map_business_columns(df)["mapping"]
    revenue_role = mapping.get("revenue")
    if isinstance(revenue_role, dict) and revenue_role.get("type") == "derived":
        q_col, p_col = revenue_role.get("depends_on", [None, None])
        revenue = pd.to_numeric(df[q_col], errors="coerce") * pd.to_numeric(df[p_col], errors="coerce")
    elif isinstance(revenue_role, str) and revenue_role in df.columns:
        revenue = pd.to_numeric(df[revenue_role], errors="coerce")
    else:
        raise ValueError("Dashboard requires a revenue field or quantity and unit price fields.")

    date_col = mapping.get("date")
    date_values = pd.to_datetime(df[date_col], errors="coerce") if isinstance(date_col, str) and date_col in df.columns else None
    country_col = mapping.get("country")
    country_values = df[country_col].fillna("Unknown").astype(str) if isinstance(country_col, str) and country_col in df.columns else pd.Series(["All"] * len(df), index=df.index)
    countries = sorted(country_values.dropna().unique().tolist())

    frame = pd.DataFrame({"revenue": revenue, "country": country_values}, index=df.index)
    if date_values is not None:
        frame["date"] = date_values
    quantity_col = mapping.get("quantity")
    frame["quantity"] = pd.to_numeric(df[quantity_col], errors="coerce") if isinstance(quantity_col, str) and quantity_col in df.columns else 0
    customer_col, order_col, product_col = mapping.get("customer_id"), mapping.get("order_id"), mapping.get("product_id")
    frame["customer"] = df[customer_col] if isinstance(customer_col, str) and customer_col in df.columns else None
    frame["order"] = df[order_col] if isinstance(order_col, str) and order_col in df.columns else None
    frame["product"] = df[product_col].astype(str) if isinstance(product_col, str) and product_col in df.columns else "Unknown"
    product_name_col = mapping.get("product_name")
    frame["product_name"] = df[product_name_col].astype(str) if isinstance(product_name_col, str) and product_name_col in df.columns else frame["product"]
    if "date" in frame.columns:
        frame["quarter"] = frame["date"].dt.to_period("Q").astype(str)
        frame["weekday"] = frame["date"].dt.day_name()

    if country and country != "All":
        frame = frame[frame["country"] == country]
    if "date" in frame.columns and start_date:
        frame = frame[frame["date"] >= pd.to_datetime(start_date, errors="coerce")]
    if "date" in frame.columns and end_date:
        end = pd.to_datetime(end_date, errors="coerce")
        if pd.notna(end):
            frame = frame[frame["date"] < end + pd.Timedelta(days=1)]
    if product:
        frame = frame[frame["product_name"] == product]
    if quarter and "quarter" in frame.columns:
        frame = frame[frame["quarter"] == quarter]
    if weekday and "weekday" in frame.columns:
        frame = frame[frame["weekday"] == weekday]

    revenue_sum = float(frame["revenue"].sum(skipna=True))
    order_count = int(frame["order"].nunique(dropna=True)) if frame["order"].notna().any() else None
    customer_count = int(frame["customer"].nunique(dropna=True)) if frame["customer"].notna().any() else None
    units = float(frame["quantity"].sum(skipna=True))
    kpis = [
        {"label": "Total Revenue", "value": round(revenue_sum, 2), "format": "currency"},
        {"label": "Total Customers", "value": customer_count, "format": "number"},
        {"label": "Total Orders", "value": order_count, "format": "number"},
        {"label": "Avg Order Value", "value": round(revenue_sum / order_count, 2) if order_count else None, "format": "currency"},
        {"label": "Total Quantity", "value": round(units, 2), "format": "number"},
    ]

    def records(grouped, key, value="revenue", limit=10):
        if grouped.empty:
            return []
        return [{key: str(idx), value: round(float(row), 2)} for idx, row in grouped.head(limit).items()]

    countries_by_revenue = frame.groupby("country")["revenue"].sum().sort_values(ascending=False)
    products_by_revenue = frame.groupby("product_name")["revenue"].sum().sort_values(ascending=False)
    monthly = []
    quarterly = []
    weekdays = []
    if "date" in frame.columns:
        dated = frame.dropna(subset=["date"]).copy()
        if not dated.empty:
            dated["month"] = dated["date"].dt.to_period("M").astype(str)
            dated["quarter"] = dated["date"].dt.to_period("Q").astype(str)
            dated["weekday"] = dated["date"].dt.day_name()
            monthly = records(dated.groupby("month")["revenue"].sum().sort_index(), "period", limit=24)
            quarterly = records(dated.groupby("quarter")["revenue"].sum().sort_index(), "quarter", limit=16)
            weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            weekdays = records(dated.groupby("weekday")["revenue"].sum().reindex(weekday_order).dropna().sort_values(ascending=False), "day", limit=7)

    segments = []
    if frame["customer"].notna().any():
        customers = frame.dropna(subset=["customer"]).groupby("customer").agg(
            revenue=("revenue","sum"), orders=("order","nunique"),
            last_date=("date","max") if "date" in frame.columns else ("revenue","count")
        )
        if "date" in frame.columns:
            ref_date = frame["date"].max()
            customers["recency"] = (ref_date.normalize() - pd.to_datetime(customers["last_date"]).dt.normalize()).dt.days
            conditions = [
                (customers["recency"] <= 30) & (customers["orders"] >= 5) & (customers["revenue"] >= customers["revenue"].quantile(.75)),
                customers["orders"] >= 5,
                customers["recency"] > 90,
            ]
            labels = ["Champions", "Loyal Customers", "At Risk"]
            customers["segment"] = "Others"
            for condition, label in zip(conditions, labels):
                customers.loc[condition & customers["segment"].eq("Others"), "segment"] = label
            segments = records(customers.groupby("segment")["revenue"].sum().sort_values(ascending=False), "segment", limit=8)

    return {
        "dataset_rows": int(len(frame)), "countries": countries, "active_country": country or "All",
        "kpis": kpis, "country_revenue": records(countries_by_revenue, "country"),
        "monthly_revenue": monthly, "product_revenue": records(products_by_revenue, "product", limit=10),
        "customer_segments": segments, "quarterly_revenue": quarterly, "weekday_revenue": weekdays,
        "date_min": frame["date"].min().date().isoformat() if "date" in frame.columns and frame["date"].notna().any() else None,
        "date_max": frame["date"].max().date().isoformat() if "date" in frame.columns and frame["date"].notna().any() else None,
    }
