import numpy as np
import pandas as pd


SUPPORTED_AGGREGATIONS = {
    "sum",
    "mean",
    "median",
    "min",
    "max",
    "count",
    "std",
}


def _clean_value(value):
    """Convert Pandas and NumPy values into JSON-safe Python values."""
    if value is None:
        return None

    if isinstance(value, dict):
        return {str(key): _clean_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_clean_value(item) for item in value]

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, np.generic):
        return value.item()

    return value


def _validate_dataframe(df: pd.DataFrame):
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a Pandas DataFrame.")

    if df.empty:
        raise ValueError("Cannot analyze an empty dataset.")

    if len(df.columns) == 0:
        raise ValueError("Dataset has no columns.")


def get_analytics_overview(df: pd.DataFrame) -> dict:
    """Return a high-level analytical overview of a dataset."""
    _validate_dataframe(df)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    datetime_columns = df.select_dtypes(include=["datetime"]).columns.tolist()
    boolean_columns = df.select_dtypes(include=["bool"]).columns.tolist()

    categorical_columns = [
        column
        for column in df.columns
        if column not in numeric_columns
        and column not in datetime_columns
        and column not in boolean_columns
    ]

    column_details = []

    for column in df.columns:
        series = df[column]

        column_details.append({
            "column": str(column),
            "data_type": str(series.dtype),
            "non_null_count": int(series.count()),
            "missing_count": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
        })

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "numeric_column_count": len(numeric_columns),
        "categorical_column_count": len(categorical_columns),
        "datetime_column_count": len(datetime_columns),
        "boolean_column_count": len(boolean_columns),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_usage_mb": round(
            float(df.memory_usage(deep=True).sum() / (1024 * 1024)),
            3,
        ),
        "numeric_columns": [str(column) for column in numeric_columns],
        "categorical_columns": [str(column) for column in categorical_columns],
        "datetime_columns": [str(column) for column in datetime_columns],
        "boolean_columns": [str(column) for column in boolean_columns],
        "columns": column_details,
    }


def get_descriptive_statistics(df: pd.DataFrame) -> dict:
    """Calculate descriptive statistics for every dataset column."""
    _validate_dataframe(df)

    statistics = {}

    for column in df.columns:
        series = df[column]
        column_stats = {
            "data_type": str(series.dtype),
            "count": int(series.count()),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_bool_dtype(series):
            clean_series = series.dropna()
            column_stats.update({
                "type": "boolean",
                "true_count": int(clean_series.sum()),
                "false_count": int((~clean_series).sum()),
            })

        elif pd.api.types.is_numeric_dtype(series):
            clean_series = series.dropna()

            column_stats.update({
                "type": "numeric",
                "mean": _clean_value(clean_series.mean()),
                "median": _clean_value(clean_series.median()),
                "std": _clean_value(clean_series.std()),
                "variance": _clean_value(clean_series.var()),
                "min": _clean_value(clean_series.min()),
                "max": _clean_value(clean_series.max()),
                "q1": _clean_value(clean_series.quantile(0.25)),
                "q3": _clean_value(clean_series.quantile(0.75)),
                "skewness": _clean_value(clean_series.skew()),
            })

        elif pd.api.types.is_datetime64_any_dtype(series):
            clean_series = series.dropna()

            column_stats.update({
                "type": "datetime",
                "minimum": _clean_value(clean_series.min()),
                "maximum": _clean_value(clean_series.max()),
            })

        else:
            clean_series = series.dropna()
            value_counts = clean_series.astype(str).value_counts()

            column_stats.update({
                "type": "categorical",
                "top_value": (
                    str(value_counts.index[0])
                    if not value_counts.empty else None
                ),
                "top_frequency": (
                    int(value_counts.iloc[0])
                    if not value_counts.empty else 0
                ),
            })

        statistics[str(column)] = column_stats

    return statistics


def get_correlation_matrix(
    df: pd.DataFrame,
    method: str = "pearson",
) -> dict:
    """Calculate correlations between numerical columns."""
    _validate_dataframe(df)

    if method not in {"pearson", "spearman", "kendall"}:
        raise ValueError(
            "Correlation method must be pearson, spearman, or kendall."
        )

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] < 2:
        return {
            "method": method,
            "columns": [str(column) for column in numeric_df.columns],
            "matrix": {},
            "message": "At least two numeric columns are required.",
        }

    correlation = numeric_df.corr(method=method)

    matrix = {}

    for column in correlation.columns:
        matrix[str(column)] = {
            str(index): _clean_value(value)
            for index, value in correlation[column].items()
        }

    return {
        "method": method,
        "columns": [str(column) for column in correlation.columns],
        "matrix": matrix,
    }


def get_group_by_analysis(
    df: pd.DataFrame,
    group_by: str,
    metric: str,
    aggregation: str = "sum",
    limit: int = 20,
) -> dict:
    """Aggregate a metric using a grouping column."""
    _validate_dataframe(df)

    if group_by not in df.columns:
        raise ValueError(f"Grouping column '{group_by}' does not exist.")

    if metric not in df.columns:
        raise ValueError(f"Metric column '{metric}' does not exist.")

    if aggregation not in SUPPORTED_AGGREGATIONS:
        raise ValueError(
            "Unsupported aggregation. Choose from: "
            f"{sorted(SUPPORTED_AGGREGATIONS)}"
        )

    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("Limit must be an integer between 1 and 1000.")

    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[metric]):
        raise ValueError("The selected metric must be numeric.")

    result = (
        df.groupby(group_by, dropna=False)[metric]
        .agg(aggregation)
        .reset_index()
        .sort_values(metric, ascending=False, na_position="last")
        .head(limit)
    )

    records = [
        {
            group_by: _clean_value(row[group_by]),
            metric: _clean_value(row[metric]),
        }
        for _, row in result.iterrows()
    ]

    return {
        "group_by": group_by,
        "metric": metric,
        "aggregation": aggregation,
        "total_groups": int(df[group_by].nunique(dropna=False)),
        "returned_groups": len(records),
        "results": records,
    }


def get_cross_tabulation(
    df: pd.DataFrame,
    row_column: str,
    column_column: str,
    normalize: bool = False,
) -> dict:
    """Create a cross-tabulation between two categorical columns."""
    _validate_dataframe(df)

    if row_column not in df.columns:
        raise ValueError(f"Column '{row_column}' does not exist.")

    if column_column not in df.columns:
        raise ValueError(f"Column '{column_column}' does not exist.")

    if row_column == column_column:
        raise ValueError("Choose two different columns.")

    table = pd.crosstab(
        df[row_column],
        df[column_column],
        normalize="all" if normalize else False,
        dropna=False,
    )

    results = []

    for index, row in table.iterrows():
        results.append({
            "category": _clean_value(index),
            "values": {
                str(column): _clean_value(value)
                for column, value in row.items()
            },
        })

    return {
        "row_column": row_column,
        "column_column": column_column,
        "normalized": normalize,
        "row_categories": len(table.index),
        "column_categories": len(table.columns),
        "columns": [str(column) for column in table.columns],
        "results": results,
    }
