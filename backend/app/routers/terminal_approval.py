# NOTICE: This file is protected under RCF-PL
import logging
import subprocess
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.user import User
from app.security import get_current_user
from app.tools.terminal_tools import PENDING_APPROVALS, mask_secrets, set_rlimits

router = APIRouter(prefix="/terminal/approval", tags=["Terminal"])
log = logging.getLogger(__name__)


class ApprovalPayload(BaseModel):
    command: Optional[str] = None

class ApprovalResponse(BaseModel):
    request_id: str
    status: str
    output: Optional[str] = None


@router.post("/approve_latest", response_model=ApprovalResponse)
async def approve_latest_request(payload: Optional[ApprovalPayload] = None, user: User = Depends(get_current_user)):
    """Approve the most recent pending terminal execution request."""
    if PENDING_APPROVALS:
        request_id = list(PENDING_APPROVALS.keys())[-1]
        item = PENDING_APPROVALS[request_id]
        future = item.get("future")
        if future and not future.done():
            future.set_result(True)
            log.info("Latest terminal execution request APPROVED [%s]", request_id)
            return ApprovalResponse(request_id=request_id, status="approved")
    
    # Fallback: if command is provided directly in request body, execute safely
    if payload and payload.command:
        try:
            res = subprocess.run(
                ["bash", "-c", payload.command],
                capture_output=True,
                text=True,
                timeout=15,
                preexec_fn=set_rlimits,
                cwd="/workspaces/AladdinAI",
            )
            out = mask_secrets((res.stdout or "") + ("\n" + res.stderr if res.stderr else ""))
            return ApprovalResponse(request_id="direct", status="approved_and_executed", output=out)
        except Exception as e:
            return ApprovalResponse(request_id="direct", status="failed", output=str(e))

    return ApprovalResponse(request_id="none", status="no_pending_requests")


@router.post("/reject_latest", response_model=ApprovalResponse)
async def reject_latest_request(user: User = Depends(get_current_user)):
    """Reject the most recent pending terminal execution request."""
    if not PENDING_APPROVALS:
        return ApprovalResponse(request_id="none", status="no_pending_requests")
    
    request_id = list(PENDING_APPROVALS.keys())[-1]
    item = PENDING_APPROVALS[request_id]
    future = item.get("future")
    if future and not future.done():
        future.set_result(False)
        log.info("Latest terminal execution request REJECTED [%s]", request_id)
        return ApprovalResponse(request_id=request_id, status="rejected")
    
    return ApprovalResponse(request_id=request_id, status="already_processed")


@router.post("/{request_id}/approve", response_model=ApprovalResponse)
async def approve_request(request_id: str, user: User = Depends(get_current_user)):
    """Approve a pending terminal execution request."""
    item = PENDING_APPROVALS.get(request_id)
    if not item:
        return ApprovalResponse(request_id=request_id, status="not_found_or_expired")
    
    future = item.get("future")
    if future and not future.done():
        future.set_result(True)
        log.info("Terminal execution request APPROVED [%s]", request_id)
        return ApprovalResponse(request_id=request_id, status="approved")
    
    return ApprovalResponse(request_id=request_id, status="already_processed")


@router.post("/{request_id}/reject", response_model=ApprovalResponse)
async def reject_request(request_id: str, user: User = Depends(get_current_user)):
    """Reject a pending terminal execution request."""
    item = PENDING_APPROVALS.get(request_id)
    if not item:
        return ApprovalResponse(request_id=request_id, status="not_found_or_expired")
    
    future = item.get("future")
    if future and not future.done():
        future.set_result(False)
        log.info("Terminal execution request REJECTED [%s]", request_id)
        return ApprovalResponse(request_id=request_id, status="rejected")
    
    return ApprovalResponse(request_id=request_id, status="already_processed")

