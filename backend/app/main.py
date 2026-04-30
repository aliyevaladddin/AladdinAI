# NOTICE: This file is protected under RCF-PL v1.2.8
# [RCF:PROTECTED]
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import (
    agents, auth, bentoml, channels_email, channels_messaging,
    chat, crm_activities, crm_contacts, crm_deals, mongodb,
    providers, router_config, vms, webhooks
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="AladdinAI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(router_config.router, prefix="/api")
app.include_router(channels_messaging.router, prefix="/api")
app.include_router(channels_email.router, prefix="/api")
app.include_router(crm_contacts.router, prefix="/api")
app.include_router(crm_deals.router, prefix="/api")
app.include_router(crm_activities.router, prefix="/api")
app.include_router(vms.router, prefix="/api")
app.include_router(mongodb.router, prefix="/api")
app.include_router(bentoml.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "AladdinAI API is running", "version": "0.1.0", "protocol": "RCF/1.2.8"}
