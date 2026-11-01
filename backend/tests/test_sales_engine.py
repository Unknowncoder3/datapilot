import pandas as pd
import pytest

from app.services.business_intelligence.sales_engine import (
    get_sales_by_country,
    get_sales_trends,
    get_top_products,
)


def sample_sales():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A1", "A2", "C3", "A4"],
        "InvoiceDate": pd.to_datetime([
            "2025-01-02", "2025-01-02", "2025-02-02",
            "2025-02-10", "2025-03-01",
        ]),
        "StockCode": ["P1", "P2", "P1", "P2", "P3"],
        "Description": ["Tea", "Coffee", "Tea", "Coffee", "Cake"],
        "Quantity": [2, 1, 3, -1, 4],
        "UnitPrice": [5.0, 8.0, 5.0, 8.0, 2.0],
        "Country": ["UK", "UK", "FR", "UK", "FR"],
    })


def test_monthly_sales_trends_and_growth():
    result = get_sales_trends(sample_sales())
    assert result["frequency"] == "month"
    assert [item["period"] for item in result["results"]] == [
        "2025-01", "2025-02", "2025-03"
    ]
    assert result["results"][0]["revenue"] == 18.0
    assert result["results"][1]["revenue"] == 7.0
    assert result["results"][2]["growth_percent"] == pytest.approx(14.29, abs=0.01)


def test_cancelled_invoice_rows_are_identified_but_included():
    result = get_sales_trends(sample_sales())
    february = result["results"][1]
    assert february["cancelled_rows"] == 1
    assert february["revenue"] == 7.0


def test_daily_frequency():
    result = get_sales_trends(sample_sales(), frequency="day")
    assert result["periods"] == 4


def test_rejects_unsupported_frequency():
    with pytest.raises(ValueError, match="Frequency"):
        get_sales_trends(sample_sales(), frequency="year")


def test_sales_by_country():
    result = get_sales_by_country(sample_sales())
    assert result["results"][0]["country"] == "FR"
    assert result["results"][0]["revenue"] == 23.0


def test_top_products():
    result = get_top_products(sample_sales(), limit=2)
    assert len(result["results"]) == 2
    assert result["results"][0]["product_id"] == "P1"
    assert result["results"][0]["revenue"] == 25.0


def test_rejects_missing_country_mapping():
    df = sample_sales().drop(columns=["Country"])
    with pytest.raises(ValueError, match="Country performance"):
        get_sales_by_country(df)


def test_rejects_invalid_limit():
    with pytest.raises(ValueError, match="Limit"):
        get_top_products(sample_sales(), limit=0)
