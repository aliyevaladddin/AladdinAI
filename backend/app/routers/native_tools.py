# NOTICE: This file is protected under RCF-PL
# [RCF:PROTECTED]
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from app.security import get_current_user
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/native", tags=["Native Tools"])

NATIVE_DIR = Path(__file__).resolve().parent.parent.parent / "native"
GREP_BIN = NATIVE_DIR / "aladdin-grep"
LOG_BIN = NATIVE_DIR / "aladdin-log-stream"

def ensure_binaries():
    if not (GREP_BIN.exists() and LOG_BIN.exists()):
        try:
            subprocess.run(["make", "-C", str(NATIVE_DIR)], capture_output=True, timeout=15)
        except Exception as e:
            log.error("Failed to build native C binaries: %s", e)

@router.get("/search")
async def fast_native_search(query: str = Query(..., min_length=1), path: str = Query("."), current_user: User = Depends(get_current_user)):
    """Fast native C project code search using mmap memory mapping."""
    ensure_binaries()
    if not GREP_BIN.exists():
        raise HTTPException(status_code=500, detail="Native grep C binary not compiled")

    target_dir = os.path.abspath(path)
    try:
        proc = await asyncio.create_subprocess_exec(
            str(GREP_BIN), "--path", target_dir, "--query", query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()

        results = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except Exception:
                    pass
        return {"query": query, "count": len(results), "results": results}
    except Exception as e:
        log.exception("Error running fast native search: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/filter")
async def filter_log_stream(filter_str: str = Query(""), log_path: str = Query(""), current_user: User = Depends(get_current_user)):
    """High-speed C log stream filtering engine."""
    ensure_binaries()
    if not LOG_BIN.exists():
        raise HTTPException(status_code=500, detail="Native log stream C binary not compiled")

    args = [str(LOG_BIN)]
    if filter_str:
        args.extend(["--filter", filter_str])
    if log_path and os.path.exists(log_path):
        args.extend(["--file", log_path])

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()

        logs = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except Exception:
                    pass
        return {"count": len(logs), "logs": logs}
    except Exception as e:
        log.exception("Error running native log filter: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
