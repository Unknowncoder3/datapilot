import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.column_mapper import map_business_columns
from app.services.business_intelligence.sales_engine import _revenue_series


def _robust_z_scores(values: pd.Series) -> tuple[pd.Series, float, float]:
    median = float(values.median())
    mad = float((values - median).abs().median())
    if mad > 0:
        scores = 0.67448975 * (values - median) / mad
    else:
        scores = pd.Series(0.0, index=values.index)
        non_median = values != median
        scores.loc[non_median] = float("inf")
    return scores, median, mad


def _anomaly(
    anomaly_id: str,
    category: str,
    title: str,
    description: str,
    severity: str,
    score: float,
    evidence: dict,
    limitations: list[str] | None = None,
) -> dict:
    safe_score = float(score) if pd.notna(score) and score != float("inf") else 999.0
    return {
        "id": anomaly_id,
        "category": category,
        "title": title,
        "description": description,
        "severity": severity,
        "score": round(safe_score, 3),
        "evidence": evidence,
        "limitations": limitations or [],
        "method": "median_absolute_deviation",
    }


def detect_business_anomalies(
    df: pd.DataFrame,
    mapping: dict | None = None,
    sensitivity: float = 3.5,
    limit: int = 100,
    min_periods: int = 14,
) -> dict:
    """Detect robust statistical outliers without treating them as proof of fraud or error."""
    _validate_dataframe(df)
    if not isinstance(sensitivity, (int, float)) or isinstance(sensitivity, bool) or sensitivity <= 0:
        raise ValueError("sensitivity must be a positive number.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValueError("limit must be an integer between 1 and 500.")
    if not isinstance(min_periods, int) or isinstance(min_periods, bool) or min_periods < 5:
        raise ValueError("min_periods must be an integer of at least 5.")

    resolved = mapping or map_business_columns(df)["mapping"]
    anomalies = []
    unavailable = []

    revenue_role = resolved.get("revenue")
    revenue_available = (
        isinstance(revenue_role, str) and revenue_role in df.columns
    ) or (
        isinstance(revenue_role, dict)
        and revenue_role.get("type") == "derived"
        and all(column in df.columns for column in revenue_role.get("depends_on", []))
    )

    date_col = resolved.get("date")
    if revenue_available and isinstance(date_col, str) and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        frame = pd.DataFrame({
            "date": dates,
            "revenue": _revenue_series(df, resolved),
        }).dropna()
        if not frame.empty:
            frame["period"] = frame["date"].dt.strftime("%Y-%m-%d")
            daily = frame.groupby("period", sort=True)["revenue"].sum()
            if len(daily) >= min_periods:
                scores, median, mad = _robust_z_scores(daily)
                candidates = daily[scores.abs() >= sensitivity]
                for period, value in candidates.items():
                    score = float(scores.loc[period])
                    anomalies.append(_anomaly(
                        f"daily_revenue_{period}", "revenue",
                        "Unusual daily revenue",
                        f"Net revenue on {period} differs substantially from the dataset's daily median baseline.",
                        "high" if abs(score) >= sensitivity * 1.5 else "medium",
                        abs(score),
                        {
                            "period": str(period),
                            "revenue": round(float(value), 2),
                            "baseline_median": round(median, 2),
                            "median_absolute_deviation": round(mad, 2),
                            "robust_z_score": round(score, 3) if pd.notna(score) and abs(score) != float("inf") else None,
                            "direction": "above" if value > median else "below",
                            "observed_days": int(len(daily)),
                        },
                        ["Daily totals retain negative returns and cancellation values.", "A statistical outlier is a review signal, not evidence of an error or fraud."],
                    ))
            else:
                unavailable.append({
                    "category": "revenue",
                    "reason": f"At least {min_periods} observed days are required; found {len(daily)}."
                })
    else:
        unavailable.append({
            "category": "revenue",
            "reason": "A mapped date and revenue field (or quantity plus unit price) are required for daily revenue anomaly detection."
        })

    numeric_roles = ("quantity", "unit_price", "revenue")
    for role in numeric_roles:
        column = resolved.get(role)
        if isinstance(column, dict) and column.get("type") == "derived":
            continue
        if not isinstance(column, str) or column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(values) < min_periods:
            continue
        scores, median, mad = _robust_z_scores(values)
        candidates = values[scores.abs() >= sensitivity].sort_values(
            key=lambda series: scores.loc[series.index].abs(), ascending=False
        ).head(limit)
        for row_index, value in candidates.items():
            score = float(scores.loc[row_index])
            anomalies.append(_anomaly(
                f"transaction_{role}_{row_index}", "transaction",
                f"Unusual {role.replace('_', ' ')} value",
                f"A value in '{column}' is statistically unusual compared with the column's robust median baseline.",
                "high" if abs(score) >= sensitivity * 1.5 else "medium",
                abs(score),
                {
                    "row_index": int(row_index) if isinstance(row_index, (int,)) else str(row_index),
                    "column": column,
                    "value": float(value),
                    "baseline_median": round(median, 6),
                    "median_absolute_deviation": round(mad, 6),
                    "robust_z_score": round(score, 3) if pd.notna(score) and abs(score) != float("inf") else None,
                },
                ["Review the source transaction before taking action; unusual values can be legitimate."],
            ))

    anomalies.sort(key=lambda item: item["score"] or 0, reverse=True)
    return {
        "row_count": int(len(df)),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:limit],
        "unavailable_checks": unavailable,
        "method": "robust_mad",
        "parameters": {
            "sensitivity": float(sensitivity),
            "minimum_observations": min_periods,
            "limit": limit,
        },
        "notes": [
            "Anomalies are statistical review signals, not proof of fraud, error or causation.",
            "Signed revenue is preserved; negative returns and cancellation values are not silently removed.",
            "Daily revenue detection requires sufficient observed dates; incomplete periods can still appear as outliers."
        ],
    }
