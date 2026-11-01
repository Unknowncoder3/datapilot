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
