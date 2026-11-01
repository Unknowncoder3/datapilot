import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.customer_product_engine import get_customer_rfm


def generate_customer_recommendations(
    df: pd.DataFrame,
    mapping: dict | None = None,
    at_risk_days: int = 90,
    recent_days: int = 30,
) -> dict:
    """Identify dataset-relative high-value inactive and recently loyal customer segments."""
    _validate_dataframe(df)
    for name, value in (("at_risk_days", at_risk_days), ("recent_days", recent_days)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name} must be a positive integer.")

    resolved = mapping or map_business_columns(df)["mapping"]
    required = ("customer_id", "date", "order_id", "revenue")
    missing = [role for role in required if not resolved.get(role)]
    if missing:
        return {
            "row_count": int(len(df)),
            "available": False,
            "recommendation_count": 0,
            "recommendations": [],
            "unavailable_recommendations": [{
                "category": "customer_retention",
                "reason": f"Customer recommendations require mapped fields: {', '.join(missing)}.",
            }],
            "method": "deterministic_rules",
        }

    rfm = get_customer_rfm(df, mapping=resolved)
    records = pd.DataFrame(rfm["results"])
    if records.empty:
        return {
            "row_count": int(len(df)),
            "available": False,
            "recommendation_count": 0,
            "recommendations": [],
            "unavailable_recommendations": [{
                "category": "customer_retention",
                "reason": "No valid customer transaction history was available for RFM analysis.",
            }],
            "method": "deterministic_rules",
        }

    positive_monetary = records.loc[records["monetary"] > 0, "monetary"]
    recommendations = []
    unavailable = []
    if positive_monetary.empty:
        unavailable.append({
            "category": "customer_retention",
            "reason": "No customers have positive net monetary value; high-value retention segments cannot be identified.",
        })
        value_threshold = None
    else:
        value_threshold = float(positive_monetary.quantile(0.75))
        at_risk = records[
            (records["recency_days"] >= at_risk_days)
            & (records["monetary"] >= value_threshold)
            & (records["monetary"] > 0)
        ].sort_values(["monetary", "recency_days"], ascending=[False, False])
        if not at_risk.empty:
            recommendations.append({
                "id": "retain_high_value_inactive_customers",
                "category": "customer_retention",
                "title": "Re-engage high-value inactive customers",
                "rationale": "Customers with relatively high positive historical spend have not purchased for an extended period within the dataset.",
                "recommended_action": "Review this segment and consider targeted, margin-aware win-back outreach; test a relevant product reminder or service follow-up before offering discounts.",
                "priority": "high" if int(at_risk["recency_days"].max()) >= 180 else "medium",
                "confidence": "medium",
                "evidence": {
                    "reference_date": rfm["reference_date"],
                    "at_risk_days_threshold": at_risk_days,
                    "positive_customer_monetary_75th_percentile": round(value_threshold, 2),
                    "at_risk_customer_count": int(len(at_risk)),
                    "total_customers": int(len(records)),
                    "sample_customers": [
                        {
                            "customer_id": str(row.customer_id),
                            "recency_days": int(row.recency_days),
                            "frequency": int(row.frequency),
                            "monetary": round(float(row.monetary), 2),
                        }
                        for row in at_risk.head(10).itertuples(index=False)
                    ],
                },
                "limitations": [
                    "Recency is measured against the latest valid date in the dataset, not today's date.",
                    "The 75th-percentile monetary threshold is relative to this dataset and is not a profitability measure.",
                    "No customer contact, discount or retention outcome is inferred from transaction history alone.",
                ],
                "method": "deterministic_rule",
            })
        else:
            unavailable.append({
                "category": "customer_retention",
                "reason": f"No positive-spend customers meet both the {at_risk_days}-day inactivity and top-quartile monetary criteria.",
            })

        frequency_threshold = float(records["frequency"].quantile(0.75))
        loyal = records[
            (records["recency_days"] <= recent_days)
            & (records["frequency"] >= frequency_threshold)
            & (records["monetary"] > 0)
        ].sort_values(["frequency", "monetary"], ascending=[False, False])
        if not loyal.empty:
            recommendations.append({
                "id": "nurture_recent_frequent_customers",
                "category": "customer_growth",
                "title": "Nurture recently active frequent customers",
                "rationale": "A segment of customers has purchased recently and has relatively high order frequency in this dataset.",
                "recommended_action": "Test relevant cross-sell, replenishment or loyalty engagement for this segment; compare repeat purchase and net revenue outcomes before expanding the campaign.",
                "priority": "medium",
                "confidence": "medium",
                "evidence": {
                    "reference_date": rfm["reference_date"],
                    "recent_days_threshold": recent_days,
                    "frequency_75th_percentile": round(frequency_threshold, 2),
                    "loyal_customer_count": int(len(loyal)),
                    "total_customers": int(len(records)),
                    "sample_customers": [
                        {
                            "customer_id": str(row.customer_id),
                            "recency_days": int(row.recency_days),
                            "frequency": int(row.frequency),
                            "monetary": round(float(row.monetary), 2),
                        }
                        for row in loyal.head(10).itertuples(index=False)
                    ],
                },
                "limitations": [
                    "Customer segments and thresholds are relative to this dataset's observed history.",
                    "Frequency counts distinct mapped orders; it does not establish future purchase intent or profitability.",
                ],
                "method": "deterministic_rule",
            })
        else:
            unavailable.append({
                "category": "customer_growth",
                "reason": f"No positive-spend customers meet both the {recent_days}-day recency and top-quartile frequency criteria.",
            })

    recommendations.sort(
        key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item["priority"]], item["id"])
    )
    return {
        "row_count": int(len(df)),
        "available": True,
        "reference_date": rfm["reference_date"],
        "customer_count": int(len(records)),
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "unavailable_recommendations": unavailable,
        "method": "deterministic_rules",
        "notes": [
            "Recency is measured relative to the latest valid transaction date in the dataset, not the current date.",
            "Monetary value is signed net revenue; customers with non-positive monetary value are not classified as high-value.",
            "Segments indicate observed historical patterns, not churn probability or causal effects.",
        ],
    }
