import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.sales_engine import _revenue_series


def _resolved_mapping(df: pd.DataFrame, mapping: dict | None) -> dict:
    return mapping or map_business_columns(df)["mapping"]


def _recommendation(
    recommendation_id: str,
    category: str,
    title: str,
    rationale: str,
    action: str,
    priority: str,
    confidence: str,
    evidence: dict,
    limitations: list[str] | None = None,
) -> dict:
    return {
        "id": recommendation_id,
        "category": category,
        "title": title,
        "rationale": rationale,
        "recommended_action": action,
        "priority": priority,
        "confidence": confidence,
        "evidence": evidence,
        "limitations": limitations or [],
        "method": "deterministic_rule",
    }


def generate_revenue_recommendations(
    df: pd.DataFrame,
    mapping: dict | None = None,
    negative_revenue_threshold: float = 5.0,
    change_threshold: float = 10.0,
) -> dict:
    """Generate evidence-backed revenue and sales actions without forecasting or causal claims."""
    _validate_dataframe(df)
    for name, value in (
        ("negative_revenue_threshold", negative_revenue_threshold),
        ("change_threshold", change_threshold),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value <= 100:
            raise ValueError(f"{name} must be greater than 0 and at most 100.")

    resolved = _resolved_mapping(df, mapping)
    revenue_role = resolved.get("revenue")
    revenue_available = (
        isinstance(revenue_role, str) and revenue_role in df.columns
    ) or (
        isinstance(revenue_role, dict)
        and revenue_role.get("type") == "derived"
        and all(col in df.columns for col in revenue_role.get("depends_on", []))
    )
    if not revenue_available:
        return {
            "row_count": int(len(df)),
            "available": False,
            "recommendation_count": 0,
            "recommendations": [],
            "unavailable_recommendations": [{
                "category": "revenue",
                "reason": "A mapped revenue field or quantity and unit price are required.",
            }],
            "method": "deterministic_rules",
        }

    revenue = _revenue_series(df, resolved)
    valid = revenue.dropna()
    recommendations = []
    unavailable = []
    if valid.empty:
        return {
            "row_count": int(len(df)),
            "available": False,
            "recommendation_count": 0,
            "recommendations": [],
            "unavailable_recommendations": [{
                "category": "revenue",
                "reason": "No valid numeric revenue values were found.",
            }],
            "method": "deterministic_rules",
        }

    total = float(valid.sum())
    negative = valid[valid < 0]
    negative_rows_percent = len(negative) / len(valid) * 100
    negative_value_abs = abs(float(negative.sum()))
    negative_value_share = negative_value_abs / abs(total) * 100 if total != 0 else None
    if negative_rows_percent >= negative_revenue_threshold:
        recommendations.append(_recommendation(
            "review_negative_revenue", "revenue_quality",
            "Review returns, refunds and negative adjustments",
            "A material share of transaction rows contains negative revenue values.",
            "Segment negative transactions by invoice, product and period; verify whether they represent expected returns, refunds, cancellations or data-quality issues before changing sales targets.",
            "high" if negative_rows_percent >= 15 else "medium",
            "high",
            {
                "negative_rows": int(len(negative)),
                "valid_revenue_rows": int(len(valid)),
                "negative_rows_percent": round(negative_rows_percent, 2),
                "negative_value_total": round(float(negative.sum()), 2),
                "negative_value_share_of_absolute_net_revenue_percent": round(negative_value_share, 2) if negative_value_share is not None else None,
            },
            ["Negative values are not assumed to be errors; they may be legitimate returns, refunds or adjustments."],
        ))

    date_col = resolved.get("date")
    if isinstance(date_col, str) and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        time_frame = pd.DataFrame({"date": dates, "revenue": revenue}).dropna()
        if not time_frame.empty:
            time_frame["period"] = time_frame["date"].dt.to_period("M").astype(str)
            monthly = time_frame.groupby("period", sort=True)["revenue"].sum()
            if len(monthly) >= 2:
                previous_period, current_period = str(monthly.index[-2]), str(monthly.index[-1])
                previous, current = float(monthly.iloc[-2]), float(monthly.iloc[-1])
                if previous > 0:
                    change_percent = (current - previous) / previous * 100
                    evidence = {
                        "previous_period": previous_period,
                        "current_period": current_period,
                        "previous_revenue": round(previous, 2),
                        "current_revenue": round(current, 2),
                        "change": round(current - previous, 2),
                        "change_percent": round(change_percent, 2),
                    }
                    if change_percent <= -change_threshold:
                        recommendations.append(_recommendation(
                            "investigate_revenue_decline", "sales_performance",
                            "Investigate the recent revenue decline",
                            "Revenue in the latest observed month is materially below the preceding observed month.",
                            "Compare like-for-like trading days and investigate changes in order volume, product availability, customer activity, returns and market mix before selecting a corrective action.",
                            "high" if change_percent <= -25 else "medium",
                            "medium",
                            evidence,
                            ["The latest observed month may be incomplete; this comparison is not seasonally adjusted and does not establish causation."],
                        ))
                    elif change_percent >= change_threshold:
                        recommendations.append(_recommendation(
                            "validate_revenue_growth", "sales_opportunity",
                            "Validate and understand recent revenue growth",
                            "Revenue in the latest observed month is materially above the preceding observed month.",
                            "Identify the products, customers and markets associated with the increase, then check whether the drivers are repeatable before scaling inventory or spend.",
                            "medium",
                            "medium",
                            evidence,
                            ["The latest observed month may be incomplete; this comparison is not seasonally adjusted and does not establish causation."],
                        ))
            else:
                unavailable.append({
                    "category": "sales_performance",
                    "reason": "At least two observed months are required for a revenue trend recommendation.",
                })
        else:
            unavailable.append({
                "category": "sales_performance",
                "reason": "No valid transaction dates and revenue values were found.",
            })
    else:
        unavailable.append({
            "category": "sales_performance",
            "reason": "A mapped transaction date is required for time-based sales recommendations.",
        })

    recommendations.sort(
        key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item["priority"]], item["id"])
    )
    return {
        "row_count": int(len(df)),
        "available": True,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "unavailable_recommendations": unavailable,
        "method": "deterministic_rules",
        "notes": [
            "Recommendations are generated only when mapped data meets the relevant rule requirements.",
            "Negative revenue may represent legitimate returns, refunds or adjustments and should be investigated, not automatically removed.",
            "Period comparisons use the latest two observed calendar months, which may be incomplete.",
            "Recommendations are decision-support prompts, not causal conclusions or guaranteed outcomes.",
        ],
    }
