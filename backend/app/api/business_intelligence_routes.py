from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.business_intelligence.column_mapper import (
    map_business_columns,
    validate_business_mapping,
)
from app.api.analytics_routes import _load_dataset


router = APIRouter(tags=["business-intelligence"])


@router.get("/{dataset_id}/bi/mapping")
def get_business_mapping(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **map_business_columns(df),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{dataset_id}/bi/mapping")
def validate_mapping_override(
    dataset_id: int,
    mapping: dict = Body(..., description="Business role to dataset column mapping"),
    db: Session = Depends(get_db),
):
    df = _load_dataset(dataset_id, db)
    try:
        return {
            "dataset_id": dataset_id,
            **validate_business_mapping(df, mapping),
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
