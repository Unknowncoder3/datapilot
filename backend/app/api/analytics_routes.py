from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.dataset import Dataset
from app.services.profiler import read_dataset
from app.services.visualization_engine import build_chart, recommend_charts


router = APIRouter(tags=["analytics"])
storage_path = Path(get_settings().upload_dir).resolve()


def _get_dataset_path(dataset_id: int, db: Session) -> Path:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    path = Path(dataset.file_path).resolve()

    try:
        path.relative_to(storage_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset storage path.")

    return path


# In-memory dataset cache.
# Cache entries are invalidated when the file path, size, or modification time changes.
_dataset_cache: dict[int, tuple[str, int, int, object]] = {}
_dataset_cache_lock = Lock()


def _load_dataset(dataset_id: int, db: Session):
    path = _get_dataset_path(dataset_id, db)
    db.close()

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Dataset file is missing from storage.")

    try:
        stat = path.stat()
        cache_key = (str(path), stat.st_mtime_ns, stat.st_size)

        with _dataset_cache_lock:
            cached = _dataset_cache.get(dataset_id)

            if cached is not None and cached[:3] == cache_key:
                # Return a copy so downstream analytics cannot modify the cached frame.
                return cached[3].copy(deep=True)

            df = read_dataset(path)
            _dataset_cache[dataset_id] = (*cache_key, df)

            # Remove stale cache entries for other dataset IDs only if their
            # files have disappeared. This avoids retaining deleted uploads.
            stale_ids = [
                cached_id
                for cached_id, entry in _dataset_cache.items()
                if cached_id != dataset_id and not Path(entry[0]).is_file()
            ]
            for stale_id in stale_ids:
                _dataset_cache.pop(stale_id, None)

            return df.copy(deep=True)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not read dataset.") from exc


@router.get("/{dataset_id}/insights")
def dataset_insights(
    dataset_id: int,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Generate explainable, dataset-grounded insights without an external AI call."""
    import math
    import pandas as pd

    df = _load_dataset(dataset_id, db)
    row_count = int(len(df))
    insights = []

    if row_count == 0 or len(df.columns) == 0:
        return {
            "dataset_id": dataset_id,
            "rows_analyzed": row_count,
            "insight_count": 0,
            "insights": [],
        }

    # Missingness: surface columns with a meaningful amount of absent data.
    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        missing_pct = (missing_count / row_count) * 100
        if missing_pct >= 10:
            severity = "high" if missing_pct >= 40 else "medium"
            insights.append({
                "type": "data_quality",
                "severity": severity,
                "title": f"{str(column)} has missing values",
                "description": f"{missing_count:,} of {row_count:,} rows ({missing_pct:.1f}%) are missing in this column.",
                "metric": {"label": "Missing", "value": round(missing_pct, 2), "format": "percent"},
                "columns": [str(column)],
            })

    duplicate_count = int(df.duplicated().sum())
    duplicate_pct = (duplicate_count / row_count) * 100
    if duplicate_count and duplicate_pct >= 1:
        insights.append({
            "type": "data_quality",
            "severity": "medium" if duplicate_pct < 10 else "high",
            "title": "Duplicate rows detected",
            "description": f"{duplicate_count:,} rows ({duplicate_pct:.1f}%) are exact duplicates across all columns.",
            "metric": {"label": "Duplicate rows", "value": duplicate_count, "format": "number"},
            "columns": [str(column) for column in df.columns],
        })

    # Numeric columns: IQR-based outliers and broad distribution highlights.
    numeric_columns = list(df.select_dtypes(include="number").columns)[:30]
    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(values) < 8 or values.nunique() < 4:
            continue
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        if not math.isfinite(iqr) or iqr <= 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((values < lower) | (values > upper)).sum())
        outlier_pct = (outlier_count / len(values)) * 100
        if outlier_count and outlier_pct >= 1:
            insights.append({
                "type": "distribution",
                "severity": "medium" if outlier_pct < 5 else "high",
                "title": f"Potential outliers in {str(column)}",
                "description": f"{outlier_count:,} values ({outlier_pct:.1f}% of non-missing values) fall outside the 1.5×IQR range ({lower:,.3g} to {upper:,.3g}). Review these values; they may be valid extremes.",
                "metric": {"label": "Potential outliers", "value": outlier_count, "format": "number"},
                "columns": [str(column)],
            })

    # Low-cardinality categorical columns: reveal dominant category concentration.
    for column in list(df.select_dtypes(include=["object", "category", "string"]).columns)[:30]:
        values = df[column].dropna()
        unique_count = int(values.nunique())
        if len(values) < 10 or unique_count < 2 or unique_count > 50:
            continue
        counts = values.astype(str).value_counts()
        leader = str(counts.index[0])
        share = (int(counts.iloc[0]) / len(values)) * 100
        if share >= 80:
            insights.append({
                "type": "concentration",
                "severity": "low",
                "title": f"{str(column)} is highly concentrated",
                "description": f"{leader} represents {share:.1f}% of non-missing values in this column.",
                "metric": {"label": "Leading category share", "value": round(share, 2), "format": "percent"},
                "columns": [str(column)],
                "category": leader,
            })

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda item: (severity_rank.get(item["severity"], 3), item["type"], item["title"]))
    selected = insights[:limit]
    return {
        "dataset_id": dataset_id,
        "rows_analyzed": row_count,
        "insight_count": len(insights),
        "insights": selected,
    }


@router.get("/{dataset_id}/charts/recommendations")
def chart_recommendations(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)

    try:
        return {
            "dataset_id": dataset_id,
            **recommend_charts(df),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/charts")
def create_dataset_chart(
    dataset_id: int,
    chart_type: str = Query(...),
    x: str | None = Query(None),
    y: str | None = Query(None),
    color: str | None = Query(None),
    aggregation: str = Query("sum"),
    max_points: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)

    try:
        return {
            "dataset_id": dataset_id,
            **build_chart(
                df=df,
                chart_type=chart_type,
                x=x,
                y=y,
                color=color,
                aggregation=aggregation,
                max_points=max_points,
            ),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
