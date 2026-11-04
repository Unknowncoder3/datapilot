from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.business_intelligence.column_mapper import (
    map_business_columns,
    validate_business_mapping,
)
from app.services.business_intelligence.kpi_engine import calculate_business_kpis
from app.services.business_intelligence.sales_engine import (
    get_sales_trends,
    get_sales_by_country,
    get_top_products,
)
from app.services.business_intelligence.customer_product_engine import (
    get_customer_intelligence,
    get_customer_rfm,
    get_product_intelligence,
)
from app.services.business_intelligence.query_engine import run_safe_analytics_query
from app.api.analytics_routes import _load_dataset


router = APIRouter(tags=["business-intelligence"])


@router.get("/{dataset_id}/bi/mapping")
def get_business_mapping(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **map_business_columns(df),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{dataset_id}/bi/mapping")
def validate_mapping_override(
    dataset_id: int,
    mapping: dict = Body(..., description="Business role to dataset column mapping"),
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **validate_business_mapping(df, mapping),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/kpis")
def get_business_kpis(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **calculate_business_kpis(df),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/sales/trends")
def sales_trends(
    dataset_id: int,
    frequency: str = "month",
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {"dataset_id": dataset_id, **get_sales_trends(df, frequency=frequency)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/sales/countries")
def sales_by_country(
    dataset_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {"dataset_id": dataset_id, **get_sales_by_country(df, limit=limit)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/sales/products")
def top_selling_products(
    dataset_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {"dataset_id": dataset_id, **get_top_products(df, limit=limit)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/customers")
def customer_intelligence(
    dataset_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **get_customer_intelligence(df, limit=limit),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/customers/rfm")
def customer_rfm(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {"dataset_id": dataset_id, **get_customer_rfm(df)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/bi/products")
def product_intelligence(
    dataset_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **get_product_intelligence(df, limit=limit),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@router.post("/{dataset_id}/bi/query")
def run_business_query(
    dataset_id: int,
    query: dict = Body(
        ...,
        description="Validated query with columns, filters, group_by, aggregations, sorting, and pagination.",
        example={
            "filters": [{"column": "Country", "operator": "eq", "value": "United Kingdom"}],
            "group_by": ["Country"],
            "aggregations": [{"column": "Quantity", "aggregation": "sum", "alias": "units_sold"}],
            "sort_by": "units_sold",
            "sort_order": "desc",
            "limit": 20,
            "offset": 0,
        },
    ),
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        if not isinstance(query, dict):
            raise ValueError("Query body must be a JSON object.")
        allowed = {
            "columns", "filters", "group_by", "aggregations",
            "sort_by", "sort_order", "limit", "offset",
        }
        unknown = set(query) - allowed
        if unknown:
            raise ValueError(f"Unsupported query properties: {sorted(unknown)}.")
        return {
            "dataset_id": dataset_id,
            **run_safe_analytics_query(df, **query),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

from app.services.business_intelligence.insight_engine import generate_business_insights


@router.get("/{dataset_id}/bi/insights")
def business_insights(
    dataset_id: int,
    top_n: int = 5,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **generate_business_insights(df, top_n=top_n),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.anomaly_engine import detect_business_anomalies


@router.get("/{dataset_id}/bi/anomalies")
def business_anomalies(
    dataset_id: int,
    sensitivity: float = 3.5,
    limit: int = 100,
    min_periods: int = 14,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **detect_business_anomalies(
                df,
                sensitivity=sensitivity,
                limit=limit,
                min_periods=min_periods,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.driver_engine import analyze_business_drivers


@router.get("/{dataset_id}/bi/drivers")
def business_drivers(
    dataset_id: int,
    top_n: int = 10,
    frequency: str = "month",
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **analyze_business_drivers(
                df,
                top_n=top_n,
                frequency=frequency,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.revenue_recommendation_engine import (
    generate_revenue_recommendations,
)


@router.get("/{dataset_id}/bi/recommendations/revenue")
def revenue_recommendations(
    dataset_id: int,
    negative_revenue_threshold: float = 5.0,
    change_threshold: float = 10.0,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **generate_revenue_recommendations(
                df,
                negative_revenue_threshold=negative_revenue_threshold,
                change_threshold=change_threshold,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.customer_recommendation_engine import (
    generate_customer_recommendations,
)


@router.get("/{dataset_id}/bi/recommendations/customers")
def customer_recommendations(
    dataset_id: int,
    at_risk_days: int = 90,
    recent_days: int = 30,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **generate_customer_recommendations(
                df,
                at_risk_days=at_risk_days,
                recent_days=recent_days,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.product_recommendation_engine import (
    generate_product_recommendations,
)


@router.get("/{dataset_id}/bi/recommendations/products")
def product_recommendations(
    dataset_id: int,
    change_threshold: float = 10.0,
    top_n: int = 10,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **generate_product_recommendations(
                df,
                change_threshold=change_threshold,
                top_n=top_n,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.market_recommendation_engine import (
    generate_market_recommendations,
)


@router.get("/{dataset_id}/bi/recommendations/markets")
def market_recommendations(
    dataset_id: int,
    growth_threshold: float = 10.0,
    minimum_previous_revenue: float = 100.0,
    top_n: int = 10,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **generate_market_recommendations(
                df,
                growth_threshold=growth_threshold,
                minimum_previous_revenue=minimum_previous_revenue,
                top_n=top_n,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.recommendation_scoring_engine import (
    generate_prioritized_recommendations,
)


@router.get("/{dataset_id}/bi/recommendations")
def prioritized_recommendations(
    dataset_id: int,
    top_n: int = 50,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **generate_prioritized_recommendations(df, top_n=top_n),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


from app.services.business_intelligence.advanced_dashboard_engine import build_advanced_dashboard


@router.get("/{dataset_id}/bi/advanced-dashboard")
def advanced_dashboard(
    dataset_id: int,
    country: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    product: str | None = None,
    quarter: str | None = None,
    weekday: str | None = None,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **build_advanced_dashboard(df, country=country, start_date=start_date, end_date=end_date, product=product, quarter=quarter, weekday=weekday),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{dataset_id}/bi/ask")
def ask_dataset_question(dataset_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Answer a small, explicit set of natural-language business questions using dataset fields."""
    import re
    import pandas as pd

    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(status_code=422, detail="Enter a question about your dataset.")
    if len(question) > 500:
        raise HTTPException(status_code=422, detail="Question must be 500 characters or fewer.")

    df = _load_dataset(dataset_id, db)
    mapping = map_business_columns(df).get("mapping", {})
    # Column mapper exposes the role mapping directly in its result; tolerate both shapes.
    if not mapping:
        mapping = map_business_columns(df)
    # Resolve short follow-ups against the most recent user question in this session.
    # This keeps the existing deterministic dataset analytics intent parser grounded.
    conversation = payload.get("conversation", []) if isinstance(payload, dict) else []
    previous_question = next((item.get("content", "") for item in reversed(conversation)
                              if isinstance(item, dict) and item.get("role") == "user"
                              and isinstance(item.get("content"), str)), "")
    follow_up = question.strip().lower()
    follow_up_markers = ("why", "explain", "what about", "and ", "compare", "more", "chart", "graph", "show it", "that")
    intent_question = question
    if previous_question and (len(follow_up.split()) <= 5 or any(marker in follow_up for marker in follow_up_markers)):
        intent_question = f"{previous_question} {question}"
    q = re.sub(r"[^a-z0-9 ]", " ", intent_question.lower())
    q = re.sub(r"\\s+", " ", q).strip()

    revenue_role = mapping.get("revenue")
    if isinstance(revenue_role, dict) and revenue_role.get("type") == "derived":
        qty_col, price_col = revenue_role.get("depends_on", [None, None])
        if qty_col not in df.columns or price_col not in df.columns:
            revenue_role = None
        else:
            revenue = pd.to_numeric(df[qty_col], errors="coerce") * pd.to_numeric(df[price_col], errors="coerce")
    elif isinstance(revenue_role, str) and revenue_role in df.columns:
        revenue = pd.to_numeric(df[revenue_role], errors="coerce")
    else:
        revenue_role = None
        revenue = None

    country_col = mapping.get("country")
    product_col = mapping.get("product_name") or mapping.get("product_id")
    customer_col = mapping.get("customer_id")
    order_col = mapping.get("order_id")

    def grouped_top(column, label):
        if not isinstance(column, str) or column not in df.columns:
            raise HTTPException(status_code=422, detail=f"Could not identify a {label} column in this dataset.")
        if revenue is None:
            counts = df[column].dropna().astype(str).value_counts().head(10)
            rows = [{"label": str(k), "value": int(v)} for k, v in counts.items()]
            metric = "row count"
        else:
            grouped = pd.DataFrame({"group": df[column].astype("string"), "value": revenue}).dropna(subset=["group"]).groupby("group", dropna=False)["value"].sum().sort_values(ascending=False).head(10)
            rows = [{"label": str(k), "value": float(v)} for k, v in grouped.items()]
            metric = "revenue"
        return {"question": question.strip(), "answer": f"Here are the top {len(rows)} {label} by {metric}.", "chart": {"type": "bar", "title": f"Top {label.title()} by {metric.title()}", "metric": metric, "data": rows}, "source": "dataset", "rows_analyzed": int(len(df))}

    if any(term in q for term in ["country", "market", "region"]) and any(term in q for term in ["top", "highest", "most", "best", "revenue", "sales", "rank", "which"]):
        return grouped_top(country_col or mapping.get("region"), "countries/markets")
    if any(term in q for term in ["product", "item", "sku"]) and any(term in q for term in ["top", "highest", "most", "best", "revenue", "sales", "rank", "which"]):
        return grouped_top(product_col, "products")
    if any(term in q for term in ["total revenue", "total sales", "revenue overall", "sales overall", "how much revenue", "how much sales"]):
        if revenue is None:
            raise HTTPException(status_code=422, detail="Revenue could not be inferred. Please use the Business Mapping screen to confirm your sales columns.")
        total = float(revenue.sum(skipna=True))
        return {"question": question.strip(), "answer": f"Total revenue across {len(df):,} rows is {total:,.2f}.", "metric": {"label": "Total revenue", "value": total, "format": "currency"}, "source": "dataset", "rows_analyzed": int(len(df))}
    if any(term in q for term in ["customer", "customers", "client"]) and any(term in q for term in ["count", "number", "how many", "total", "unique"]):
        if not isinstance(customer_col, str) or customer_col not in df.columns:
            raise HTTPException(status_code=422, detail="Could not identify a customer ID column in this dataset.")
        count = int(df[customer_col].nunique(dropna=True))
        return {"question": question.strip(), "answer": f"The dataset contains {count:,} unique customers.", "metric": {"label": "Unique customers", "value": count, "format": "number"}, "source": "dataset", "rows_analyzed": int(len(df))}
    if any(term in q for term in ["order", "invoice", "transaction"]) and any(term in q for term in ["count", "number", "how many", "total", "unique"]):
        if isinstance(order_col, str) and order_col in df.columns:
            count = int(df[order_col].nunique(dropna=True))
        else:
            count = int(len(df))
        return {"question": question.strip(), "answer": f"The dataset contains {count:,} orders/transactions.", "metric": {"label": "Orders / transactions", "value": count, "format": "number"}, "source": "dataset", "rows_analyzed": int(len(df))}
    raise HTTPException(status_code=422, detail="I can answer questions about total revenue/sales, unique customers or orders, top countries/markets, and top products. Try one of the suggested questions.")
