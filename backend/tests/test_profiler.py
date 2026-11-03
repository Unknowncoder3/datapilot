import pandas as pd

from app.services.profiler import profile_dataframe
from pathlib import Path
from app.services.profiler import read_dataset


def test_csv_date_detection(tmp_path):
    csv_file = tmp_path / "sales.csv"

    csv_file.write_text(
        "order_id,order_date,revenue\n"
        "1001,2026-01-01,10000\n"
        "1002,2026-01-02,20000\n"
        "1003,2026-01-03,30000\n"
    )

    df = read_dataset(csv_file)

    profile = profile_dataframe(df)

    date_column = next(
        col for col in profile["columns"]
        if col["name"] == "order_date"
    )

    assert date_column["semantic_type"] == "datetime"
    assert date_column["statistics"]["earliest"].startswith("2026-01-01")

def test_profile_dataframe():
    df = pd.DataFrame({
        "name": ["A", "B", "B", "B"],
        "revenue": [10, None, 20, 20]
    })

    profile = profile_dataframe(df)

    assert profile["row_count"] == 4
    assert profile["column_count"] == 2
    assert profile["missing_cells"] == 1
    assert profile["duplicate_rows"] == 1

    assert profile["columns"][1]["semantic_type"] == "numeric"
    assert profile["columns"][1]["missing_percentage"] == 25.0


def test_numeric_statistics():
    df = pd.DataFrame({
        "sales": [10, 20, 30, 40, 50]
    })

    profile = profile_dataframe(df)
    stats = profile["columns"][0]["statistics"]

    assert stats["mean"] == 30
    assert stats["median"] == 30
    assert stats["min"] == 10
    assert stats["max"] == 50
    assert stats["q1"] == 20
    assert stats["q3"] == 40


def test_outlier_detection():
    df = pd.DataFrame({
        "sales": [10, 11, 12, 13, 14, 1000]
    })

    profile = profile_dataframe(df)
    stats = profile["columns"][0]["statistics"]

    assert stats["outlier_count"] == 1


def test_categorical_statistics():
    df = pd.DataFrame({
        "city": ["Kolkata", "Delhi", "Kolkata", "Mumbai", "Kolkata"]
    })

    profile = profile_dataframe(df)
    stats = profile["columns"][0]["statistics"]

    assert stats["top_values"][0]["value"] == "Kolkata"
    assert stats["top_values"][0]["count"] == 3
    assert stats["top_values"][0]["percentage"] == 60.0


def test_datetime_statistics():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01",
            "2026-02-01",
            "2026-03-01"
        ])
    })

    profile = profile_dataframe(df)
    column = profile["columns"][0]

    assert column["semantic_type"] == "datetime"
    assert column["statistics"]["earliest"].startswith("2026-01-01")
    assert column["statistics"]["latest"].startswith("2026-03-01")


def test_empty_dataframe():
    df = pd.DataFrame({
        "sales": pd.Series(dtype="float64")
    })

    profile = profile_dataframe(df)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 1
    assert profile["quality_score"] == 100
    assert profile["columns"][0]["statistics"]["mean"] is None
