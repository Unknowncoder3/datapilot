from __future__ import annotations

import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.insight_engine import generate_business_insights
from app.services.business_intelligence.anomaly_engine import detect_business_anomalies
from app.services.business_intelligence.recommendation_scoring_engine import (
    generate_prioritized_recommendations,
)


_SEVERITY_RANK = {"critical": 0, "high": 1, "warning": 1, "medium": 2, "low": 3, "positive": 4, "neutral": 5}


def build_ai_insights_feed(
    df: pd.DataFrame,
    mapping: dict | None = None,
    top_n: int = 10,
) -> dict:
    """Unify deterministic findings, statistical anomaly signals, and ranked actions."""
    _validate_dataframe(df)
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 30:
        raise ValueError("top_n must be an integer between 1 and 30.")

    findings_result = generate_business_insights(df, mapping=mapping, top_n=top_n)
    anomaly_result = detect_business_anomalies(
        df, mapping=mapping, sensitivity=3.5, limit=top_n, min_periods=14
    )
    recommendation_result = generate_prioritized_recommendations(
        df, mapping=mapping, top_n=top_n
    )

    feed = []
    for item in findings_result.get("insights", []):
        feed.append({
            "id": f"finding:{item.get('id', 'unknown')}",
            "kind": "finding",
            "category": item.get("category", "general"),
            "title": item.get("title", "Dataset finding"),
            "summary": item.get("summary", ""),
            "severity": item.get("severity", "neutral"),
            "metric": item.get("metric"),
            "value": item.get("value"),
            "evidence": item.get("evidence", {}),
            "confidence": item.get("confidence", "high"),
            "limitations": item.get("limitations", []),
            "method": findings_result.get("method", "deterministic_rules"),
        })

    for item in anomaly_result.get("anomalies", []):
        feed.append({
            "id": f"anomaly:{item.get('id', 'unknown')}",
            "kind": "anomaly",
            "category": item.get("category", "anomaly"),
            "title": item.get("title", "Unusual data pattern"),
            "summary": item.get("description", ""),
            "severity": item.get("severity", "medium"),
            "metric": "robust_z_score",
            "value": item.get("score"),
            "evidence": item.get("evidence", {}),
            "confidence": "medium",
            "limitations": item.get("limitations", []),
            "method": item.get("method", "median_absolute_deviation"),
        })

    for item in recommendation_result.get("recommendations", []):
        priority = str(item.get("priority", "low")).lower()
        severity = {"high": "warning", "medium": "medium", "low": "low"}.get(priority, "low")
        feed.append({
            "id": f"action:{item.get('id', 'unknown')}",
            "kind": "recommendation",
            "category": item.get("category", item.get("source", "action")),
            "title": item.get("title", "Business action"),
            "summary": item.get("description", item.get("recommendation", "")),
            "severity": severity,
            "metric": "recommendation_score",
            "value": item.get("score"),
            "evidence": item.get("evidence", {}),
            "confidence": item.get("confidence", "low"),
            "limitations": item.get("limitations", []),
            "method": "deterministic_weighted_score",
            "priority": priority,
            "score_band": item.get("score_band"),
            "source": item.get("source"),
            "suggested_action": item.get("action", item.get("suggested_action")),
        })

    feed.sort(key=lambda item: (
        _SEVERITY_RANK.get(str(item.get("severity", "neutral")).lower(), 6),
        -float(item.get("value") or 0) if item.get("kind") == "recommendation" else 0,
        item.get("category", ""),
        item.get("id", ""),
    ))
    selected = feed[:top_n]
    kind_counts = {
        kind: sum(1 for item in feed if item["kind"] == kind)
        for kind in ("finding", "anomaly", "recommendation")
    }
    severity_counts = {
        severity: sum(1 for item in feed if str(item["severity"]).lower() == severity)
        for severity in ("critical", "high", "warning", "medium", "low", "positive", "neutral")
    }

    return {
        "row_count": int(len(df)),
        "insight_count": len(feed),
        "returned_count": len(selected),
        "insights": selected,
        "counts_by_kind": kind_counts,
        "counts_by_severity": severity_counts,
        "unavailable": {
            "findings": findings_result.get("unavailable_insights", []),
            "anomalies": anomaly_result.get("unavailable_checks", []),
            "recommendations": recommendation_result.get("unavailable_sources", []),
        },
        "methods": {
            "findings": findings_result.get("method", "deterministic_rules"),
            "anomalies": anomaly_result.get("method", "robust_mad"),
            "recommendations": recommendation_result.get("method", "deterministic_rules"),
        },
        "notes": [
            "Insights are deterministic and grounded in dataset values; no external LLM is used.",
            "Statistical anomalies are review signals, not proof of fraud, error or causation.",
            "Recommendations are rule-based suggestions; scores are ranking aids, not probabilities.",
        ],
    }
