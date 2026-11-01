import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.sales_engine import _revenue_series


def _mapping_for(df: pd.DataFrame, mapping: dict | None) -> dict:
    return mapping or map_business_columns(df)["mapping"]


def _dimension_contribution(
    df: pd.DataFrame,
    revenue: pd.Series,
    column: str | None,
    label: str,
    top_n: int,
    previous_mask: pd.Series,
    current_mask: pd.Series,
) -> dict:
    if not isinstance(column, str) or column not in df.columns:
        return {
            "dimension": label,
            "available": False,
            "reason": f"A mapped {label} field is required.",
            "results": [],
        }

    frame = pd.DataFrame({
        "dimension_value": df[column].astype("string").fillna("Unknown"),
        "revenue": revenue,
        "previous": previous_mask,
        "current": current_mask,
    }).dropna(subset=["revenue"])

    previous = frame.loc[frame["previous"]].groupby("dimension_value")["revenue"].sum()
    current = frame.loc[frame["current"]].groupby("dimension_value")["revenue"].sum()
    comparison = pd.concat(
        [previous.rename("previous_revenue"), current.rename("current_revenue")],
        axis=1,
    ).fillna(0.0)
    comparison["change"] = comparison["current_revenue"] - comparison["previous_revenue"]
    total_change = float(comparison["change"].sum())
    comparison["contribution_percent"] = (
        comparison["change"] / total_change * 100 if total_change != 0 else 0.0
    )
    comparison = comparison.sort_values("change", ascending=False)
    results = []
    for value, row in comparison.head(top_n).iterrows():
        results.append({
            "value": str(value),
            "previous_revenue": round(float(row["previous_revenue"]), 2),
            "current_revenue": round(float(row["current_revenue"]), 2),
            "revenue_change": round(float(row["change"]), 2),
            "contribution_percent": round(float(row["contribution_percent"]), 2),
        })
    return {
        "dimension": label,
        "available": True,
        "total_groups": int(len(comparison)),
        "total_revenue_change": round(total_change, 2),
        "results": results,
        "notes": [
            "Contribution percentages are signed and can exceed 100% when groups offset one another.",
            "Only the highest positive contributors are returned; negative contributors may also materially affect the total.",
        ],
    }


