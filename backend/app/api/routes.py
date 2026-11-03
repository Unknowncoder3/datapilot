import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.dataset import Dataset
from app.services.profiler import profile_dataframe, read_dataset


router = APIRouter(tags=["datasets"])

settings = get_settings()
storage_path = Path(settings.upload_dir).resolve()
storage_path.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CHUNK_SIZE = 1024 * 1024


def get_dataset_or_404(dataset_id: int, db: Session):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    return dataset


def get_safe_file_path(dataset: Dataset) -> Path:
    """Ensure a stored dataset path remains inside the upload directory."""
    path = Path(dataset.file_path).resolve()

    try:
        path.relative_to(storage_path)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset storage path."
        )

    return path


def serialize_dataset(dataset: Dataset):
    return {
        "id": dataset.id,
        "name": dataset.name,
        "original_filename": dataset.original_filename,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "missing_cells": dataset.missing_cells,
        "duplicate_rows": dataset.duplicate_rows,
        "created_at": dataset.created_at,
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "datapilot-api",
        "phase": 1,
    }


@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required."
        )

    original_filename = Path(file.filename).name
    suffix = Path(original_filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only CSV, XLSX, and XLS files are supported."
        )

    max_size = settings.max_upload_size_mb * 1024 * 1024
    path = storage_path / f"{uuid4().hex}{suffix}"
    total_size = 0

    try:
        with path.open("wb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail="File is too large."
                    )

                output.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        profile = profile_dataframe(read_dataset(path))

        dataset = Dataset(
            name=Path(original_filename).stem,
            original_filename=original_filename,
            file_path=str(path),
            file_type=suffix.lstrip("."),
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            missing_cells=profile["missing_cells"],
            duplicate_rows=profile["duplicate_rows"],
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return {
            **serialize_dataset(dataset),
            **profile,
        }

    except HTTPException:
        db.rollback()
        path.unlink(missing_ok=True)
        raise

    except Exception as exc:
        db.rollback()
        path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=422,
            detail="Could not process the uploaded dataset. "
                   "Check that the file is valid."
        ) from exc

    finally:
        await file.close()


@router.get("/datasets")
def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(Dataset.id)).scalar() or 0

    datasets = (
        db.query(Dataset)
        .order_by(Dataset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [serialize_dataset(item) for item in datasets],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = get_dataset_or_404(dataset_id, db)
    return serialize_dataset(dataset)


@router.get("/datasets/{dataset_id}/profile")
def get_dataset_profile(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = get_dataset_or_404(dataset_id, db)
    path = get_safe_file_path(dataset)

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Dataset file is missing from storage."
        )

    try:
        df = read_dataset(path)
        profile = profile_dataframe(df)

        return {
            "dataset": serialize_dataset(dataset),
            "profile": profile,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not generate dataset profile."
        ) from exc


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: int,
    rows: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    dataset = get_dataset_or_404(dataset_id, db)
    path = get_safe_file_path(dataset)

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Dataset file is missing from storage."
        )

    try:
        df = read_dataset(path)
        preview_df = df.head(rows)

        # Convert timestamps and missing values into JSON-safe values.
        records = json.loads(
            preview_df.to_json(
                orient="records",
                date_format="iso"
            )
        )

        return {
            "dataset_id": dataset.id,
            "columns": [str(column) for column in df.columns],
            "rows": records,
            "returned_rows": len(records),
            "total_rows": len(df),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not preview dataset."
        ) from exc


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = get_dataset_or_404(dataset_id, db)
    path = get_safe_file_path(dataset)

    try:
        db.delete(dataset)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not delete dataset."
        ) from exc

    # Remove the physical file after the database transaction succeeds.
    path.unlink(missing_ok=True)

    return {
        "message": "Dataset deleted successfully.",
        "dataset_id": dataset_id,
    }
