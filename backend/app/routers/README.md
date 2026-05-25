# API Endpoints (FastAPI Routers)

This directory contains the FastAPI routing modules, which handle incoming HTTP requests and WebSocket connections from the frontend or external systems.

## Architecture & Integration
* **Dependency Injection**:
  * For database transactions, routers use `get_db = Depends(get_async_db)`.
  * For user authentication, routers rely on `current_user: User = Depends(get_current_user)`.
* **Validation & Serialization**: All endpoints receive and return structured data validated through Pydantic schemas defined in `app/schemas/`.
* **API Documentation**: The routers automatically populate the interactive OpenAPI/Swagger documentation available at `http://localhost:8000/docs`.

## Endpoint Modules

### 🖥️ Web Terminals & Infrastructure
* **`terminal_providers.py`**: Manages the lifecycle of user-specific `ttyd` containers (create, start, stop, delete). It also exposes the `/api/terminal/auth` endpoint used by Traefik's `forwardAuth` middleware for secure session routing.
* **`terminal_ws.py`**: Manages WebSocket upgrades and proxying for interactive terminal communication.
* **`vms.py`**: Endpoints for starting, stopping, and managing VMs.

### 🤖 AI Agents & Chat
* **`agents.py`**: Endpoints to create, edit, and configure AI agents, connect tools, and assign system personas.
* **`chat.py`**: Handles interactive chat sessions with streaming LLM completions.
* **`providers.py`**: Set up and manage LLM API credentials with automatic server-side encryption.
* **`bentoml.py`** & **`mongodb.py`**: Integrations with machine learning models and external Vector DB / NoSQL databases.

### 💼 CRM Features
* **`crm_contacts.py`**: Add, update, and manage CRM contacts.
* **`crm_deals.py`**: Deals pipeline and pipeline stage transitions.
* **`crm_activities.py`**: Log communications, reminders, and activities associated with active deals.

### ⚙️ Core Services & Integrations
* **`auth.py`**: Manages user login, registration, and JWT token rotation.
* **`user.py`**: Provides current user profile details.
* **`notifications.py`**: Distributes system notifications to the user interface.
* **`channels_messaging.py`** & **`channels_email.py`**: Webhook receivers and interfaces for Telegram chats and Email.
* **`webhooks.py`**: Configurable webhooks to notify third-party applications.
