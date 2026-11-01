import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.sales_engine import _revenue_series


def generate_market_recommendations(
    df: pd.DataFrame,
    mapping: dict | None = None,
    growth_threshold: float = 10.0,
    minimum_previous_revenue: float = 100.0,
    top_n: int = 10,
) -> dict:
    """Identify observed country-level growth and decline; do not infer market potential."""
    _validate_dataframe(df)
    if not isinstance(growth_threshold, (int, float)) or isinstance(growth_threshold, bool) or not 0 < growth_threshold <= 100:
        raise ValueError("growth_threshold must be greater than 0 and at most 100.")
    if not isinstance(minimum_previous_revenue, (int, float)) or isinstance(minimum_previous_revenue, bool) or minimum_previous_revenue < 0:
        raise ValueError("minimum_previous_revenue must be zero or greater.")
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 50:
        raise ValueError("top_n must be an integer between 1 and 50.")

    resolved = mapping or map_business_columns(df)["mapping"]
    country_col, date_col = resolved.get("country"), resolved.get("date")
    revenue_role = resolved.get("revenue")
    revenue_available = (
        isinstance(revenue_role, str) and revenue_role in df.columns
    ) or (
        isinstance(revenue_role, dict)
        and revenue_role.get("type") == "derived"
        and all(col in df.columns for col in revenue_role.get("depends_on", []))
    )
    missing = []
    if not isinstance(country_col, str) or country_col not in df.columns:
        missing.append("country")
    if not revenue_available:
        missing.append("revenue")
    if missing:
        return {
            "row_count": int(len(df)), "available": False,
            "recommendation_count": 0, "recommendations": [],
            "unavailable_recommendations": [{
                "category": "market_performance",
                "reason": f"Market recommendations require mapped fields: {', '.join(missing)}.",
            }],
            "method": "deterministic_rules",
        }

    revenue = _revenue_series(df, resolved)
    countries = df[country_col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    country_totals = pd.DataFrame({"country": countries, "revenue": revenue}).dropna(subset=["revenue"])
    grouped = country_totals.groupby("country")["revenue"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    recommendations = []
    unavailable = []
    date_available = isinstance(date_col, str) and date_col in df.columns

    if date_available:
        period_frame = pd.DataFrame({
            "country": countries,
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "revenue": revenue,
        }).dropna(subset=["date", "revenue"])
        if not period_frame.empty:
            period_frame["period"] = period_frame["date"].dt.to_period("M").astype(str)
            periods = sorted(period_frame["period"].unique())
            if len(periods) >= 2:
                previous_period, current_period = periods[-2], periods[-1]
                pivot = period_frame[period_frame["period"].isin([previous_period, current_period])].pivot_table(
                    index="country", columns="period", values="revenue", aggfunc="sum", fill_value=0
                )
                for period in (previous_period, current_period):
                    if period not in pivot.columns:
                        pivot[period] = 0.0
                pivot["previous_revenue"] = pivot[previous_period]
                pivot["current_revenue"] = pivot[current_period]
                pivot = pivot[pivot["previous_revenue"] >= minimum_previous_revenue].copy()
                pivot["change"] = pivot["current_revenue"] - pivot["previous_revenue"]
                pivot["change_percent"] = pivot["change"] / pivot["previous_revenue"] * 100
                growing = pivot[pivot["change_percent"] >= growth_threshold].sort_values("current_revenue", ascending=False).head(top_n)
                declining = pivot[pivot["change_percent"] <= -growth_threshold].sort_values("change_percent").head(top_n)

                def serialize(rows):
                    return [
                        {
                            "country": str(country),
                            "previous_revenue": round(float(row["previous_revenue"]), 2),
                            "current_revenue": round(float(row["current_revenue"]), 2),
                            "revenue_change": round(float(row["change"]), 2),
                            "change_percent": round(float(row["change_percent"]), 2),
                        }
                        for country, row in rows.iterrows()
                    ]

                if not growing.empty:
                    recommendations.append({
                        "id": "validate_growing_markets",
                        "category": "market_opportunity",
                        "title": "Validate countries with growing revenue",
                        "rationale": "These countries show revenue growth above the configured threshold between the latest two observed months.",
                        "recommended_action": "Validate repeat demand, order economics, fulfilment capacity, local requirements and customer concentration before testing additional distribution or marketing in these countries.",
                        "priority": "medium",
                        "confidence": "medium",
                        "evidence": {
                            "previous_period": previous_period, "current_period": current_period,
                            "growth_threshold_percent": growth_threshold,
                            "minimum_previous_revenue": minimum_previous_revenue,
                            "countries": serialize(growing),
                        },
                        "limitations": [
                            "Revenue growth alone does not establish market size, addressable demand or profitability.",
                            "The latest observed month may be incomplete and the comparison is not seasonally adjusted.",
                        ],
                        "method": "deterministic_rule",
                    })
                if not declining.empty:
                    recommendations.append({
                        "id": "investigate_declining_markets",
                        "category": "market_performance",
                        "title": "Investigate countries with declining revenue",
                        "rationale": "These countries show revenue declines beyond the configured threshold.",
                        "recommended_action": "Review order volume, returns, customer concentration, fulfilment issues and trading-day coverage before reducing investment or changing market coverage.",
                        "priority": "medium",
                        "confidence": "medium",
                        "evidence": {
                            "previous_period": previous_period, "current_period": current_period,
                            "growth_threshold_percent": growth_threshold,
                            "minimum_previous_revenue": minimum_previous_revenue,
                            "countries": serialize(declining),
                        },
                        "limitations": [
                            "Revenue declines do not establish why performance changed.",
                            "The latest observed month may be incomplete and the comparison is not seasonally adjusted.",
                        ],
                        "method": "deterministic_rule",
                    })
                if growing.empty and declining.empty:
                    unavailable.append({
                        "category": "market_performance",
                        "reason": "No country met the configured baseline and percentage-change thresholds.",
                    })
            else:
                unavailable.append({
                    "category": "market_performance",
                    "reason": "At least two observed months are required for country trend recommendations.",
                })
        else:
            unavailable.append({
                "category": "market_performance",
                "reason": "No valid country, date and revenue rows were found.",
            })
    else:
        unavailable.append({
            "category": "market_performance",
            "reason": "A mapped transaction date is required for country trend recommendations.",
        })

    top_markets = [
        {"country": str(country), "net_revenue": round(float(row["sum"]), 2), "transaction_rows": int(row["count"])}
        for country, row in grouped.head(top_n).iterrows()
    ]
    recommendations.sort(key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item["priority"]], item["id"]))
    return {
        "row_count": int(len(df)), "available": True,
        "country_count": int(len(grouped)), "top_markets": top_markets,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "unavailable_recommendations": unavailable,
        "method": "deterministic_rules",
        "notes": [
            "Country performance is based on signed net revenue, including negative returns and adjustments.",
            "Country revenue growth is a signal for further validation, not proof of market potential or profitability.",
            "Month-over-month comparisons use the latest two observed calendar months, which may be incomplete.",
        ],
    }
