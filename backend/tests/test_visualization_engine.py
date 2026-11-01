import pandas as pd
import pytest

from app.services.visualization_engine import build_chart, recommend_charts


@pytest.fixture
def chart_dataframe():
    return pd.DataFrame({
        "date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        "region": ["East", "West", "East"],
        "sales": [100, 150, 200],
        "quantity": [2, 3, 4],
    })


def test_recommend_charts_detects_column_types(chart_dataframe):
    result = recommend_charts(chart_dataframe)

    assert "sales" in result["numeric_columns"]
    assert "region" in result["categorical_columns"]
    assert "date" in result["datetime_columns"]
    assert any(item["chart_type"] == "line" for item in result["recommendations"])
    assert any(item["chart_type"] == "scatter" for item in result["recommendations"])


def test_build_bar_chart(chart_dataframe):
    result = build_chart(
        chart_dataframe,
        chart_type="bar",
        x="region",
        y="sales",
        aggregation="sum",
    )

    assert result["chart_type"] == "bar"
    assert result["data_points"] == 2
    assert result["figure"]["data"]


def test_build_line_chart(chart_dataframe):
    result = build_chart(
        chart_dataframe,
        chart_type="line",
        x="date",
        y="sales",
    )

    assert result["chart_type"] == "line"
    assert result["figure"]["data"]


def test_build_scatter_chart(chart_dataframe):
    result = build_chart(
        chart_dataframe,
        chart_type="scatter",
        x="sales",
        y="quantity",
    )

    assert result["chart_type"] == "scatter"


def test_build_histogram(chart_dataframe):
    result = build_chart(
        chart_dataframe,
        chart_type="histogram",
        x="sales",
    )

    assert result["chart_type"] == "histogram"


def test_build_box_chart(chart_dataframe):
    result = build_chart(
        chart_dataframe,
        chart_type="box",
        x="region",
        y="sales",
    )

    assert result["chart_type"] == "box"


def test_build_pie_chart(chart_dataframe):
    result = build_chart(
        chart_dataframe,
        chart_type="pie",
        x="region",
    )

    assert result["chart_type"] == "pie"


def test_build_heatmap(chart_dataframe):
    result = build_chart(chart_dataframe, chart_type="heatmap")

    assert result["chart_type"] == "heatmap"


def test_invalid_chart_type(chart_dataframe):
    with pytest.raises(ValueError):
        build_chart(chart_dataframe, chart_type="unknown")


def test_invalid_column(chart_dataframe):
    with pytest.raises(ValueError):
        build_chart(
            chart_dataframe,
            chart_type="histogram",
            x="missing_column",
        )
