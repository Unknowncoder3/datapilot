import pandas as pd
import pytest

from app.services.business_intelligence.kpi_engine import calculate_business_kpis


def retail_data():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A1", "A2", "A3"],
        "CustomerID": [10, 10, 11, None],
        "StockCode": ["P1", "P2", "P1", "P3"],
        "Quantity": [2, 1, 3, 2],
        "UnitPrice": [5.0, 8.0, 5.0, 4.0],
    })


def test_calculates_retail_kpis_from_derived_revenue():
    result = calculate_business_kpis(retail_data())
    metrics = result["metrics"]

    assert metrics["total_revenue"]["value"] == 41.0
    assert metrics["total_orders"]["value"] == 3
    assert metrics["average_order_value"]["value"] == 13.67
    assert metrics["total_units_sold"]["value"] == 8.0
    assert metrics["unique_customers"]["value"] == 2
    assert metrics["unique_products"]["value"] == 3
    assert metrics["total_profit"]["available"] is False


def test_order_count_is_distinct_not_row_count():
    result = calculate_business_kpis(retail_data())
    assert result["metrics"]["total_orders"]["value"] == 3
    assert result["row_count"] == 4


def test_handles_missing_order_and_customer_fields():
    df = pd.DataFrame({"Quantity": [2, 3], "UnitPrice": [4.0, 5.0]})
    result = calculate_business_kpis(df)

    assert result["metrics"]["total_revenue"]["value"] == 23.0
    assert result["metrics"]["total_orders"]["available"] is False
    assert result["metrics"]["average_order_value"]["available"] is False
    assert result["metrics"]["unique_customers"]["available"] is False


def test_uses_explicit_revenue_and_profit_columns():
    df = pd.DataFrame({
        "OrderID": ["A", "B"],
        "Revenue": [100.0, 150.0],
        "Profit": [20.0, 30.0],
    })
    result = calculate_business_kpis(df)

    assert result["metrics"]["total_revenue"]["value"] == 250.0
    assert result["metrics"]["total_profit"]["value"] == 50.0


def test_numeric_strings_are_coerced_safely():
    df = pd.DataFrame({
        "OrderID": ["A", "B"],
        "Quantity": ["2", "invalid"],
        "UnitPrice": ["5.5", "3.0"],
    })
    result = calculate_business_kpis(df)

    assert result["metrics"]["total_revenue"]["value"] == 11.0
    assert result["metrics"]["total_units_sold"]["value"] == 2.0


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        calculate_business_kpis(pd.DataFrame())
