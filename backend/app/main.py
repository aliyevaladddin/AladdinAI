from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import (
    auth, vms, providers, mongodb, bentoml, agents, router_config, chat,
    channels_email, channels_messaging, webhooks,
    crm_contacts, crm_deals, crm_activities,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="AladdinAI Platform", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

routers = [
    # Auth
    auth,
    # Infrastructure
    vms, providers, mongodb, bentoml,
    # Agents & Router
    agents, router_config, chat,
    # Channels
    channels_email, channels_messaging, webhooks,
    # CRM
    crm_contacts, crm_deals, crm_activities,
]

for r in routers:
    app.include_router(r.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
