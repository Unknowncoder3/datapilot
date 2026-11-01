import pandas as pd

from app.services.analytics_engine import (
    SUPPORTED_AGGREGATIONS,
    _clean_value,
    _validate_dataframe,
)


FILTER_OPERATORS = {
    "eq", "ne", "gt", "gte", "lt", "lte", "contains", "in", "is_null", "not_null"
}


def run_safe_analytics_query(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    filters: list[dict] | None = None,
    group_by: list[str] | None = None,
    aggregations: list[dict] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Run a validated, SQL-like analytics query against a dataframe (never raw SQL)."""
    _validate_dataframe(df)

    columns = columns or []
    filters = filters or []
    group_by = group_by or []
    aggregations = aggregations or []

    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("Limit must be an integer between 1 and 1000.")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("Offset must be a non-negative integer.")
    if sort_order not in {"asc", "desc"}:
        raise ValueError("Sort order must be 'asc' or 'desc'.")
    if not all(isinstance(items, list) for items in (columns, filters, group_by, aggregations)):
        raise ValueError("Columns, filters, group_by, and aggregations must be lists.")

    requested_columns = list(dict.fromkeys(columns + group_by))
    for column in requested_columns:
        if not isinstance(column, str) or column not in df.columns:
            raise ValueError(f"Unknown dataset column: {column!r}.")
    if len(group_by) != len(set(group_by)):
        raise ValueError("Group-by columns must not contain duplicates.")

    working = df.copy()
    applied_filters = []
    for condition in filters:
        if not isinstance(condition, dict):
            raise ValueError("Each filter must be an object.")
        unknown_keys = set(condition) - {"column", "operator", "value"}
        if unknown_keys:
            raise ValueError(f"Unsupported filter properties: {sorted(unknown_keys)}.")
        column = condition.get("column")
        operator = condition.get("operator")
        value = condition.get("value")
        if not isinstance(column, str) or column not in working.columns:
            raise ValueError(f"Unknown filter column: {column!r}.")
        if operator not in FILTER_OPERATORS:
            raise ValueError(f"Unsupported filter operator: {operator!r}.")
        series = working[column]
        if operator == "eq":
            mask = series.eq(value)
        elif operator == "ne":
            mask = series.ne(value)
        elif operator in {"gt", "gte", "lt", "lte"}:
            if value is None:
                raise ValueError(f"Filter '{operator}' requires a value.")
            comparable = series
            comparison_value = value
            if pd.api.types.is_numeric_dtype(series):
                comparable = pd.to_numeric(series, errors="coerce")
                try:
                    comparison_value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Filter value for '{column}' must be numeric.") from exc
            elif pd.api.types.is_datetime64_any_dtype(series):
                comparison_value = pd.to_datetime(value, errors="coerce")
                if pd.isna(comparison_value):
                    raise ValueError(f"Filter value for '{column}' must be a valid date.")
            try:
                mask = {
                    "gt": comparable.gt,
                    "gte": comparable.ge,
                    "lt": comparable.lt,
                    "lte": comparable.le,
                }[operator](comparison_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Filter value is incompatible with column '{column}'.") from exc
        elif operator == "contains":
            if not isinstance(value, str):
                raise ValueError("The 'contains' filter requires a string value.")
            mask = series.astype("string").str.contains(value, case=False, regex=False, na=False)
        elif operator == "in":
            if not isinstance(value, list) or not value:
                raise ValueError("The 'in' filter requires a non-empty list.")
            mask = series.isin(value)
        elif operator == "is_null":
            mask = series.isna()
        else:
            mask = series.notna()
        working = working.loc[mask.fillna(False)]
        applied_filters.append({
            "column": column,
            "operator": operator,
            "value": value,
        })

    if aggregations:
        if not group_by and not any(item.get("aggregation") == "count" for item in aggregations if isinstance(item, dict)):
            # A global aggregate is allowed; group_by remains optional.
            pass
        output_names = set(group_by)
        specs = []
        for item in aggregations:
            if not isinstance(item, dict) or set(item) - {"column", "aggregation", "alias"}:
                raise ValueError("Each aggregation must contain only column, aggregation, and optional alias.")
            source = item.get("column")
            operation = item.get("aggregation")
            alias = item.get("alias") or f"{source}_{operation}"
            if not isinstance(source, str) or source not in working.columns:
                raise ValueError(f"Unknown aggregation column: {source!r}.")
            if operation not in SUPPORTED_AGGREGATIONS:
                raise ValueError(f"Unsupported aggregation: {operation!r}.")
            if operation != "count" and not pd.api.types.is_numeric_dtype(working[source]):
                raise ValueError(f"Aggregation '{operation}' requires a numeric column: '{source}'.")
            if not isinstance(alias, str) or not alias or alias in output_names:
                raise ValueError(f"Invalid or duplicate aggregation alias: {alias!r}.")
            if alias in output_names:
                raise ValueError(f"Duplicate output name: {alias!r}.")
            output_names.add(alias)
            specs.append((source, operation, alias))

        if group_by:
            grouped = working.groupby(group_by, dropna=False, sort=False)
            result = grouped.size().rename("__group_size__").reset_index()[group_by]
            for source, operation, alias in specs:
                values = grouped[source].agg(operation).reset_index(drop=True)
                result[alias] = values
        else:
            row = {}
            for source, operation, alias in specs:
                value = working[source].agg(operation)
                row[alias] = value
            result = pd.DataFrame([row])
        available_outputs = list(result.columns)
    else:
        if not columns:
            raise ValueError("Provide columns for a row query or aggregations for an aggregate query.")
        result = working[columns].copy()
        available_outputs = list(result.columns)

    if sort_by is not None:
        if sort_by not in available_outputs:
            raise ValueError(f"Sort column '{sort_by}' is not in the query output.")
        result = result.sort_values(sort_by, ascending=sort_order == "asc", na_position="last")

    total_rows = len(result)
    page = result.iloc[offset:offset + limit]
    records = [
        {str(key): _clean_value(value) for key, value in row.items()}
        for row in page.to_dict(orient="records")
    ]
    return {
        "row_count": total_rows,
        "returned_rows": len(records),
        "limit": limit,
        "offset": offset,
        "columns": [str(column) for column in available_outputs],
        "filters_applied": applied_filters,
        "results": records,
        "execution": "validated_dataframe_query",
        "safety": "Only declared columns, filters, and aggregations are executed; arbitrary SQL is not accepted.",
    }
