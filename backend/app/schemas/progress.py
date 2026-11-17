from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProgressUpdateRequest(BaseModel):
    is_completed: bool


class ProgressUpdateResponse(BaseModel):
    item_id: int
    is_completed: bool
    completed_at: datetime | None
    section_id: int
    section_status_after_update: str


class ProgressOverview(BaseModel):
    total_items: int
    total_completed: int
    completion_ratio: float