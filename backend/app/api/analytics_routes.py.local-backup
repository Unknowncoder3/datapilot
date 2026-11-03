from pathlib import Path

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


def _load_dataset(dataset_id: int, db: Session):
    path = _get_dataset_path(dataset_id, db)
    db.close()

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Dataset file is missing from storage.")

    try:
        return read_dataset(path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not read dataset.") from exc


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
