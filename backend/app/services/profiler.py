from pathlib import Path

import numpy as np
import pandas as pd



import re
from pathlib import Path
import pandas as pd


DATE_COLUMN_HINTS = {
    "date", "time", "timestamp", "created_at",
    "updated_at", "order_date", "transaction_date",
    "purchase_date", "delivery_date"
}


def read_dataset(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    for column in df.columns:
        series = df[column]

        if not pd.api.types.is_object_dtype(series):
            continue

        name = str(column).strip().lower()
        normalized_name = name.replace(" ", "_")

        has_date_hint = (
            normalized_name in DATE_COLUMN_HINTS
            or any(
                token in normalized_name
                for token in ("_date", "_time", "timestamp")
            )
        )

        sample = series.dropna().astype(str).head(20)

        looks_like_iso_date = (
            len(sample) > 0
            and sample.str.match(
                r"^\d{4}-\d{2}-\d{2}([ T].*)?$"
            ).mean() >= 0.8
        )

        if not (has_date_hint or looks_like_iso_date):
            continue

        parsed = pd.to_datetime(
            series,
            errors="coerce",
            format="mixed"
        )

        valid_ratio = parsed.notna().sum() / max(series.notna().sum(), 1)

        if valid_ratio >= 0.8:
            df[column] = parsed

    return df



def _safe_number(value):
    """Convert pandas/numpy numeric values into JSON-safe Python values."""
    if pd.isna(value):
        return None

    result = float(value)

    if not np.isfinite(result):
        return None

    return result


def infer_semantic_type(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    return "categorical"


def _numeric_profile(series):
    values = series.dropna()

    if values.empty:
        return {
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "q1": None,
            "q3": None,
            "outlier_count": 0,
        }

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outlier_count = int(
        ((values < lower_bound) | (values > upper_bound)).sum()
    )

    return {
        "mean": _safe_number(values.mean()),
        "median": _safe_number(values.median()),
        "std": _safe_number(values.std()),
        "min": _safe_number(values.min()),
        "max": _safe_number(values.max()),
        "q1": _safe_number(q1),
        "q3": _safe_number(q3),
        "outlier_count": outlier_count,
    }


def _categorical_profile(series):
    values = series.dropna()
    frequencies = values.value_counts().head(5)

    top_values = []

    for value, count in frequencies.items():
        top_values.append({
            "value": str(value),
            "count": int(count),
            "percentage": round(
                (int(count) / len(values)) * 100, 2
            ) if len(values) else 0,
        })

    return {
        "top_values": top_values,
    }


def _datetime_profile(series):
    values = series.dropna()

    if values.empty:
        return {
            "earliest": None,
            "latest": None,
        }

    return {
        "earliest": values.min().isoformat(),
        "latest": values.max().isoformat(),
    }


def profile_dataframe(df):
    columns = []

    for name in df.columns:
        series = df[name]
        missing = int(series.isna().sum())
        total = len(series)

        semantic_type = infer_semantic_type(series)

        column_profile = {
            "name": str(name),
            "dtype": str(series.dtype),
            "semantic_type": semantic_type,
            "missing": missing,
            "missing_percentage": round(
                (missing / total) * 100, 2
            ) if total else 0,
            "unique": int(series.nunique(dropna=True)),
            "sample_values": [
                str(value)
                for value in series.dropna().head(5).tolist()
            ],
        }

        if semantic_type == "numeric":
            column_profile["statistics"] = _numeric_profile(series)

        elif semantic_type == "categorical":
            column_profile["statistics"] = _categorical_profile(series)

        elif semantic_type == "datetime":
            column_profile["statistics"] = _datetime_profile(series)

        columns.append(column_profile)

    row_count = int(len(df))
    column_count = int(len(df.columns))
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    total_cells = row_count * column_count

    completeness = (
        1 - (missing_cells / total_cells)
        if total_cells else 1
    )

    row_uniqueness = (
        1 - (duplicate_rows / row_count)
        if row_count else 1
    )

    # Heuristic score: 70% completeness + 30% row uniqueness.
    quality_score = round(
        (completeness * 70 + row_uniqueness * 30), 2
    )

    return {
        "row_count": row_count,
        "column_count": column_count,
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "quality_score": quality_score,
        "columns": columns,
    }
