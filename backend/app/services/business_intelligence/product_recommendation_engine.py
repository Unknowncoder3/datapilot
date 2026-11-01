import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.sales_engine import _revenue_series


def generate_product_recommendations(
    df: pd.DataFrame,
    mapping: dict | None = None,
    change_threshold: float = 10.0,
    top_n: int = 10,
) -> dict:
    """Generate product-level actions from signed revenue and observed monthly changes."""
    _validate_dataframe(df)
    if not isinstance(change_threshold, (int, float)) or isinstance(change_threshold, bool) or not 0 < change_threshold <= 100:
        raise ValueError("change_threshold must be greater than 0 and at most 100.")
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 50:
        raise ValueError("top_n must be an integer between 1 and 50.")

    resolved = mapping or map_business_columns(df)["mapping"]
    product_col = resolved.get("product_id")
    revenue_role = resolved.get("revenue")
    revenue_available = (
        isinstance(revenue_role, str) and revenue_role in df.columns
    ) or (
        isinstance(revenue_role, dict)
        and revenue_role.get("type") == "derived"
        and all(col in df.columns for col in revenue_role.get("depends_on", []))
    )
    missing = []
    if not isinstance(product_col, str) or product_col not in df.columns:
        missing.append("product_id")
    if not revenue_available:
        missing.append("revenue")
    if missing:
        return {
            "row_count": int(len(df)),
            "available": False,
            "recommendation_count": 0,
            "recommendations": [],
            "unavailable_recommendations": [{
                "category": "product_performance",
                "reason": f"Product recommendations require mapped fields: {', '.join(missing)}.",
            }],
            "method": "deterministic_rules",
        }

    frame = pd.DataFrame({
        "product_id": df[product_col].astype("string"),
        "revenue": _revenue_series(df, resolved),
    }, index=df.index).dropna(subset=["product_id", "revenue"])
    name_col = resolved.get("product_name")
    if isinstance(name_col, str) and name_col in df.columns:
        frame["product_name"] = df[name_col].astype("string")
    else:
        frame["product_name"] = frame["product_id"]
    quantity_col = resolved.get("quantity")
    if isinstance(quantity_col, str) and quantity_col in df.columns:
        frame["quantity"] = pd.to_numeric(df[quantity_col], errors="coerce")
    else:
        frame["quantity"] = None

    grouped = frame.groupby("product_id", dropna=False).agg(
        revenue=("revenue", "sum"),
        quantity=("quantity", "sum"),
        product_name=("product_name", "first"),
    )
    recommendations = []
    negative_products = grouped[grouped["revenue"] < 0].sort_values("revenue").head(top_n)
    if not negative_products.empty:
        recommendations.append({
            "id": "review_negative_net_revenue_products",
            "category": "product_quality",
            "title": "Review products with negative net revenue",
            "rationale": "Some products have negative cumulative net revenue after signed transaction values are included.",
            "recommended_action": "Inspect returns, refunds, cancellations, pricing and product records for these products; distinguish expected return-heavy items from data-quality or operational issues before changing assortment decisions.",
            "priority": "high",
            "confidence": "medium",
            "evidence": {
                "negative_product_count": int((grouped["revenue"] < 0).sum()),
                "products": [
                    {
                        "product_id": str(product_id),
                        "product_name": str(row["product_name"]),
                        "net_revenue": round(float(row["revenue"]), 2),
                        "net_quantity": round(float(row["quantity"]), 2) if pd.notna(row["quantity"]) else None,
                    }
                    for product_id, row in negative_products.iterrows()
                ],
            },
            "limitations": [
                "Negative net revenue may reflect legitimate returns or adjustments; it is not proof of a defective product.",
                "No product cost or margin is inferred.",
            ],
            "method": "deterministic_rule",
        })

    date_col = resolved.get("date")
    unavailable = []
    if isinstance(date_col, str) and date_col in df.columns:
        time_frame = pd.DataFrame({
            "product_id": df[product_col].astype("string"),
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "revenue": _revenue_series(df, resolved),
        }).dropna(subset=["product_id", "date", "revenue"])
        if not time_frame.empty:
            time_frame["period"] = time_frame["date"].dt.to_period("M").astype(str)
            periods = sorted(time_frame["period"].unique())
            if len(periods) >= 2:
                previous_period, current_period = periods[-2], periods[-1]
                product_period = time_frame[time_frame["period"].isin([previous_period, current_period])].pivot_table(
                    index="product_id", columns="period", values="revenue", aggfunc="sum", fill_value=0
                )
                for period in (previous_period, current_period):
                    if period not in product_period.columns:
                        product_period[period] = 0.0
                product_period["change"] = product_period[current_period] - product_period[previous_period]
                comparable = product_period[product_period[previous_period] > 0].copy()
                comparable["change_percent"] = (
                    (comparable[current_period] - comparable[previous_period])
                    / comparable[previous_period] * 100
                )
                declining = comparable[comparable["change_percent"] <= -change_threshold].sort_values("change_percent").head(top_n)
                growing = comparable[comparable["change_percent"] >= change_threshold].sort_values("change_percent", ascending=False).head(top_n)
                names = frame.groupby("product_id")["product_name"].first().to_dict()

                def product_rows(selected):
                    return [
                        {
                            "product_id": str(product_id),
                            "product_name": str(names.get(product_id, product_id)),
                            "previous_revenue": round(float(row[previous_period]), 2),
                            "current_revenue": round(float(row[current_period]), 2),
                            "revenue_change": round(float(row["change"]), 2),
                            "change_percent": round(float(row["change_percent"]), 2),
                        }
                        for product_id, row in selected.iterrows()
                    ]

                if not declining.empty:
                    recommendations.append({
                        "id": "investigate_declining_products",
                        "category": "product_performance",
                        "title": "Investigate products with declining revenue",
                        "rationale": "These products recorded a material revenue decline between the latest two observed months.",
                        "recommended_action": "Review availability, pricing, customer demand, returns and promotion history for the listed products; compare equivalent trading days before changing stock or marketing plans.",
                        "priority": "high" if float(declining["change_percent"].min()) <= -25 else "medium",
                        "confidence": "medium",
                        "evidence": {
                            "previous_period": previous_period,
                            "current_period": current_period,
                            "threshold_percent": change_threshold,
                            "declining_product_count": int(len(declining)),
                            "products": product_rows(declining),
                        },
                        "limitations": [
                            "The latest observed month may be incomplete and the comparison is not seasonally adjusted.",
                            "Products with zero or negative previous-period revenue are excluded from percentage-change analysis.",
                            "Revenue changes do not establish causation or product profitability.",
                        ],
                        "method": "deterministic_rule",
                    })
                if not growing.empty:
                    recommendations.append({
                        "id": "validate_growing_products",
                        "category": "product_opportunity",
                        "title": "Validate products with growing revenue",
                        "rationale": "These products recorded material revenue growth between the latest two observed months.",
                        "recommended_action": "Check whether growth is supported by repeat demand and adequate stock; validate returns and margins before increasing inventory or promotional spend.",
                        "priority": "medium",
                        "confidence": "medium",
                        "evidence": {
                            "previous_period": previous_period,
                            "current_period": current_period,
                            "threshold_percent": change_threshold,
                            "growing_product_count": int(len(growing)),
                            "products": product_rows(growing),
                        },
                        "limitations": [
                            "The latest observed month may be incomplete and the comparison is not seasonally adjusted.",
                            "Revenue growth does not establish profitability or future demand.",
                        ],
                        "method": "deterministic_rule",
                    })
                if declining.empty and growing.empty:
                    unavailable.append({
                        "category": "product_performance",
                        "reason": "No products met the configured positive-baseline revenue change threshold.",
                    })
            else:
                unavailable.append({
                    "category": "product_performance",
                    "reason": "At least two observed months are required for product trend recommendations.",
                })
        else:
            unavailable.append({
                "category": "product_performance",
                "reason": "No valid product, date and revenue rows were found for trend analysis.",
            })
    else:
        unavailable.append({
            "category": "product_performance",
            "reason": "A mapped transaction date is required for product trend recommendations.",
        })

    recommendations.sort(
        key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item["priority"]], item["id"])
    )
    return {
        "row_count": int(len(df)),
        "available": True,
        "product_count": int(len(grouped)),
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "unavailable_recommendations": unavailable,
        "method": "deterministic_rules",
        "notes": [
            "Product revenue uses signed values; negative returns and adjustments are retained.",
            "Month-over-month comparisons use the latest two observed calendar months, which may be incomplete.",
            "No cost, margin, inventory availability or causal effect is inferred when those fields are unavailable.",
        ],
    }
