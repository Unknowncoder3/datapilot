import pandas as pd
import pytest

from app.services.business_intelligence.customer_product_engine import (
    get_customer_intelligence,
    get_customer_rfm,
    get_product_intelligence,
)


def sample_sales():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A1", "A2", "C3", "A4"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-01-02", "2025-02-02",
            "2025-02-10", "2025-03-01",
        ]),
        "CustomerID": [101, 101, 102, 101, 103],
        "StockCode": ["P1", "P2", "P1", "P2", "P3"],
        "Description": ["Tea", "Coffee", "Tea", "Coffee", "Cake"],
        "Quantity": [2, 1, 3, -1, 4],
        "UnitPrice": [5.0, 8.0, 5.0, 8.0, 2.0],
        "Country": ["UK", "UK", "FR", "UK", "FR"],
    })


def test_customer_intelligence_aggregates_orders_and_revenue():
    result = get_customer_intelligence(sample_sales())
    assert result["unique_customers"] == 3
    assert result["results"][0]["customer_id"] == "102"
    assert result["results"][0]["revenue"] == 15.0
    customer_101 = next(item for item in result["results"] if item["customer_id"] == "101")
    assert customer_101["revenue"] == 10.0
    assert customer_101["order_count"] == 2
    assert customer_101["transaction_rows"] == 3


def test_customer_intelligence_rejects_missing_customer_id():
    with pytest.raises(ValueError, match="customer identifier"):
        get_customer_intelligence(sample_sales().drop(columns=["CustomerID"]))


def test_customer_intelligence_rejects_invalid_limit():
    with pytest.raises(ValueError, match="Limit"):
        get_customer_intelligence(sample_sales(), limit=0)


def test_rfm_calculates_dataset_relative_scores():
    result = get_customer_rfm(sample_sales())
    assert result["reference_date"] == "2025-03-01"
    assert result["customer_count"] == 3
    assert all(1 <= item["r_score"] <= 5 for item in result["results"])
    assert all(1 <= item["f_score"] <= 5 for item in result["results"])
    assert all(1 <= item["m_score"] <= 5 for item in result["results"])
    assert result["results"][0]["customer_id"] == "103"


def test_rfm_requires_date_and_order_fields():
    df = sample_sales().drop(columns=["InvoiceDate"])
    with pytest.raises(ValueError, match="date"):
        get_customer_rfm(df)


def test_product_intelligence_ranks_by_revenue():
    result = get_product_intelligence(sample_sales(), limit=2)
    assert result["unique_products"] == 3
    assert result["results"][0]["product_id"] == "P1"
    assert result["results"][0]["revenue"] == 25.0
    assert result["results"][0]["quantity"] == 5.0


def test_product_intelligence_rejects_missing_product_id():
    with pytest.raises(ValueError, match="product identifier"):
        get_product_intelligence(sample_sales().drop(columns=["StockCode"]))


def test_product_intelligence_rejects_invalid_limit():
    with pytest.raises(ValueError, match="Limit"):
        get_product_intelligence(sample_sales(), limit=101)
