from __future__ import annotations

import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.revenue_recommendation_engine import generate_revenue_recommendations
from app.services.business_intelligence.customer_recommendation_engine import generate_customer_recommendations
from app.services.business_intelligence.product_recommendation_engine import generate_product_recommendations
from app.services.business_intelligence.market_recommendation_engine import generate_market_recommendations


_PRIORITY_POINTS = {"high": 40, "medium": 25, "low": 10}
_CONFIDENCE_POINTS = {"high": 25, "medium": 17, "low": 9}


def _evidence_completeness(evidence: dict) -> tuple[int, int]:
    """Return a bounded evidence score and count of populated evidence fields."""
    if not isinstance(evidence, dict) or not evidence:
        return 0, 0
    populated = 0
    for value in evidence.values():
        if value is None:
            continue
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            continue
        populated += 1
    score = round((populated / len(evidence)) * 35)
    return score, populated


def _score_recommendation(recommendation: dict) -> dict:
    priority = str(recommendation.get("priority", "low")).lower()
    confidence = str(recommendation.get("confidence", "low")).lower()
    priority_points = _PRIORITY_POINTS.get(priority, 0)
    confidence_points = _CONFIDENCE_POINTS.get(confidence, 0)
    evidence_points, populated_fields = _evidence_completeness(
        recommendation.get("evidence", {})
    )
    total = min(100, priority_points + confidence_points + evidence_points)
    if total >= 75:
        band = "critical"
    elif total >= 55:
        band = "high"
    elif total >= 35:
        band = "medium"
    else:
        band = "low"

    scored = dict(recommendation)
    scored["score"] = total
    scored["score_band"] = band
    scored["score_breakdown"] = {
        "priority_points": priority_points,
        "confidence_points": confidence_points,
        "evidence_points": evidence_points,
        "populated_evidence_fields": populated_fields,
        "total_evidence_fields": len(recommendation.get("evidence", {}))
        if isinstance(recommendation.get("evidence", {}), dict) else 0,
    }
    return scored


def generate_prioritized_recommendations(
    df: pd.DataFrame,
    mapping: dict | None = None,
    top_n: int = 50,
) -> dict:
    """Combine revenue, customer, product and market rules into one scored action list."""
    _validate_dataframe(df)
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 200:
        raise ValueError("top_n must be an integer between 1 and 200.")

    engines = [
        ("revenue", generate_revenue_recommendations),
        ("customers", generate_customer_recommendations),
        ("products", generate_product_recommendations),
        ("markets", generate_market_recommendations),
    ]
    source_results = {}
    all_recommendations = []
    unavailable = []

    for source, engine in engines:
        result = engine(df, mapping=mapping)
        source_results[source] = {
            "available": bool(result.get("available", True)),
            "recommendation_count": int(result.get("recommendation_count", 0)),
        }
        for recommendation in result.get("recommendations", []):
            enriched = dict(recommendation)
            enriched["source"] = source
            all_recommendations.append(_score_recommendation(enriched))
        for item in result.get("unavailable_recommendations", []):
            unavailable.append({"source": source, **item})

    all_recommendations.sort(
        key=lambda item: (
            -item["score"],
            {"high": 0, "medium": 1, "low": 2}.get(item.get("priority"), 3),
            item.get("id", ""),
        )
    )
    total = len(all_recommendations)
    selected = all_recommendations[:top_n]
    return {
        "row_count": int(len(df)),
        "available": total > 0,
        "source_summary": source_results,
        "recommendation_count": total,
        "returned_count": len(selected),
        "recommendations": selected,
        "unavailable_sources": unavailable,
        "scoring": {
            "method": "deterministic_weighted_score",
            "maximum_score": 100,
            "weights": {
                "priority": 40,
                "confidence": 25,
                "evidence_completeness": 35,
            },
            "bands": {
                "critical": "75-100",
                "high": "55-74",
                "medium": "35-54",
                "low": "0-34",
            },
            "note": "Scores rank rule-based recommendations for review; they are not probabilities, predicted outcomes or causal impact estimates.",
        },
        "method": "deterministic_rules_with_weighted_prioritization",
    }
