from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.services.analytics_engine import (
    _clean_value,
    get_analytics_overview,
    get_descriptive_statistics,
    get_correlation_matrix,
)
from app.services.profiler import profile_dataframe, read_dataset


def build_report_content(dataset_path: Path, report_type: str = "summary") -> dict:
    """Build a JSON-safe, dataset-grounded report from an uploaded file."""
    if report_type not in {"summary", "full"}:
        raise ValueError("Report type must be 'summary' or 'full'.")

    path = Path(dataset_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Dataset file is missing from storage.")

    df = read_dataset(path)
    if df.empty or len(df.columns) == 0:
        raise ValueError("Cannot generate a report from an empty dataset.")

    profile = profile_dataframe(df)
    content = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_type": report_type,
        "overview": get_analytics_overview(df),
        "data_quality": {
            "quality_score": profile["quality_score"],
            "row_count": profile["row_count"],
            "column_count": profile["column_count"],
            "missing_cells": profile["missing_cells"],
            "duplicate_rows": profile["duplicate_rows"],
            "columns": profile["columns"],
        },
        "descriptive_statistics": get_descriptive_statistics(df),
    }

    if report_type == "full":
        content["correlation"] = get_correlation_matrix(df)
        sample = df.head(20)
        content["sample_rows"] = [
            {str(column): _clean_value(value) for column, value in row.items()}
            for row in sample.to_dict(orient="records")
        ]
        content["sample_row_count"] = len(sample)

    return content
