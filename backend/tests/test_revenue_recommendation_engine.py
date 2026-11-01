import pandas as pd
import pytest

from app.services.business_intelligence.revenue_recommendation_engine import (
    generate_revenue_recommendations,
)


def sample_retail():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A2", "A3", "A4", "A5", "A6"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-01-10", "2025-01-20",
            "2025-02-02", "2025-02-10", "2025-02-20",
        ]),
        "Quantity": [10, 8, -2, 3, 2, -1],
        "UnitPrice": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    })


def test_recommends_investigating_material_revenue_decline():
    result = generate_revenue_recommendations(sample_retail())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "investigate_revenue_decline"
    )
    assert item["evidence"]["previous_period"] == "2025-01"
    assert item["evidence"]["current_period"] == "2025-02"
    assert item["evidence"]["change_percent"] < -10
    assert item["method"] == "deterministic_rule"


def test_recommends_review_of_negative_revenue_rows():
    result = generate_revenue_recommendations(sample_retail())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "review_negative_revenue"
    )
    assert item["evidence"]["negative_rows"] == 2
    assert item["evidence"]["negative_rows_percent"] > 5
    assert "not assumed to be errors" in item["limitations"][0]


def test_recommends_validating_growth():
    df = sample_retail()
    df.loc[3:, "Quantity"] = [10, 12, 8]
    result = generate_revenue_recommendations(df)
    assert any(
        rec["id"] == "validate_revenue_growth"
        for rec in result["recommendations"]
    )


def test_reports_missing_date_without_failing():
    df = pd.DataFrame({"Revenue": [100.0, 50.0]})
    result = generate_revenue_recommendations(df)
    assert result["available"] is True
    assert result["recommendations"] == []
    assert result["unavailable_recommendations"][0]["category"] == "sales_performance"


def test_reports_missing_revenue_mapping():
    df = pd.DataFrame({"name": ["a", "b"], "score": [1, 2]})
    result = generate_revenue_recommendations(df)
    assert result["available"] is False
    assert result["recommendation_count"] == 0
    assert result["unavailable_recommendations"]


@pytest.mark.parametrize("kwargs", [
    {"negative_revenue_threshold": 0},
    {"negative_revenue_threshold": 101},
    {"change_threshold": 0},
    {"change_threshold": 101},
])
def test_validates_thresholds(kwargs):
    with pytest.raises(ValueError):
        generate_revenue_recommendations(sample_retail(), **kwargs)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        generate_revenue_recommendations(pd.DataFrame())
