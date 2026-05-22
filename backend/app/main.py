# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    agents, auth, bentoml, channels_email, channels_messaging,
    chat, crm_activities, crm_contacts, crm_deals, dashboard, mongodb,
    notifications, providers, router_config, search, ssh_exec,
    terminal_ws, triggers as triggers_router, vms, webhooks,
)
from app.services import triggers as triggers_service
from app.services import telegram_poller
from app.services import terminal_health

app = FastAPI(title="AladdinAI API")


@app.on_event("startup")
async def _start_scheduler():
    await triggers_service.hydrate_from_db()
    await telegram_poller.start()
    terminal_health.start()


@app.on_event("shutdown")
async def _stop_scheduler():
    await triggers_service.shutdown()
    await telegram_poller.stop()
    terminal_health.stop()

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(terminal_ws.router)
app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(router_config.router, prefix="/api")
app.include_router(channels_messaging.router, prefix="/api")
app.include_router(channels_email.router, prefix="/api")
app.include_router(crm_contacts.router, prefix="/api")
app.include_router(crm_deals.router, prefix="/api")
app.include_router(crm_activities.router, prefix="/api")
app.include_router(vms.router, prefix="/api/vms")
app.include_router(mongodb.router, prefix="/api")
app.include_router(bentoml.router, prefix="/api/bentoml", tags=["BentoML"])
app.include_router(webhooks.router, prefix="/api")
app.include_router(ssh_exec.router, prefix="/api")
app.include_router(triggers_router.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(terminal_providers.router, prefix="/api/terminal", tags=["terminal"])

@app.get("/")
async def root():
    return {"message": "AladdinAI API is running", "version": "0.1.0", "protocol": "RCF/2.0.3"}
