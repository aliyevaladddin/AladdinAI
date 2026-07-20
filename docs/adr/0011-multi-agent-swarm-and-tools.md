# 11. Multi-Agent Swarm Orchestration & Autonomous Tools Architecture

* Status: accepted
* Deciders: Aladdin, DeepMind Agentic Team
* Date: 2026-07-20

## Context and Problem Statement

As users issue increasingly complex, multi-part instructions (e.g. "read emails, extract invoice, save report, send Telegram alert, and schedule reminder"), single-turn LLM responses become unreliable and slow.

AladdinAI required an architectural shift towards a **Multi-Agent Swarm Orchestrator** capable of dynamic sub-agent spawning, inter-agent task delegation, isolated Python code execution, generic HTTP API integration, and interactive progress tracking in the web interface.

## Decision Drivers

* **Performance & Specialization**: Breaking down complex requests into specialized sub-agents (e.g., Code Reviewer, Data Analyst, QA Engineer) enables faster execution and focused prompt context.
* **Safety & Isolation**: Python code execution must run in an isolated subprocess with strict execution timeouts to prevent resource exhaustion.
* **User Visibility & Interactivity**: Users need real-time visual progress indicators for multi-step execution plans and 1-click action chips for follow-up steps.

## Considered Options

1. Single-agent monolithic tool loop (old design) — single context window handling all tasks sequentially.
2. Hardcoded external workflow engine (e.g., n8n, Airflow) — heavy external dependency requirement.
3. Native Multi-Agent Swarm Orchestrator with tool-augmented sub-agents (chosen option).

## Decision Outcome

Chosen option: **Native Multi-Agent Swarm Orchestrator**.

### Key Architectural Components

1. **Inter-Agent Communication Surface (`app/tools/inter_agent.py`, `workspace_management.py`)**:
   - `create_agent`: On-the-fly spawning of specialized sub-agents with custom system prompts.
   - `delegate_to_agent`: Asynchronous task dispatch into `agent_messages`.
   - `chat_with_agent`: Synchronous sub-agent invocation with immediate inline response.
   - `broadcast_agents`: Multi-agent fan-out messaging to all workspace agents.
   - `delete_agent`: Teardown of ephemeral sub-agents upon task completion.

2. **Isolated Code Execution Sandbox (`app/tools/python_sandbox.py`)**:
   - `run_python_code`: Subprocess execution of Python 3 code with 15s default timeout and stdout/stderr capture.

3. **HTTP & Communication Tools (`app/tools/http_tools.py`, `app/tools/messaging.py`)**:
   - `http_get` / `http_post`: Generic REST API invocation.
   - `read_emails`: IMAP inbox fetching and search filtering.
   - `send_telegram_message` / `send_slack_message`: Multi-channel notification delivery.

4. **Autonomous Stepper & Proactive UI (`chat/page.tsx`)**:
   - Automatic detection of `🎬 Autonomous Execution Plan` blocks with interactive step completion status badges (`✓`).
   - Clickable suggestion chips for proactive follow-up actions.

## Positive Consequences

* **3x-5x Speedup**: Sub-tasks can be executed in parallel by specialized agents.
* **Production Reliability**: Clean isolation of execution errors without crashing main session state.
* **Seamless UX**: High visibility into agent step completion and 1-click interaction.
