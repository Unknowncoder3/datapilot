import numpy as np
import pandas as pd

from app.services.analytics_engine import _validate_dataframe
from app.services.business_intelligence.sales_engine import (
    _base_sales_frame,
    _resolve_mapping,
)


def _fit_trend_with_seasonality(values: np.ndarray, seasonal_period: int | None):
    """Fit a linear trend and, when enough cycles exist, additive seasonal effects."""
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    trend = intercept + slope * x
    seasonal = np.zeros(len(values), dtype=float)
    seasonal_effects = None

    # Require at least two complete cycles; otherwise seasonal estimates are
    # too weak to be useful and the transparent trend-only baseline is used.
    if seasonal_period and len(values) >= seasonal_period * 2:
        residuals = values - trend
        slots = np.arange(len(values)) % seasonal_period
        effects = np.array([
            float(residuals[slots == slot].mean()) if np.any(slots == slot) else 0.0
            for slot in range(seasonal_period)
        ])
        effects -= effects.mean()
        seasonal = effects[slots]
        seasonal_effects = effects.tolist()

    fitted = trend + seasonal
    errors = values - fitted
    residual_std = float(np.std(errors, ddof=1)) if len(errors) > 2 else 0.0
    return slope, intercept, fitted, residual_std, seasonal_effects


def forecast_revenue(
    df: pd.DataFrame,
    horizon: int = 6,
    frequency: str = "month",
    mapping: dict | None = None,
) -> dict:
    """Build a revenue forecast with optional additive seasonality."""
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
        seasonal_period = 12
    else:
        frame["period"] = frame["date"].dt.floor("D")
        period_freq = "D"
        seasonal_period = 7

    grouped = frame.groupby("period", sort=True)["revenue"].sum().dropna()
    if len(grouped) < 3:
        raise ValueError("At least 3 historical periods are required to forecast.")

    full_index = pd.period_range(grouped.index.min(), grouped.index.max(), freq=period_freq)
    grouped = grouped.reindex(full_index, fill_value=0.0)
    values = grouped.astype(float).to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("Historical revenue contains non-finite values.")

    slope, intercept, fitted, residual_std, seasonal_effects = _fit_trend_with_seasonality(
        values, seasonal_period
    )
    future_x = np.arange(len(values), len(values) + horizon, dtype=float)
    predictions = intercept + slope * future_x
    if seasonal_effects is not None:
        future_slots = np.arange(len(values), len(values) + horizon) % seasonal_period
        predictions = predictions + np.asarray(seasonal_effects)[future_slots]

    # Approximate uncertainty expands with forecast distance. This is a
    # heuristic band, not a formal statistical prediction interval.
    steps = np.arange(1, horizon + 1, dtype=float)
    margins = 1.96 * residual_std * np.sqrt(1.0 + steps / max(len(values), 1))
    lower = predictions - margins
    upper = predictions + margins

    if frequency == "month":
        future_periods = pd.period_range(grouped.index[-1] + 1, periods=horizon, freq="M")
        labels = [period.strftime("%Y-%m") for period in future_periods]
        historical_labels = [period.strftime("%Y-%m") for period in grouped.index]
    else:
        future_periods = pd.date_range(
            grouped.index[-1].to_timestamp() + pd.Timedelta(days=1),
            periods=horizon,
            freq="D",
        )
        labels = [date.strftime("%Y-%m-%d") for date in future_periods]
        historical_labels = [period.strftime("%Y-%m-%d") for period in grouped.index]

    model = "linear_trend_with_additive_seasonality" if seasonal_effects is not None else "linear_trend_baseline"
    notes = [
        "Forecasts are estimates based on historical revenue and are not guarantees.",
        "The uncertainty band is a heuristic based on residual dispersion and forecast distance; it is not a formal prediction interval.",
        "Missing calendar periods in the historical series are filled with zero revenue.",
    ]
    if seasonal_effects is None:
        notes.append(
            f"Seasonality was not fitted because at least {seasonal_period * 2} historical "
            f"{'months' if frequency == 'month' else 'days'} are needed; trend-only baseline was used."
        )
    else:
        notes.append(
            f"Additive seasonality was fitted using a {seasonal_period}-period cycle and at least two observed cycles."
        )

    return {
        "frequency": frequency,
        "target": "revenue",
        "model": model,
        "seasonality_period": seasonal_period if seasonal_effects is not None else None,
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
        "notes": notes,
    }
