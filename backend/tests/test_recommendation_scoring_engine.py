import pandas as pd
import pytest

from app.services.business_intelligence.recommendation_scoring_engine import (
    generate_prioritized_recommendations,
    _score_recommendation,
)


def retail_data():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A2", "A3", "A4", "A5", "A6"],
        "CustomerID": ["C1", "C2", "C1", "C2", "C3", "C3"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-01", "2025-01-02", "2025-02-01",
            "2025-02-02", "2025-02-10", "2025-02-20",
        ]),
        "StockCode": ["P1", "P2", "P1", "P2", "P3", "P3"],
        "Description": ["Product 1", "Product 2", "Product 1",
                        "Product 2", "Product 3", "Product 3"],
        "Country": ["UK", "UK", "UK", "DE", "DE", "DE"],
        "Quantity": [10, 5, 2, 10, 4, 3],
        "UnitPrice": [10.0, 20.0, 10.0, 20.0, 5.0, 5.0],
    })


def test_scores_recommendations_and_returns_sorted_results():
    result = generate_prioritized_recommendations(retail_data())
    assert result["recommendation_count"] > 0
    scores = [item["score"] for item in result["recommendations"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= score <= 100 for score in scores)
    assert all(item["score_band"] in {"critical", "high", "medium", "low"}
               for item in result["recommendations"])


def test_score_breakdown_is_transparent_and_bounded():
    recommendation = {
        "id": "example",
        "priority": "high",
        "confidence": "medium",
        "evidence": {"count": 5, "period": "2025-02", "missing": None},
    }
    result = _score_recommendation(recommendation)
    assert result["score"] == 80
    assert result["score_breakdown"]["priority_points"] == 40
    assert result["score_breakdown"]["confidence_points"] == 17
    assert result["score_breakdown"]["evidence_points"] == 23


def test_reports_unavailable_sources_when_fields_are_missing():
    result = generate_prioritized_recommendations(
        pd.DataFrame({"name": ["a", "b"], "value": [1, 2]})
    )
    assert result["available"] is False
    assert result["recommendation_count"] == 0
    assert len(result["unavailable_sources"]) == 4


def test_top_n_limits_returned_items_not_total_count():
    result = generate_prioritized_recommendations(retail_data(), top_n=1)
    assert result["returned_count"] == 1
    assert result["recommendation_count"] >= result["returned_count"]


@pytest.mark.parametrize("top_n", [0, 201, True, 1.5])
def test_validates_top_n(top_n):
    with pytest.raises(ValueError, match="top_n"):
        generate_prioritized_recommendations(retail_data(), top_n=top_n)


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        generate_prioritized_recommendations(pd.DataFrame())
