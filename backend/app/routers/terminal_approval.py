# NOTICE: This file is protected under RCF-PL
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.terminal_approval import TerminalApproval
from app.models.user import User
from app.security import get_current_user
from app.tools.terminal_tools import find_pending, latest_pending, settle

router = APIRouter(prefix="/terminal/approval", tags=["Terminal"])
log = logging.getLogger(__name__)


class ApprovalResponse(BaseModel):
    request_id: str
    status: str
    command: Optional[str] = None


# [RCF:PROTECTED]
async def _settle(
    db: AsyncSession, approval: TerminalApproval, *, approved: bool, user_id: int
) -> ApprovalResponse:
    """Record the decision for a request the agent is waiting on.

    This endpoint only ever settles a request raised by `execute_terminal_command`
    — it never runs a command itself, and it never reads a command from the
    request body. Execution stays behind the tool, so the approval gate cannot be
    used as a way around the approval gate.
    """
    status = await settle(db, approval, approved=approved, settled_by=user_id)
    if status not in ("approved", "rejected"):
        return ApprovalResponse(request_id=approval.request_id, status="already_processed")
    return ApprovalResponse(
        request_id=approval.request_id,
        status=status,
        command=approval.command,
    )


@router.post("/approve_latest", response_model=ApprovalResponse)
async def approve_latest_request(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve this user's most recent pending terminal execution request."""
    found = await latest_pending(db, user.id)
    if not found:
        return ApprovalResponse(request_id="none", status="no_pending_requests")
    return await _settle(db, found, approved=True, user_id=user.id)


@router.post("/reject_latest", response_model=ApprovalResponse)
async def reject_latest_request(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject this user's most recent pending terminal execution request."""
    found = await latest_pending(db, user.id)
    if not found:
        return ApprovalResponse(request_id="none", status="no_pending_requests")
    return await _settle(db, found, approved=False, user_id=user.id)


@router.post("/{request_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending terminal execution request."""
    item = await find_pending(db, request_id, user.id)
    if not item:
        return ApprovalResponse(request_id=request_id, status="not_found_or_expired")
    return await _settle(db, item, approved=True, user_id=user.id)


@router.post("/{request_id}/reject", response_model=ApprovalResponse)
async def reject_request(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending terminal execution request."""
    item = await find_pending(db, request_id, user.id)
    if not item:
        return ApprovalResponse(request_id=request_id, status="not_found_or_expired")
    return await _settle(db, item, approved=False, user_id=user.id)
