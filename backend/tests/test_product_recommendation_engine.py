import pandas as pd
import pytest

from app.services.business_intelligence.product_recommendation_engine import (
    generate_product_recommendations,
)


def product_data():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-01-10", "2025-01-15",
            "2025-02-02", "2025-02-10", "2025-02-15", "2025-02-20",
        ]),
        "StockCode": ["DECLINE", "GROW", "NEG", "DECLINE", "GROW", "NEG", "STABLE"],
        "Description": ["Declining item", "Growing item", "Return item",
                        "Declining item", "Growing item", "Return item", "Stable item"],
        "Quantity": [10, 2, 1, 2, 10, -3, 5],
        "UnitPrice": [10.0, 10.0, 5.0, 10.0, 10.0, 5.0, 10.0],
    })


def test_recommends_investigating_declining_products():
    result = generate_product_recommendations(product_data())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "investigate_declining_products"
    )
    assert item["evidence"]["previous_period"] == "2025-01"
    assert item["evidence"]["current_period"] == "2025-02"
    assert item["evidence"]["products"][0]["product_id"] == "DECLINE"
    assert item["evidence"]["products"][0]["change_percent"] < -10


def test_recommends_validating_growing_products():
    result = generate_product_recommendations(product_data())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "validate_growing_products"
    )
    assert item["evidence"]["products"][0]["product_id"] == "GROW"
    assert item["evidence"]["products"][0]["change_percent"] > 10


def test_flags_products_with_negative_net_revenue():
    result = generate_product_recommendations(product_data())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "review_negative_net_revenue_products"
    )
    assert item["evidence"]["products"][0]["product_id"] == "NEG"
    assert item["evidence"]["products"][0]["net_revenue"] < 0


def test_reports_missing_product_or_revenue_mapping():
    result = generate_product_recommendations(pd.DataFrame({"name": ["a"], "score": [1]}))
    assert result["available"] is False
    assert result["recommendation_count"] == 0
    assert result["unavailable_recommendations"]


@pytest.mark.parametrize("kwargs", [
    {"change_threshold": 0},
    {"change_threshold": 101},
    {"top_n": 0},
    {"top_n": 51},
])
def test_validates_parameters(kwargs):
    with pytest.raises(ValueError):
        generate_product_recommendations(product_data(), **kwargs)


def test_reports_missing_date_but_can_review_negative_products():
    df = pd.DataFrame({
        "StockCode": ["P1", "P1", "P2"],
        "Quantity": [-2, 1, 3],
        "UnitPrice": [10.0, 5.0, 2.0],
    })
    result = generate_product_recommendations(df)
    assert result["available"] is True
    assert any(
        rec["id"] == "review_negative_net_revenue_products"
        for rec in result["recommendations"]
    )
    assert any(
        item["category"] == "product_performance"
        for item in result["unavailable_recommendations"]
    )


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        generate_product_recommendations(pd.DataFrame())
