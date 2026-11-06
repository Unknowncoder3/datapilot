from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    report_type: Literal["summary", "full"] = "summary"


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    title: str
    report_type: str
    format: str
    content: dict | None
    created_at: datetime
