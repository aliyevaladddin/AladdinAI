# Application Services (Business Logic)

This directory contains the core business logic, background tasks, external SDK wrappers, and runner components of the AladdinAI application. 

By keeping logic inside dedicated service modules, we ensure that API routers (`app/routers/`) remain thin and focuses strictly on HTTP/WebSocket handling.

## Primary Services

### 🖥️ Infrastructure & Docker Routing
* **`docker_runner.py`**: Interacts with the Docker daemon to create, start, stop, and clean up interactive container terminals. It also handles dynamic Traefik routing configuration writes (`terminal-p{id}.yaml`) to the File provider directory.
* **`terminal_token_broker.py`**: Manages secure token creation, verification (`peek_token`), and session cookies (`aladdin_term_sess`) for container authentication.
* **`terminal_health.py`**: Performs asynchronous health checks on user terminals to ensure responsiveness.
* **`terminal_adapters/`**: Adapters for connecting different terminal technologies (e.g. `ttyd` generic HTTP connections).

### 🤖 LLM & Agent Execution
* **`orchestrator.py`**: The agent orchestrator that coordinates system tasks, parses user requests, and selects which agent or tool should handle a query.
* **`agent_runner.py`**: Executes an agent's reasoning loop, injecting the context window, prompt, and system variables.
* **`llm_service.py`**: Standardized service wrapper to perform completions, streaming, and embeddings across OpenAI, Anthropic, Gemini, and Groq providers.
* **`memory.py`**: Handles chat session memory retrieval and context windows.

### 🛡️ Safety & Security
* **`safety.py` & `url_safety.py`**: Guards against prompts injection, filters unsafe words/actions, and screens URLs prior to executing them within terminal containers.

### 💼 CRM, Channels & Webhooks
* **`crm_service.py`**: Business logic for deals updates, activity tracking, and contact merges.
* **`email_service.py` & `telegram_poller.py`**: Services that connect to external messaging hubs (Telegram polling, SMTP/IMAP send and read loops).
* **`webhook_service.py`**: Triggers, dispatches, and logs outgoing HTTP webhooks to external integrations.
