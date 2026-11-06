import pandas as pd
import pytest
from pydantic import ValidationError

from app.schemas.report import ReportCreate
from app.services.report_service import build_report_content


def test_build_summary_report(tmp_path):
    dataset_path = tmp_path / "sample.csv"
    pd.DataFrame({
        "region": ["East", "West", "East", "North"],
        "revenue": [100, 200, 150, 80],
        "quantity": [1, 2, 3, 1],
    }).to_csv(dataset_path, index=False)

    report = build_report_content(dataset_path, "summary")

    assert report["report_type"] == "summary"
    assert report["overview"]["row_count"] == 4
    assert report["overview"]["column_count"] == 3
    assert report["data_quality"]["quality_score"] <= 100
    assert "revenue" in report["descriptive_statistics"]
    assert "sample_rows" not in report


def test_build_full_report_includes_correlation_and_preview(tmp_path):
    dataset_path = tmp_path / "sample.csv"
    pd.DataFrame({
        "revenue": [10, 20, 30],
        "quantity": [1, 2, 3],
    }).to_csv(dataset_path, index=False)

    report = build_report_content(dataset_path, "full")

    assert "correlation" in report
    assert report["sample_row_count"] == 3
    assert len(report["sample_rows"]) == 3
    assert report["correlation"]["columns"] == ["revenue", "quantity"]


def test_report_rejects_unknown_type(tmp_path):
    dataset_path = tmp_path / "sample.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="Report type"):
        build_report_content(dataset_path, "pdf")


def test_report_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_report_content(tmp_path / "missing.csv")


def test_report_title_is_trimmed():
    request = ReportCreate(title="  Monthly Sales  ")
    assert request.title == "Monthly Sales"


def test_report_title_rejects_whitespace():
    with pytest.raises(ValidationError):
        ReportCreate(title="   ")
