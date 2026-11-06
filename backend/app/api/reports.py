from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportRead
from app.services.report_service import build_report_content


router = APIRouter(tags=["reports"])
storage_path = Path(get_settings().upload_dir).resolve()


def _get_dataset_or_404(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


def _get_safe_dataset_path(dataset: Dataset) -> Path:
    path = Path(dataset.file_path).resolve()
    try:
        path.relative_to(storage_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid dataset storage path.") from exc

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Dataset file is missing from storage.")
    return path


@router.post("/datasets/{dataset_id}/reports", response_model=ReportRead, status_code=201)
def create_report(
    dataset_id: int,
    payload: ReportCreate,
    db: Session = Depends(get_db),
):
    dataset = _get_dataset_or_404(dataset_id, db)
    path = _get_safe_dataset_path(dataset)

    try:
        content = build_report_content(path, report_type=payload.report_type)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not generate report from this dataset.") from exc

    report = Report(
        dataset_id=dataset.id,
        title=payload.title.strip(),
        report_type=payload.report_type,
        format="json",
        content=content,
    )
    db.add(report)
    try:
        db.commit()
        db.refresh(report)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save report.") from exc

    return report


@router.get("/datasets/{dataset_id}/reports", response_model=list[ReportRead])
def list_dataset_reports(
    dataset_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _get_dataset_or_404(dataset_id, db)
    return (
        db.query(Report)
        .filter(Report.dataset_id == dataset_id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/reports/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.delete("/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    db.delete(report)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not delete report.") from exc

    return {"message": "Report deleted successfully.", "report_id": report_id}