def analyze_business_drivers(
    df: pd.DataFrame,
    mapping: dict | None = None,
    top_n: int = 10,
    frequency: str = "month",
) -> dict:
    """Explain the latest observed revenue change through mix and price-volume drivers."""
    _validate_dataframe(df)
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 50:
        raise ValueError("top_n must be an integer between 1 and 50.")
    if frequency not in {"month", "day"}:
        raise ValueError("Frequency must be 'month' or 'day'.")

    resolved = _mapping_for(df, mapping)
    revenue = _revenue_series(df, resolved)
    date_col = resolved.get("date")
    if not isinstance(date_col, str) or date_col not in df.columns:
        return {
            "row_count": int(len(df)),
            "available": False,
            "reason": "Business driver comparison requires a mapped transaction date.",
            "unavailable_analyses": ["period_comparison", "price_volume", "customer", "product", "geography"],
        }

    dates = pd.to_datetime(df[date_col], errors="coerce")
    frame = pd.DataFrame({"date": dates, "revenue": revenue}, index=df.index).dropna()
    if frame.empty:
        raise ValueError("No valid transaction dates and revenue values were found.")

    frame["period"] = (
        frame["date"].dt.to_period("M").astype(str)
        if frequency == "month"
        else frame["date"].dt.strftime("%Y-%m-%d")
    )
    periods = sorted(frame["period"].unique())
    if len(periods) < 2:
        return {
            "row_count": int(len(df)),
            "available": False,
            "frequency": frequency,
            "observed_periods": len(periods),
            "reason": "At least two observed periods are required for driver comparison.",
            "unavailable_analyses": ["period_comparison", "price_volume", "customer", "product", "geography"],
        }

    previous_period, current_period = periods[-2], periods[-1]
    previous_mask = frame["period"].eq(previous_period)
    current_mask = frame["period"].eq(current_period)
    previous_revenue = float(frame.loc[previous_mask, "revenue"].sum())
    current_revenue = float(frame.loc[current_mask, "revenue"].sum())
    change = current_revenue - previous_revenue
    change_percent = (
        round(change / previous_revenue * 100, 2) if previous_revenue > 0 else None
    )

    result = {
        "row_count": int(len(df)),
        "available": True,
        "frequency": frequency,
        "comparison": {
            "previous_period": previous_period,
            "current_period": current_period,
            "previous_revenue": round(previous_revenue, 2),
            "current_revenue": round(current_revenue, 2),
            "revenue_change": round(change, 2),
            "revenue_change_percent": change_percent,
            "direction": "increased" if change > 0 else "decreased" if change < 0 else "unchanged",
            "previous_rows": int(previous_mask.sum()),
            "current_rows": int(current_mask.sum()),
        },
        "drivers": {},
        "unavailable_analyses": [],
    }

    quantity_col = resolved.get("quantity")
    price_col = resolved.get("unit_price")
    if (
        isinstance(quantity_col, str) and quantity_col in df.columns
        and isinstance(price_col, str) and price_col in df.columns
        and isinstance(resolved.get("revenue"), dict)
        and resolved["revenue"].get("type") == "derived"
    ):
        q = pd.to_numeric(df[quantity_col], errors="coerce")
        p = pd.to_numeric(df[price_col], errors="coerce")
        valid = dates.notna() & q.notna() & p.notna()
        previous_valid = valid & dates.map(
            lambda value: value.to_period("M").strftime("%Y-%m") == previous_period
            if pd.notna(value) and frequency == "month"
            else value.strftime("%Y-%m-%d") == previous_period if pd.notna(value) else False
        )
        current_valid = valid & dates.map(
            lambda value: value.to_period("M").strftime("%Y-%m") == current_period
            if pd.notna(value) and frequency == "month"
            else value.strftime("%Y-%m-%d") == current_period if pd.notna(value) else False
        )
        previous_q = float(q[previous_valid].sum())
        current_q = float(q[current_valid].sum())
        previous_r = float((q[previous_valid] * p[previous_valid]).sum())
        current_r = float((q[current_valid] * p[current_valid]).sum())
        previous_p = previous_r / previous_q if previous_q != 0 else None
        current_p = current_r / current_q if current_q != 0 else None
        if previous_p is not None and current_p is not None:
            volume_effect = (current_q - previous_q) * (previous_p + current_p) / 2
            price_effect = (current_p - previous_p) * (previous_q + current_q) / 2
            result["drivers"]["price_volume"] = {
                "available": True,
                "previous_units": round(previous_q, 2),
                "current_units": round(current_q, 2),
                "previous_weighted_unit_price": round(previous_p, 4),
                "current_weighted_unit_price": round(current_p, 4),
                "volume_effect": round(volume_effect, 2),
                "price_effect": round(price_effect, 2),
                "explained_revenue_change": round(volume_effect + price_effect, 2),
                "reconciliation_difference": round(
                    (current_r - previous_r) - (volume_effect + price_effect), 6
                ),
                "method": "symmetric_shapley_decomposition",
                "notes": [
                    "Volume and price effects split the interaction term equally.",
                    "Weighted unit price is net revenue divided by net units; returns and negative quantities remain included.",
                    "Decomposition is unavailable if either period has zero net units.",
                ],
            }
        else:
            result["drivers"]["price_volume"] = {
                "available": False,
                "reason": "Price-volume decomposition requires non-zero net units in both periods.",
            }
            result["unavailable_analyses"].append("price_volume")
    else:
        result["drivers"]["price_volume"] = {
            "available": False,
            "reason": "Price-volume decomposition requires mapped quantity, unit price, and revenue derived from quantity × unit price.",
        }
        result["unavailable_analyses"].append("price_volume")

    dimensions = [
        ("customer", resolved.get("customer_id"), "customer"),
        ("product", resolved.get("product_id"), "product"),
        ("geography", resolved.get("country") or resolved.get("region"), "geography"),
    ]
    for key, column, label in dimensions:
        analysis = _dimension_contribution(
            df, revenue, column, label, top_n,
            frame["period"].eq(previous_period).reindex(df.index, fill_value=False),
            frame["period"].eq(current_period).reindex(df.index, fill_value=False),
        )
        result["drivers"][key] = analysis
        if not analysis["available"]:
            result["unavailable_analyses"].append(key)

    result["notes"] = [
        "Driver analysis compares the latest two observed periods, not necessarily complete calendar periods.",
        "Revenue remains signed; returns, refunds and cancellation values are not silently removed.",
        "Contribution analysis describes association and arithmetic attribution, not causal proof.",
        "Profitability cannot be inferred without valid cost or profit fields.",
    ]
    return result
