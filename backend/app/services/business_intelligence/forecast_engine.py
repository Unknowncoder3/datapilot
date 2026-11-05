import numpy as np
import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.sales_engine import (
    _base_sales_frame,
    _resolve_mapping,
)


def forecast_revenue(
    df: pd.DataFrame,
    horizon: int = 6,
    frequency: str = "month",
    mapping: dict | None = None,
) -> dict:
    """Build a transparent baseline revenue forecast from historical aggregates."""
    _validate_dataframe(df)

    if not isinstance(horizon, int) or isinstance(horizon, bool) or not 1 <= horizon <= 24:
        raise ValueError("Forecast horizon must be an integer between 1 and 24.")
    if frequency not in {"month", "day"}:
        raise ValueError("Frequency must be 'month' or 'day'.")

    resolved = _resolve_mapping(df, mapping)
    frame = _base_sales_frame(df, resolved).dropna(subset=["date"])
    if frame.empty:
        raise ValueError("No valid transaction dates were found.")

    if frequency == "month":
        frame["period"] = frame["date"].dt.to_period("M")
        period_freq = "M"
    else:
        frame["period"] = frame["date"].dt.floor("D")
        period_freq = "D"

    grouped = frame.groupby("period", sort=True)["revenue"].sum().dropna()
    if len(grouped) < 3:
        raise ValueError("At least 3 historical periods are required to forecast.")

    # Fill missing calendar periods with zero revenue so the trend uses a
    # continuous timeline rather than skipping periods with no transactions.
    full_index = pd.period_range(grouped.index.min(), grouped.index.max(), freq=period_freq)
    grouped = grouped.reindex(full_index, fill_value=0.0)
    values = grouped.astype(float).to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("Historical revenue contains non-finite values.")

    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    fitted = intercept + slope * x
    residuals = values - fitted
    residual_std = float(np.std(residuals, ddof=1)) if len(values) > 2 else 0.0

    future_x = np.arange(len(values), len(values) + horizon, dtype=float)
    predictions = intercept + slope * future_x
    # A simple approximate band based on historical residual dispersion.
    margin = 1.96 * residual_std
    lower = predictions - margin
    upper = predictions + margin

    if frequency == "month":
        future_periods = pd.period_range(grouped.index[-1] + 1, periods=horizon, freq="M")
        labels = [period.strftime("%Y-%m") for period in future_periods]
        historical_labels = [period.strftime("%Y-%m") for period in grouped.index]
    else:
        future_periods = pd.date_range(grouped.index[-1].to_timestamp() + pd.Timedelta(days=1), periods=horizon, freq="D")
        labels = [date.strftime("%Y-%m-%d") for date in future_periods]
        historical_labels = [period.strftime("%Y-%m-%d") for period in grouped.index]

    return {
        "frequency": frequency,
        "target": "revenue",
        "model": "linear_trend_baseline",
        "historical_periods": len(values),
        "forecast_horizon": horizon,
        "historical": [
            {"period": label, "actual": round(float(value), 2), "fitted": round(float(fit), 2)}
            for label, value, fit in zip(historical_labels, values, fitted)
        ],
        "forecast": [
            {
                "period": label,
                "prediction": round(float(prediction), 2),
                "lower_bound": round(float(low), 2),
                "upper_bound": round(float(high), 2),
            }
            for label, prediction, low, high in zip(labels, predictions, lower, upper)
        ],
        "notes": [
            "This is a baseline linear-trend forecast, not a guarantee.",
            "The approximate 95% band uses historical residual standard deviation and is not a formal prediction interval.",
            "Missing calendar periods in the historical series are filled with zero revenue.",
        ],
    }
