import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.sales_engine import _revenue_series


def _insight(
    insight_id: str,
    category: str,
    title: str,
    summary: str,
    severity: str,
    metric: str | None = None,
    value=None,
    evidence: dict | None = None,
    confidence: str = "high",
    limitations: list[str] | None = None,
) -> dict:
    return {
        "id": insight_id,
        "category": category,
        "title": title,
        "summary": summary,
        "severity": severity,
        "metric": metric,
        "value": value,
        "evidence": evidence or {},
        "confidence": confidence,
        "limitations": limitations or [],
    }


def generate_business_insights(
    df: pd.DataFrame,
    mapping: dict | None = None,
    top_n: int = 5,
) -> dict:
    """Generate deterministic, evidence-backed insights from mapped business fields."""
    _validate_dataframe(df)
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 20:
        raise ValueError("top_n must be an integer between 1 and 20.")

    resolved = mapping or map_business_columns(df)["mapping"]
    insights = []
    unavailable = []

    revenue_role = resolved.get("revenue")
    revenue_available = (
        isinstance(revenue_role, str) and revenue_role in df.columns
    ) or (
        isinstance(revenue_role, dict)
        and revenue_role.get("type") == "derived"
        and all(col in df.columns for col in revenue_role.get("depends_on", []))
    )

    if revenue_available:
        revenue = _revenue_series(df, resolved)
        valid_revenue = revenue.dropna()
        if not valid_revenue.empty:
            total = float(valid_revenue.sum())
            negative_rows = int((valid_revenue < 0).sum())
            positive_rows = int((valid_revenue > 0).sum())
            insights.append(_insight(
                "revenue_summary", "performance", "Revenue overview",
                "Net revenue is calculated from the mapped revenue field; negative values remain included.",
                "positive" if total > 0 else "warning" if total < 0 else "neutral",
                "revenue", round(total, 2),
                {
                    "valid_rows": int(valid_revenue.size),
                    "positive_rows": positive_rows,
                    "negative_rows": negative_rows,
                    "negative_value_total": round(float(valid_revenue[valid_revenue < 0].sum()), 2),
                },
                limitations=["Negative revenue rows are retained and may represent returns, refunds or adjustments."],
            ))
    else:
        unavailable.append({
            "category": "performance",
            "reason": "Revenue requires a mapped revenue field or both quantity and unit price."
        })

    date_col = resolved.get("date")
    if isinstance(date_col, str) and date_col in df.columns and revenue_available:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        time_frame = pd.DataFrame({"date": dates, "revenue": _revenue_series(df, resolved)}).dropna()
        if not time_frame.empty:
            time_frame["period"] = time_frame["date"].dt.to_period("M").astype(str)
            monthly = time_frame.groupby("period", sort=True)["revenue"].sum()
            if len(monthly) >= 2:
                previous = float(monthly.iloc[-2])
                current = float(monthly.iloc[-1])
                if previous > 0:
                    change = (current - previous) / previous * 100
                    direction = "increased" if change > 0 else "decreased" if change < 0 else "was unchanged"
                    insights.append(_insight(
                        "monthly_revenue_change", "sales",
                        f"Monthly revenue {direction}",
                        f"Revenue {direction} by {abs(change):.2f}% in the latest observed month compared with the preceding observed month.",
                        "positive" if change > 0 else "warning" if change < 0 else "neutral",
                        "revenue_growth_percent", round(change, 2),
                        {
                            "latest_period": str(monthly.index[-1]),
                            "latest_revenue": round(current, 2),
                            "previous_period": str(monthly.index[-2]),
                            "previous_revenue": round(previous, 2),
                        },
                        limitations=["Comparison uses the latest two observed months, which may not be complete calendar months."],
                    ))
                else:
                    unavailable.append({
                        "category": "sales",
                        "reason": "Monthly growth is not calculated because the preceding observed month has zero or negative revenue."
                    })
            else:
                unavailable.append({
                    "category": "sales",
                    "reason": "At least two observed months are required for a month-over-month comparison."
                })
    else:
        unavailable.append({
            "category": "sales",
            "reason": "A mapped transaction date and revenue are required for time-based insights."
        })

    product_col = resolved.get("product_id")
    if revenue_available and isinstance(product_col, str) and product_col in df.columns:
        frame = pd.DataFrame({
            "product": df[product_col].astype("string").fillna("Unknown"),
            "revenue": _revenue_series(df, resolved),
        }).dropna(subset=["revenue"])
        if not frame.empty:
            grouped = frame.groupby("product")["revenue"].sum().sort_values(ascending=False)
            top = grouped.head(top_n)
            name_col = resolved.get("product_name")
            names = {}
            if isinstance(name_col, str) and name_col in df.columns:
                names = df.assign(_product=df[product_col].astype("string").fillna("Unknown")) \
                    .groupby("_product")[name_col].first().astype(str).to_dict()
            if not top.empty:
                product_id = str(top.index[0])
                insights.append(_insight(
                    "top_product", "product", "Highest-revenue product",
                    f"Product {names.get(product_id, product_id)} has the highest net revenue in this dataset.",
                    "positive", "product_revenue", round(float(top.iloc[0]), 2),
                    {
                        "product_id": product_id,
                        "product_name": names.get(product_id, product_id),
                        "top_products": [
                            {"product_id": str(key), "revenue": round(float(value), 2)}
                            for key, value in top.items()
                        ],
                    },
                    limitations=["Ranking uses signed net revenue; returns and negative adjustments reduce product revenue."],
                ))
    else:
        unavailable.append({
            "category": "product",
            "reason": "A mapped product identifier and revenue are required for product performance insights."
        })

    country_col = resolved.get("country") or resolved.get("region")
    if revenue_available and isinstance(country_col, str) and country_col in df.columns:
        frame = pd.DataFrame({
            "location": df[country_col].astype("string").fillna("Unknown"),
            "revenue": _revenue_series(df, resolved),
        }).dropna(subset=["revenue"])
        grouped = frame.groupby("location")["revenue"].sum().sort_values(ascending=False)
        if not grouped.empty:
            insights.append(_insight(
                "top_market", "geography", "Highest-revenue market",
                f"{grouped.index[0]} has the highest net revenue among the available geographic groups.",
                "positive", "market_revenue", round(float(grouped.iloc[0]), 2),
                {
                    "dimension": country_col,
                    "market": str(grouped.index[0]),
                    "top_markets": [
                        {"market": str(key), "revenue": round(float(value), 2)}
                        for key, value in grouped.head(top_n).items()
                    ],
                },
                limitations=["This is a revenue ranking, not a profitability or market-share comparison."],
            ))

    insights.sort(key=lambda item: (
        {"critical": 0, "warning": 1, "positive": 2, "neutral": 3}.get(item["severity"], 4),
        item["category"],
    ))
    return {
        "row_count": int(len(df)),
        "insight_count": len(insights),
        "insights": insights,
        "unavailable_insights": unavailable,
        "method": "deterministic_rules",
        "notes": [
            "Insights are generated from observed dataset values and mapped business fields.",
            "These findings describe patterns and contributions; they do not establish causation.",
            "No LLM-generated metrics or forecasts are used."
        ],
    }
