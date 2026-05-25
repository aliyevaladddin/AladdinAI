# Database Models (SQLAlchemy)

This directory contains the SQLAlchemy models defining the relational database schema (SQLite / PostgreSQL) for AladdinAI and the relationships between tables.

## Principles & Best Practices
* **Base Class**: All models inherit from the declarative `Base` class imported from `app.database`.
* **Async Compatibility**: Database queries are executed asynchronously using `AsyncSession`.
* **Relationships**: Use SQLAlchemy's `relationship` with `lazy="selectin"` for loading relationship attributes asynchronously (this avoids the N+1 query problem).
* **Schema Synchronization**: Each model has corresponding Pydantic schemas in `app/schemas/` for input validation and output serialization.

## Core Models

### 🖥️ Infrastructure & Web Terminals
* **`TerminalProvider` (`terminal_provider.py`)**: Stores user-specific web terminal settings, container credentials, network names, and lifecycle states for active `ttyd` containers.
* **`VM` (`vm.py`)**: Describes Virtual Machine instances used across the workspace.

### 🤖 Agents & LLMs
* **`Agent` (`agent.py`)**: AI agents, their configured system prompts, roles, and connected capabilities.
* **`AgentMessage` (`agent_message.py`)** & **`Conversation` (`conversation.py`)**: Stores the full chat history, context, and message exchanges between users and agents.
* **`LLMProvider` (`llm_provider.py`)**: Stores configured integrations (OpenAI, Anthropic, Gemini, Groq) with encrypted API credentials.

### 💼 CRM & Communications
* **`Contact` (`contact.py`)**, **`Deal` (`deal.py`)**, & **`Activity` (`activity.py`)**: Entities for CRM features, pipelines, kanban-style deals, and timeline logs.
* **`EmailAccount` (`email_account.py`)** & **`MessagingChannel` (`messaging_channel.py`)**: Third-party communications setups (Telegram channels, SMTP/IMAP servers, and custom Webhooks).

### ⚙️ Core Core
* **`User` (`user.py`)**: User accounts, access levels, and hashed credentials.
* **`Notification` (`notification.py`)**: Real-time notifications dispatched to the frontend UI.
