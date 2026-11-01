import pandas as pd
import pytest

from app.services.business_intelligence.query_engine import run_safe_analytics_query


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "Country": ["India", "USA", "India", "UK", "USA"],
        "Product": ["A", "B", "A", "C", "B"],
        "Sales": [100, 200, 150, 300, 250],
        "Quantity": [2, 4, 3, 6, 5],
        "Active": [True, False, True, True, False],
    })


def test_grouped_aggregate_query(sample_df):
    result = run_safe_analytics_query(
        sample_df,
        group_by=["Country"],
        aggregations=[
            {"column": "Sales", "aggregation": "sum", "alias": "revenue"},
            {"column": "Quantity", "aggregation": "mean", "alias": "average_units"},
        ],
        sort_by="revenue",
    )
    assert result["row_count"] == 3
    assert result["results"][0]["Country"] == "USA"
    assert result["results"][0]["revenue"] == 450
    assert result["columns"] == ["Country", "revenue", "average_units"]


def test_filter_and_paginate_rows(sample_df):
    result = run_safe_analytics_query(
        sample_df,
        columns=["Product", "Sales"],
        filters=[{"column": "Country", "operator": "eq", "value": "India"}],
        sort_by="Sales",
        sort_order="desc",
        limit=1,
        offset=1,
    )
    assert result["row_count"] == 2
    assert result["returned_rows"] == 1
    assert result["results"][0] == {"Product": "A", "Sales": 100}


def test_contains_and_in_filters(sample_df):
    result = run_safe_analytics_query(
        sample_df,
        columns=["Country", "Sales"],
        filters=[
            {"column": "Country", "operator": "contains", "value": "u"},
            {"column": "Product", "operator": "in", "value": ["B", "C"]},
        ],
    )
    assert result["row_count"] == 3


def test_global_aggregate_query(sample_df):
    result = run_safe_analytics_query(
        sample_df,
        aggregations=[{"column": "Sales", "aggregation": "sum", "alias": "total_sales"}],
    )
    assert result["results"] == [{"total_sales": 1000}]


def test_null_filter(sample_df):
    df = sample_df.copy()
    df.loc[0, "Product"] = None
    result = run_safe_analytics_query(
        df,
        columns=["Product"],
        filters=[{"column": "Product", "operator": "is_null"}],
    )
    assert result["row_count"] == 1


@pytest.mark.parametrize("kwargs, message", [
    ({"columns": ["Missing"]}, "Unknown dataset column"),
    ({"columns": ["Sales"], "filters": [{"column": "Sales", "operator": "exec", "value": "x"}]}, "Unsupported filter operator"),
    ({"columns": ["Sales"], "sort_by": "Unknown"}, "Sort column"),
    ({"columns": ["Sales"], "limit": 0}, "Limit"),
    ({"columns": ["Sales"], "offset": -1}, "Offset"),
    ({"columns": ["Sales"], "sort_order": "sideways"}, "Sort order"),
    ({"columns": ["Country"], "aggregations": [{"column": "Country", "aggregation": "sum"}]}, "requires a numeric column"),
])
def test_rejects_invalid_query(sample_df, kwargs, message):
    with pytest.raises(ValueError, match=message):
        run_safe_analytics_query(sample_df, **kwargs)


def test_requires_columns_or_aggregations(sample_df):
    with pytest.raises(ValueError, match="Provide columns"):
        run_safe_analytics_query(sample_df)
