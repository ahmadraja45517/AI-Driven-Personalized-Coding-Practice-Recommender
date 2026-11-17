from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningItem, SectionItem, SectionUnlock, StudentProgress
from app.models.enums import UnlockStatus
from app.schemas.progress import ProgressUpdateResponse
from app.services.unlock_service import evaluate_section_by_id


class ProgressError(Exception):
    pass


def set_item_completion(
    db: Session, user_id: int, item_id: int, is_completed: bool,
) -> ProgressUpdateResponse:
    item = db.get(LearningItem, item_id)
    if item is None or not item.is_active:
        raise ProgressError("Item not found")

    membership = db.execute(
        select(SectionItem).where(SectionItem.item_id == item_id)
    ).scalar_one_or_none()
    if membership is None:
        raise ProgressError("Item is not part of any section")

    section_id = membership.section_id
    unlock = db.execute(
        select(SectionUnlock).where(
            SectionUnlock.user_id == user_id, SectionUnlock.section_id == section_id,
        )
    ).scalar_one_or_none()
    if unlock is None or unlock.status == UnlockStatus.LOCKED:
        raise ProgressError("You cannot modify progress for a locked section")

    progress = db.execute(
        select(StudentProgress).where(
            StudentProgress.user_id == user_id, StudentProgress.item_id == item_id,
        )
    ).scalar_one_or_none()
    if progress is None:
        progress = StudentProgress(user_id=user_id, item_id=item_id)
        db.add(progress)

    if is_completed:
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.now(timezone.utc)
    else:
        progress.is_completed = False
        progress.completed_at = None
    progress.self_reported = True
    db.flush()

    evaluate_section_by_id(db, user_id, section_id)

    unlock_after = db.execute(
        select(SectionUnlock).where(
            SectionUnlock.user_id == user_id, SectionUnlock.section_id == section_id,
        )
    ).scalar_one()
    db.commit()
    db.refresh(progress)
    return ProgressUpdateResponse(
        item_id=item_id,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
        section_id=section_id,
        section_status_after_update=unlock_after.status.value,
    )