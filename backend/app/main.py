# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings as app_settings
from app.routers import (
    agents, auth, bentoml, channels_email, channels_messaging,
    chat, crm_activities, crm_contacts, crm_deals, crm_orders, crm_products, dashboard, digest, forging, mongodb,
    notifications, native_tools, providers, reports as reports_router, router_config, search,
    settings, sql, ssh_exec,
    terminal_approval, terminal_providers, terminal_ws, triggers as triggers_router, vms, webhooks,
    websearch,
)
from app.services import triggers as triggers_service
from app.services import telegram_poller
from app.services import terminal_health
from app.services import autonomous_bot_scheduler
from app.services import native_terminal_daemon
from app.tools import excel as _excel_tools  # noqa: F401 — registers excel tools

log = logging.getLogger(__name__)

# Rate limiter — keyed by client IP by default.
# To key by authenticated user, replace get_remote_address with a custom
# function that extracts user_id from the JWT in request.headers.
limiter = Limiter(key_func=get_remote_address)

# Read version from CLI package.json (single source of truth)
try:
    cli_package_path = Path(__file__).resolve().parent.parent.parent / "cli" / "package.json"
    with open(cli_package_path) as f:
        cli_package = json.load(f)
        VERSION = cli_package.get("version", "2.1.5")
except Exception:
    VERSION = "2.1.5"  # Fallback


# [RCF:PROTECTED]
@asynccontextmanager
# [RCF:PROTECTED]
async def lifespan(app: FastAPI):
    """Manages startup and shutdown of background services."""
    log.info("AladdinAI starting up (v%s)", VERSION)
    await triggers_service.hydrate_from_db()
    await telegram_poller.start()
    terminal_health.start()
    autonomous_bot_scheduler.start_scheduler()
    native_terminal_daemon.start_daemon()
    yield
    log.info("AladdinAI shutting down")
    native_terminal_daemon.stop_daemon()
    await triggers_service.shutdown()
    await telegram_poller.stop()
    terminal_health.stop()
    autonomous_bot_scheduler.stop_scheduler()

app = FastAPI(
    title="AladdinAI API",
    lifespan=lifespan,
    description="""
    🧞 **AladdinAI** - Self-hosted AI workspace with multi-agent orchestration, persistent memory, and tool execution.

    ## Features

    * 🤖 **Multi-Agent System** - Create and orchestrate specialized AI agents
    * 🧠 **Persistent Memory** - Vector-based memory with per-agent isolation
    * 🛠️ **Tool Execution** - Extensible tool registry with safety gates
    * 📊 **CRM Integration** - Contacts, deals, and activities management
    * 🔐 **Safety First** - PII detection, content filtering, and audit logging
    * 🔗 **RCF Protocol** - Cryptographic signing for webhook authenticity

    ## Authentication

    Most endpoints require JWT authentication. Include the token in the `Authorization` header:
    ```
    Authorization: Bearer <your_jwt_token>
    ```

    ## Rate Limits

    API endpoints are rate-limited per IP address to prevent abuse.
    Exceeding a limit returns HTTP 429 with a `Retry-After` header.
    """,
    version=VERSION,
    terms_of_service="https://github.com/aliyevaladddin/AladdinAI/blob/main/LICENSE",
    contact={
        "name": "Aladdin Aliyev",
        "url": "https://github.com/aliyevaladddin/AladdinAI",
        "email": "aladdin@aliyev.site",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://github.com/aliyevaladddin/AladdinAI/blob/main/LICENSE",
    },
    openapi_tags=[
        {"name": "auth", "description": "Authentication and user management"},
        {"name": "agents", "description": "Agent creation, configuration, and execution"},
        {"name": "chat", "description": "Chat interface and message history"},
        {"name": "crm", "description": "CRM operations - contacts, deals, activities"},
        {"name": "providers", "description": "LLM provider management"},
        {"name": "settings", "description": "System and user settings"},
        {"name": "webhooks", "description": "Webhook endpoints for external integrations"},
        {"name": "Terminal", "description": "Terminal, PTY C-Daemon & Remote SSH session management"},
    ],
)


# ── Attach rate limiter state and 429 error handler ─────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS origins are configured via CORS_ORIGINS env var (comma-separated).
# Defaults to localhost:3000 for local development.
# Example for production: CORS_ORIGINS=https://app.example.com,https://admin.example.com
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(terminal_ws.router, prefix="/api")
app.include_router(native_tools.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(router_config.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(sql.router, prefix="/api")
app.include_router(channels_messaging.router, prefix="/api")
app.include_router(channels_email.router, prefix="/api")
app.include_router(crm_contacts.router, prefix="/api")
app.include_router(crm_deals.router, prefix="/api")
app.include_router(crm_activities.router, prefix="/api")
app.include_router(crm_products.router, prefix="/api")
app.include_router(crm_orders.router, prefix="/api")
app.include_router(vms.router, prefix="/api/vms")
app.include_router(mongodb.router, prefix="/api")
app.include_router(bentoml.router, prefix="/api/bentoml", tags=["BentoML"])
app.include_router(webhooks.router, prefix="/api")
app.include_router(ssh_exec.router, prefix="/api")
app.include_router(triggers_router.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(terminal_providers.router, prefix="/api/terminal")
app.include_router(terminal_approval.router, prefix="/api")
app.include_router(reports_router.router, prefix="/api")
app.include_router(digest.router, prefix="/api")
app.include_router(forging.router, prefix="/api")
app.include_router(websearch.router, prefix="/api")

# [RCF:PROTECTED]
@app.get("/")
# [RCF:PROTECTED]
@limiter.limit("60/minute")
# [RCF:PROTECTED]
async def root(request: Request):
    return {"message": "AladdinAI API is running", "version": VERSION, "protocol": "RCF/2.0.3"}


# [RCF:PROTECTED]
@app.get("/health")
# [RCF:PROTECTED]
@limiter.limit("120/minute")
# [RCF:PROTECTED]
async def health(request: Request):
    """Health check endpoint for load balancers and container orchestration."""
    return {"status": "ok", "version": VERSION}


# [RCF:PROTECTED]
@app.get("/api/edition")
# [RCF:PROTECTED]
async def edition():
    """Open-core edition marker. Lets the frontend / CLI / `doctor` learn the
    commercial boundary (e.g. whether to surface forge UI). Public, non-secret.
    """
    return {"edition": app_settings.edition}
