// NOTICE: This file is protected under RCF-PL
# Data Validation & Serialization (Pydantic Schemas)

This directory contains Pydantic schemas used for request body validation, query parameter parsing, and API response serialization.

## Why Pydantic?
* **Type Safety**: Enforces type rules before data ever hits database queries or application services.
* **Auto-Documentation**: Feeds directly into FastAPI's OpenAPI generator, making Swagger UI models accurate and self-updating.
// [RCF:PROTECTED]
* **Safe Serialization**: Prevents leaking sensitive columns (like password hashes or raw decrypted API keys) by explicitly choosing which fields to include in response schemas (e.g., using `response_model` in routers).

## Core Schema Groups
* **`auth.py`**: Login request structures, register payloads, and token response payloads (`Token`, `TokenData`).
* **`terminal.py`**: Request/response types for managing web terminal providers, VM configurations, and dynamic session links.
* **`agents.py`**: Parameters for configuring AI agents, injecting system prompts, and custom tools configurations.
* **`crm.py`**: Definitions for creating and updating CRM models: Contacts, Deals, and Activities.
* **`channels.py` & `webhook.py`**: Structures for handling messaging adapters, Email/Telegram payloads, and outbound webhooks.
* **`connections.py` & `router.py`**: Connections configurations for databases (MongoDB, BentoML) and internal service routers.
