import pandas as pd
import pytest

from app.services.business_intelligence.column_mapper import (
    map_business_columns,
    validate_business_mapping,
)


def sample_retail_data():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A2", "A3"],
        "InvoiceDate": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        "CustomerID": [10, 11, 10],
        "StockCode": ["P1", "P2", "P1"],
        "Description": ["Tea", "Coffee", "Tea"],
        "Quantity": [2, 1, 3],
        "UnitPrice": [5.0, 8.0, 5.0],
        "Country": ["UK", "UK", "FR"],
    })


def test_detects_retail_business_columns():
    result = map_business_columns(sample_retail_data())
    mapping = result["mapping"]

    assert mapping["date"] == "InvoiceDate"
    assert mapping["customer_id"] == "CustomerID"
    assert mapping["order_id"] == "InvoiceNo"
    assert mapping["product_id"] == "StockCode"
    assert mapping["product_name"] == "Description"
    assert mapping["quantity"] == "Quantity"
    assert mapping["unit_price"] == "UnitPrice"
    assert mapping["revenue"]["type"] == "derived"
    assert mapping["revenue"]["depends_on"] == ["Quantity", "UnitPrice"]


def test_returns_candidates_and_available_columns():
    result = map_business_columns(sample_retail_data())

    assert "InvoiceNo" in result["available_columns"]
    assert result["candidates"]["customer_id"][0]["column"] == "CustomerID"


def test_ambiguous_customer_columns_are_not_guessed():
    df = sample_retail_data()
    df["ClientID"] = [10, 11, 12]

    result = map_business_columns(df)

    assert result["mapping"]["customer_id"] is None
    assert any("Multiple possible columns" in warning for warning in result["warnings"])


def test_validates_manual_mapping():
    result = validate_business_mapping(
        sample_retail_data(),
        {"date": "InvoiceDate", "customer_id": "CustomerID", "quantity": "Quantity"},
    )

    assert result["validated"] is True
    assert result["mapping"]["quantity"] == "Quantity"


def test_rejects_unknown_role():
    with pytest.raises(ValueError, match="Unsupported business roles"):
        validate_business_mapping(sample_retail_data(), {"unknown": "InvoiceNo"})


def test_rejects_missing_column():
    with pytest.raises(ValueError, match="Invalid column"):
        validate_business_mapping(sample_retail_data(), {"customer_id": "MissingID"})


def test_rejects_non_numeric_metric_mapping():
    with pytest.raises(ValueError, match="must be numeric"):
        validate_business_mapping(sample_retail_data(), {"quantity": "Description"})


def test_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="empty dataset"):
        map_business_columns(pd.DataFrame())
