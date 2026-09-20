from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.database import get_db
from app.models.dataset import Dataset
from app.services.profiler import profile_dataframe, read_dataset

router=APIRouter(tags=["datasets"])
settings=get_settings()
storage_path=Path(settings.upload_dir)
storage_path.mkdir(parents=True, exist_ok=True)
allowed={".csv",".xlsx",".xls"}

@router.get("/health")
def health():
    return {"status":"ok","service":"datapilot-api","phase":1}

@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile=File(...), db: Session=Depends(get_db)):
    if not file.filename: raise HTTPException(400,"A filename is required.")
    suffix=Path(file.filename).suffix.lower()
    if suffix not in allowed: raise HTTPException(400,"Only CSV, XLSX, and XLS files are supported.")
    content=await file.read()
    if len(content) > settings.max_upload_size_mb*1024*1024: raise HTTPException(413,"File is too large.")
    path=storage_path/f"{uuid4().hex}{suffix}"
    path.write_bytes(content)
    try: profile=profile_dataframe(read_dataset(path))
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422,f"Could not profile dataset: {exc}") from exc
    dataset=Dataset(name=Path(file.filename).stem,original_filename=file.filename,file_path=str(path),file_type=suffix.lstrip('.'),row_count=profile['row_count'],column_count=profile['column_count'],missing_cells=profile['missing_cells'],duplicate_rows=profile['duplicate_rows'])
    db.add(dataset); db.commit(); db.refresh(dataset)
    return {"id":dataset.id,"name":dataset.name,"original_filename":dataset.original_filename,"file_type":dataset.file_type,**profile,"created_at":dataset.created_at}
