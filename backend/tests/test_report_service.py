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


def test_build_executive_report_includes_management_analysis(tmp_path):
    dataset_path = tmp_path / "sales.csv"
    pd.DataFrame({
        "InvoiceDate": ["2025-01-15", "2025-01-20", "2025-02-15", "2025-02-20"],
        "Country": ["East", "West", "East", "East"],
        "Quantity": [2, 3, 4, 2],
        "UnitPrice": [10, 20, 10, 15],
    }).to_csv(dataset_path, index=False)

    report = build_report_content(dataset_path, "executive")
    analysis = report["executive_analysis"]

    assert report["report_type"] == "executive"
    assert analysis["metric_formula"] == "Quantity multiplied by UnitPrice"
    assert analysis["trend"]["date_field"] == "InvoiceDate"
    assert len(analysis["trend"]["series"]) == 2
    assert analysis["trend"]["period_change"]["direction"] == "down"
    assert analysis["trend"]["period_change"]["absolute_change"] == -10.0
    assert "-12.50%" in analysis["key_findings"][0]["detail"]
    assert "-10.00" in analysis["key_findings"][0]["detail"]
    assert analysis["key_findings"]
    assert analysis["management_recommendations"]



def test_executive_report_flags_partial_month_and_calculates_like_for_like(tmp_path):
    dataset_path = tmp_path / "partial_month.csv"
    pd.DataFrame({
        "InvoiceDate": ["2025-11-01", "2025-11-09", "2025-11-20", "2025-12-01", "2025-12-09"],
        "Revenue": [100, 200, 300, 150, 250],
        "Country": ["East", "West", "East", "East", "West"],
    }).to_csv(dataset_path, index=False)

    analysis = build_report_content(dataset_path, "executive")["executive_analysis"]
    change = analysis["trend"]["period_change"]
    comparable = change["like_for_like"]

    assert change["direction"] == "down"
    assert comparable["partial_period"] is True
    assert comparable["cutoff_day"] == 9
    assert comparable["previous_value"] == 300.0
    assert comparable["current_value"] == 400.0
    assert comparable["direction"] == "up"
    assert comparable["percentage_change"] == pytest.approx(33.333333)
    assert "observed only through day 9" in comparable["warning"]
    assert any("partial" in note.lower() for note in analysis["analysis_notes"])


def test_executive_breakdowns_include_contribution_percentages(tmp_path):
    dataset_path = tmp_path / "segments.csv"
    pd.DataFrame({
        "Revenue": [75, 25, 50],
        "Country": ["East", "West", "East"],
    }).to_csv(dataset_path, index=False)

    analysis = build_report_content(dataset_path, "executive")["executive_analysis"]
    country = next(item for item in analysis["performance_breakdowns"] if item["dimension"] == "Country")
    leaders = {item["name"]: item["contribution_pct"] for item in country["leaders"]}

    assert leaders["East"] == pytest.approx(125 / 150 * 100)
    assert leaders["West"] == pytest.approx(25 / 150 * 100)

def test_report_create_defaults_to_executive_type():
    request = ReportCreate(title="Monthly Business Review")
    assert request.report_type == "executive"
