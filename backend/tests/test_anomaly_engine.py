import pandas as pd
import pytest

from app.services.business_intelligence.anomaly_engine import detect_business_anomalies


def daily_data():
    dates = pd.date_range("2025-01-01", periods=20, freq="D")
    revenue = [100.0] * 19 + [500.0]
    return pd.DataFrame({
        "OrderDate": dates,
        "OrderID": [f"O{i}" for i in range(20)],
        "Revenue": revenue,
        "Quantity": [1] * 19 + [100],
        "UnitPrice": [100.0] * 20,
    })


def test_detects_daily_revenue_spike():
    result = detect_business_anomalies(daily_data())
    revenue_anomalies = [
        item for item in result["anomalies"]
        if item["category"] == "revenue"
    ]
    assert len(revenue_anomalies) == 1
    assert revenue_anomalies[0]["evidence"]["period"] == "2025-01-20"
    assert revenue_anomalies[0]["evidence"]["direction"] == "above"


def test_detects_unusual_transaction_quantity():
    result = detect_business_anomalies(daily_data())
    quantity_anomalies = [
        item for item in result["anomalies"]
        if item["category"] == "transaction"
        and item["evidence"]["column"] == "Quantity"
    ]
    assert quantity_anomalies
    assert quantity_anomalies[0]["evidence"]["value"] == 100.0


def test_requires_minimum_daily_history():
    result = detect_business_anomalies(daily_data().head(8), min_periods=14)
    assert not any(item["category"] == "revenue" for item in result["anomalies"])
    assert any("At least 14 observed days" in item["reason"] for item in result["unavailable_checks"])


def test_reports_missing_revenue_and_date_fields():
    result = detect_business_anomalies(pd.DataFrame({"name": ["a", "b"], "score": [1, 2]}))
    assert result["anomaly_count"] == 0
    assert result["unavailable_checks"]


def test_preserves_negative_revenue_in_daily_totals():
    df = daily_data()
    df.loc[0, "Revenue"] = -250.0
    result = detect_business_anomalies(df)
    assert result["row_count"] == 20
    assert any(item["category"] == "revenue" for item in result["anomalies"])


@pytest.mark.parametrize("kwargs, message", [
    ({"sensitivity": 0}, "sensitivity"),
    ({"limit": 0}, "limit"),
    ({"min_periods": 3}, "min_periods"),
])
def test_validates_parameters(kwargs, message):
    with pytest.raises(ValueError, match=message):
        detect_business_anomalies(daily_data(), **kwargs)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        detect_business_anomalies(pd.DataFrame())
