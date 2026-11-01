import pandas as pd
import pytest

from app.services.business_intelligence.insight_engine import generate_business_insights


def retail_data():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A1", "A2", "A3", "A4", "A5"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-01-10", "2025-02-02",
            "2025-02-10", "2025-03-01", "2025-03-05",
        ]),
        "CustomerID": [101, 101, 102, 103, 101, 104],
        "StockCode": ["P1", "P2", "P1", "P2", "P1", "P3"],
        "Description": ["Tea", "Coffee", "Tea", "Coffee", "Tea", "Cake"],
        "Quantity": [2, 1, 3, 2, 4, -1],
        "UnitPrice": [5.0, 8.0, 5.0, 8.0, 5.0, 2.0],
        "Country": ["UK", "UK", "FR", "UK", "FR", "UK"],
    })


def test_generates_revenue_product_and_market_insights():
    result = generate_business_insights(retail_data())
    ids = {item["id"] for item in result["insights"]}
    assert "revenue_summary" in ids
    assert "top_product" in ids
    assert "top_market" in ids
    revenue = next(item for item in result["insights"] if item["id"] == "revenue_summary")
    assert revenue["value"] == 67.0
    assert revenue["evidence"]["negative_rows"] == 1


def test_generates_monthly_comparison_when_two_months_exist():
    result = generate_business_insights(retail_data())
    item = next(item for item in result["insights"] if item["id"] == "monthly_revenue_change")
    assert item["evidence"]["previous_period"] == "2025-02"
    assert item["evidence"]["latest_period"] == "2025-03"


def test_reports_unavailable_insights_when_required_fields_are_missing():
    df = pd.DataFrame({"name": ["a", "b"], "score": [1, 2]})
    result = generate_business_insights(df)
    assert result["insight_count"] == 0
    assert result["unavailable_insights"]
    assert result["method"] == "deterministic_rules"


def test_handles_explicit_revenue_without_product_or_date_fields():
    df = pd.DataFrame({"Revenue": [10.0, -2.0], "Segment": ["A", "B"]})
    result = generate_business_insights(df)
    revenue = next(item for item in result["insights"] if item["id"] == "revenue_summary")
    assert revenue["value"] == 8.0
    assert any(item["category"] == "sales" for item in result["unavailable_insights"])


def test_validates_top_n():
    with pytest.raises(ValueError, match="top_n"):
        generate_business_insights(retail_data(), top_n=0)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        generate_business_insights(pd.DataFrame())
