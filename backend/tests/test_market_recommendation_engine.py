import pandas as pd
import pytest

from app.services.business_intelligence.market_recommendation_engine import (
    generate_market_recommendations,
)


def market_data():
    return pd.DataFrame({
        "Country": ["A", "A", "B", "B", "C", "C"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-02-02", "2025-01-03",
            "2025-02-03", "2025-01-04", "2025-02-04",
        ]),
        "Quantity": [20, 40, 50, 10, 30, 30],
        "UnitPrice": [10.0] * 6,
    })


def test_recommends_validating_growing_countries():
    result = generate_market_recommendations(market_data())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "validate_growing_markets"
    )
    assert item["evidence"]["countries"][0]["country"] == "A"
    assert item["evidence"]["countries"][0]["change_percent"] == 100.0


def test_recommends_investigating_declining_countries():
    result = generate_market_recommendations(market_data())
    item = next(
        rec for rec in result["recommendations"]
        if rec["id"] == "investigate_declining_markets"
    )
    assert item["evidence"]["countries"][0]["country"] == "B"
    assert item["evidence"]["countries"][0]["change_percent"] == -80.0


def test_excludes_tiny_previous_period_baselines():
    result = generate_market_recommendations(
        market_data(), minimum_previous_revenue=1000
    )
    assert not any(
        rec["id"] in {"validate_growing_markets", "investigate_declining_markets"}
        for rec in result["recommendations"]
    )


def test_reports_missing_country_mapping():
    result = generate_market_recommendations(
        pd.DataFrame({"Revenue": [10.0, 20.0]})
    )
    assert result["available"] is False
    assert result["recommendation_count"] == 0


@pytest.mark.parametrize("kwargs", [
    {"growth_threshold": 0},
    {"growth_threshold": 101},
    {"minimum_previous_revenue": -1},
    {"top_n": 0},
    {"top_n": 51},
])
def test_validates_parameters(kwargs):
    with pytest.raises(ValueError):
        generate_market_recommendations(market_data(), **kwargs)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        generate_market_recommendations(pd.DataFrame())
