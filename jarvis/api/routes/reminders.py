"""Reminders/scheduler management endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("")
async def list_reminders():
    from jarvis.api.main import app_state

    scheduler = app_state.get("scheduler")
    if scheduler is None:
        return {"jobs": []}
    return {"jobs": scheduler.list_jobs()}


@router.delete("/{job_id}")
async def cancel_reminder(job_id: str):
    from jarvis.api.main import app_state

    scheduler = app_state.get("scheduler")
    if scheduler is None:
        return {"cancelled": False, "reason": "Scheduler not running"}
    ok = scheduler.cancel(job_id)
    return {"cancelled": ok}
