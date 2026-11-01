import pandas as pd
import pytest

from app.services.business_intelligence.driver_engine import analyze_business_drivers


def driver_data():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A2", "A3", "A4", "A5", "A6"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-01-03", "2025-01-04",
            "2025-02-02", "2025-02-03", "2025-02-04",
        ]),
        "CustomerID": ["C1", "C2", "C1", "C1", "C2", "C3"],
        "StockCode": ["P1", "P1", "P2", "P1", "P2", "P3"],
        "Quantity": [2, 3, 1, 4, 3, 2],
        "UnitPrice": [10.0, 10.0, 20.0, 12.0, 10.0, 20.0],
        "Country": ["UK", "FR", "UK", "UK", "FR", "DE"],
    })


def test_decomposes_revenue_change_into_volume_and_price_effects():
    result = analyze_business_drivers(driver_data())
    comparison = result["comparison"]
    assert comparison["previous_period"] == "2025-01"
    assert comparison["current_period"] == "2025-02"
    price_volume = result["drivers"]["price_volume"]
    assert price_volume["available"] is True
    assert price_volume["volume_effect"] + price_volume["price_effect"] == pytest.approx(
        comparison["revenue_change"], abs=0.01
    )
    assert price_volume["reconciliation_difference"] == pytest.approx(0, abs=0.00001)


def test_returns_customer_product_and_geography_contributions():
    result = analyze_business_drivers(driver_data())
    assert result["drivers"]["customer"]["available"] is True
    assert result["drivers"]["product"]["available"] is True
    assert result["drivers"]["geography"]["available"] is True
    assert result["drivers"]["customer"]["total_groups"] == 3


def test_returns_positive_and_negative_contributors_separately():
    df = driver_data()
    df.loc[5, "Quantity"] = -10
    result = analyze_business_drivers(df)
    for dimension in ("customer", "product", "geography"):
        analysis = result["drivers"][dimension]
        assert analysis["positive_contributors"]
        assert analysis["negative_contributors"]
        assert all(item["contributor_type"] == "positive" for item in analysis["positive_contributors"])
        assert all(item["contributor_type"] == "negative" for item in analysis["negative_contributors"])
        assert analysis["results"] == (
            analysis["positive_contributors"] + analysis["negative_contributors"]
        )


def test_reports_missing_dimension_without_failing():
    df = driver_data().drop(columns=["CustomerID"])
    result = analyze_business_drivers(df)
    assert result["drivers"]["customer"]["available"] is False
    assert "customer" in result["unavailable_analyses"]
    assert result["drivers"]["product"]["available"] is True


def test_requires_two_observed_periods():
    df = driver_data().iloc[:3].copy()
    result = analyze_business_drivers(df)
    assert result["available"] is False
    assert "At least two observed periods" in result["reason"]


def test_requires_mapped_date_for_driver_analysis():
    df = pd.DataFrame({"Revenue": [10, 20], "Quantity": [1, 2], "UnitPrice": [10, 10]})
    result = analyze_business_drivers(df)
    assert result["available"] is False
    assert "mapped transaction date" in result["reason"]


@pytest.mark.parametrize("kwargs, message", [
    ({"top_n": 0}, "top_n"),
    ({"top_n": 51}, "top_n"),
    ({"frequency": "year"}, "Frequency"),
])
def test_validates_parameters(kwargs, message):
    with pytest.raises(ValueError, match=message):
        analyze_business_drivers(driver_data(), **kwargs)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        analyze_business_drivers(pd.DataFrame())
