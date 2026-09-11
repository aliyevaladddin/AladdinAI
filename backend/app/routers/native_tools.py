# NOTICE: This file is protected under RCF-PL
# [RCF:PROTECTED]
import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user import User
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/native", tags=["Native Tools"])

NATIVE_DIR = Path(__file__).resolve().parent.parent.parent / "native"
GREP_BIN = NATIVE_DIR / "aladdin-grep"
LOG_BIN = NATIVE_DIR / "aladdin-log-stream"
LOGS_ROOT = (Path(__file__).resolve().parent.parent.parent / "logs").resolve()


async def ensure_binaries():
    if not (GREP_BIN.exists() and LOG_BIN.exists()):
        try:
            proc = await asyncio.create_subprocess_exec(
                "make", "-C", str(NATIVE_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            log.error("Failed to build native C binaries: %s", e)


@router.get("/search")
async def fast_native_search(query: str = Query(..., min_length=1), path: str = Query("."), current_user: User = Depends(get_current_user)):
    """Fast native C project code search using mmap memory mapping."""
    await ensure_binaries()
    if not GREP_BIN.exists():
        raise HTTPException(status_code=500, detail="Native grep C binary not compiled")

    # Path traversal validation using Path.is_relative_to
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.resolve()

    user_path = Path(path)
    if user_path.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")

    normalized_relative = (Path(".") / user_path)
    if ".." in normalized_relative.parts:
        raise HTTPException(status_code=400, detail="Path traversal is not allowed")

    target_path = (base_dir / normalized_relative).resolve()
    if not target_path.is_relative_to(base_dir):
        raise HTTPException(status_code=400, detail="Search path is outside allowed workspace directory")

    target_dir = str(target_path)
    try:
        proc = await asyncio.create_subprocess_exec(
            str(GREP_BIN), "--path", target_dir, "--query", query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        results = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except Exception:
                    log.debug("Skipping unparseable search result line")
        return {"query": query, "count": len(results), "results": results}
    except Exception as e:
        log.exception("Error running fast native search: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/filter")
async def filter_log_stream(filter_str: str = Query(""), log_path: str = Query(""), current_user: User = Depends(get_current_user)):
    """High-speed C log stream filtering engine."""
    await ensure_binaries()
    if not LOG_BIN.exists():
        raise HTTPException(status_code=500, detail="Native log stream C binary not compiled")

    args = [str(LOG_BIN)]
    if filter_str:
        args.extend(["--filter", filter_str])
    if log_path:
        # Path traversal validation using normalized relative-path checks + containment check
        base_dir = LOGS_ROOT.resolve()
        normalized_input = Path(log_path)
        normalized_rel = normalized_input.as_posix()
        if normalized_input.is_absolute() or ".." in Path(normalized_rel).parts:
            raise HTTPException(status_code=400, detail="Invalid log_path")

        target_path = (base_dir / normalized_rel).resolve()
        if not target_path.is_relative_to(base_dir):
            raise HTTPException(status_code=400, detail="log_path is outside allowed logs directory")
        if not target_path.exists():
            raise HTTPException(status_code=400, detail="log_path does not exist")
        args.extend(["--file", str(target_path)])

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        logs = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except Exception:
                    log.debug("Skipping unparseable log line")
        return {"count": len(logs), "logs": logs}
    except Exception as e:
        log.exception("Error running native log filter: %s", e)
        raise HTTPException(status_code=500, detail=str(e))