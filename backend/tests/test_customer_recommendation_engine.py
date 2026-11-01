import pandas as pd
import pytest

from app.services.business_intelligence.customer_recommendation_engine import (
    generate_customer_recommendations,
)


def customer_data():
    rows = []
    # High-value customer who became inactive well before the dataset reference date.
    for i, date in enumerate(["2024-10-01", "2024-10-10", "2024-10-20", "2024-11-01"]):
        rows.append((f"OLD{i}", "C_OLD", date, 10, 100.0))
    # Recently frequent customer.
    for i, date in enumerate(["2025-05-01", "2025-05-10", "2025-05-20", "2025-05-29"]):
        rows.append((f"NEW{i}", "C_NEW", date, 2, 30.0))
    # Lower-spend customer.
    rows.append(("LOW1", "C_LOW", "2025-05-28", 1, 5.0))
    return pd.DataFrame(
        rows,
        columns=["InvoiceNo", "CustomerID", "InvoiceDate", "Quantity", "UnitPrice"],
    ).assign(InvoiceDate=lambda frame: pd.to_datetime(frame["InvoiceDate"]))


def test_recommends_reengagement_for_high_value_inactive_customers():
    result = generate_customer_recommendations(customer_data(), at_risk_days=90)
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "retain_high_value_inactive_customers"
    )
    assert item["evidence"]["at_risk_customer_count"] >= 1
    assert item["evidence"]["sample_customers"][0]["customer_id"] == "C_OLD"
    assert item["priority"] == "high"


def test_recommends_nurturing_recent_frequent_customers():
    result = generate_customer_recommendations(customer_data(), recent_days=30)
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "nurture_recent_frequent_customers"
    )
    assert item["evidence"]["loyal_customer_count"] >= 1
    assert any(
        customer["customer_id"] == "C_NEW"
        for customer in item["evidence"]["sample_customers"]
    )


def test_recency_uses_latest_dataset_date_not_current_date():
    result = generate_customer_recommendations(customer_data(), at_risk_days=90)
    assert result["reference_date"] == "2025-05-29"
    at_risk = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "retain_high_value_inactive_customers"
    )
    assert at_risk["evidence"]["sample_customers"][0]["recency_days"] > 90


def test_reports_missing_customer_fields():
    df = pd.DataFrame({"Revenue": [10.0, 20.0], "InvoiceDate": pd.to_datetime(["2025-01-01", "2025-02-01"])})
    result = generate_customer_recommendations(df)
    assert result["available"] is False
    assert result["recommendation_count"] == 0
    assert result["unavailable_recommendations"]


@pytest.mark.parametrize("kwargs", [
    {"at_risk_days": 0},
    {"at_risk_days": True},
    {"recent_days": 0},
])
def test_validates_day_thresholds(kwargs):
    with pytest.raises(ValueError):
        generate_customer_recommendations(customer_data(), **kwargs)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        generate_customer_recommendations(pd.DataFrame())
