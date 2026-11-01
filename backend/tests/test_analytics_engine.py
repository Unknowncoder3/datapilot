import pandas as pd
import pytest

from app.services.analytics_engine import (
    get_analytics_overview,
    get_descriptive_statistics,
    get_correlation_matrix,
    get_group_by_analysis,
    get_cross_tabulation,
)


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        "Product": ["A", "B", "A", "C", "B"],
        "Country": ["India", "USA", "India", "UK", "USA"],
        "Sales": [100, 200, 150, 300, 250],
        "Quantity": [2, 4, 3, 6, 5],
    })


def test_analytics_overview(sample_dataframe):
    result = get_analytics_overview(sample_dataframe)

    assert result["row_count"] == 5
    assert result["column_count"] == 4
    assert result["numeric_column_count"] == 2
    assert result["categorical_column_count"] == 2
    assert result["missing_cells"] == 0


def test_descriptive_statistics(sample_dataframe):
    result = get_descriptive_statistics(sample_dataframe)

    assert result["Sales"]["mean"] == 200
    assert result["Sales"]["median"] == 200
    assert result["Sales"]["min"] == 100
    assert result["Sales"]["max"] == 300


def test_correlation_matrix(sample_dataframe):
    result = get_correlation_matrix(sample_dataframe)

    assert result["method"] == "pearson"
    assert "Sales" in result["matrix"]
    assert "Quantity" in result["matrix"]
    assert result["matrix"]["Sales"]["Quantity"] == 1.0


def test_group_by_analysis(sample_dataframe):
    result = get_group_by_analysis(
        sample_dataframe,
        group_by="Country",
        metric="Sales",
        aggregation="sum",
    )

    assert result["total_groups"] == 3
    assert result["results"][0]["Country"] == "USA"
    assert result["results"][0]["Sales"] == 450


def test_cross_tabulation(sample_dataframe):
    result = get_cross_tabulation(
        sample_dataframe,
        row_column="Country",
        column_column="Product",
    )

    assert result["row_categories"] == 3
    assert result["column_categories"] == 3


def test_invalid_group_column(sample_dataframe):
    with pytest.raises(ValueError):
        get_group_by_analysis(
            sample_dataframe,
            group_by="Invalid",
            metric="Sales",
        )


def test_invalid_correlation_method(sample_dataframe):
    with pytest.raises(ValueError):
        get_correlation_matrix(
            sample_dataframe,
            method="invalid",
        )


def test_empty_dataframe():
    with pytest.raises(ValueError):
        get_analytics_overview(pd.DataFrame())
