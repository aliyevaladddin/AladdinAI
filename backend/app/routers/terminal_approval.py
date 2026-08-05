# NOTICE: This file is protected under RCF-PL
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.user import User
from app.security import get_current_user
from app.tools.terminal_tools import find_pending, latest_pending

router = APIRouter(prefix="/terminal/approval", tags=["Terminal"])
log = logging.getLogger(__name__)


class ApprovalResponse(BaseModel):
    request_id: str
    status: str
    command: Optional[str] = None


# [RCF:PROTECTED]
def _settle(request_id: str, item: dict[str, Any], *, approved: bool) -> ApprovalResponse:
    """Hand the decision to the tool call that is already awaiting it.

    This endpoint only ever resolves a future raised by `execute_terminal_command`
    — it never runs a command itself. Execution stays behind the tool, so the
    approval gate cannot be used as a way around the approval gate.
    """
    future = item.get("future")
    if future is None or future.done():
        return ApprovalResponse(request_id=request_id, status="already_processed")

    future.set_result(approved)
    log.info(
        "Terminal execution request %s [%s]",
        "APPROVED" if approved else "REJECTED",
        request_id,
    )
    return ApprovalResponse(
        request_id=request_id,
        status="approved" if approved else "rejected",
        command=item.get("command"),
    )


@router.post("/approve_latest", response_model=ApprovalResponse)
async def approve_latest_request(user: User = Depends(get_current_user)):
    """Approve this user's most recent pending terminal execution request."""
    found = latest_pending(user.id)
    if not found:
        return ApprovalResponse(request_id="none", status="no_pending_requests")
    return _settle(*found, approved=True)


@router.post("/reject_latest", response_model=ApprovalResponse)
async def reject_latest_request(user: User = Depends(get_current_user)):
    """Reject this user's most recent pending terminal execution request."""
    found = latest_pending(user.id)
    if not found:
        return ApprovalResponse(request_id="none", status="no_pending_requests")
    return _settle(*found, approved=False)


@router.post("/{request_id}/approve", response_model=ApprovalResponse)
async def approve_request(request_id: str, user: User = Depends(get_current_user)):
    """Approve a pending terminal execution request."""
    item = find_pending(request_id, user.id)
    if not item:
        return ApprovalResponse(request_id=request_id, status="not_found_or_expired")
    return _settle(request_id, item, approved=True)


@router.post("/{request_id}/reject", response_model=ApprovalResponse)
async def reject_request(request_id: str, user: User = Depends(get_current_user)):
    """Reject a pending terminal execution request."""
    item = find_pending(request_id, user.id)
    if not item:
        return ApprovalResponse(request_id=request_id, status="not_found_or_expired")
    return _settle(request_id, item, approved=False)
