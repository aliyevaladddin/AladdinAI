// NOTICE: This file is protected under RCF-PL
# Agent Tools (Function Calling)

This directory contains the tools and capabilities available to AladdinAI's AI Agents. 

These tools utilize LLM function calling to allow agents to interact with databases, communicate with other agents, send messages, analyze files, and interface with external services.

## Architecture & Base Classes
* **`base.py`**: Defies the abstract base class and registration decorators for custom Agent Tools.
* **`capabilities.py`**: Interfaces that define how tools report their arguments schema (using Pydantic models) to LLMs (OpenAI, Anthropic, Gemini, Groq).

## Available Tools

### 💬 Messaging & Communication
* **`messaging.py`**: Enables agents to send emails, read inbox emails (`read_emails`), dispatch Telegram messages (`send_telegram_message`), and post Slack webhooks (`send_slack_message`).

### Web & API Interactions
* **`http_tools.py`**: Generic HTTP GET (`http_get`) and POST (`http_post`) tools for arbitrary REST API integration.
* **`web_search.py`**: Native SearXNG/Tavily meta-search.
* **`browser.py`**: Web page scraping (`fetch_url`).

### Code Execution Sandbox
* **`python_sandbox.py`**: Isolated Python 3 execution sandbox (`run_python_code`) with execution timeouts and stdout/stderr capture.

### Scheduling & Reminders
* **`reminders.py`**: Point-in-time user reminders (`create_reminder`) with automated cron generation.

### Agent Memory
* **`memory.py`**: Provides tools for agents to write, read, and search long-term associative memory keys in NoSQL/Vector databases.

### Multi-Agent Collaboration
* **`inter_agent.py`**: Implements inter-agent communication tools (`delegate_to_agent`, `chat_with_agent`, `broadcast_agents`). Allows multiple specialized agents to collaborate, delegate tasks, query each other, and report progress.

### Computer Vision & Media
* **`vision.py`**: Tools for processing media files, scanning documents, and analyzing uploaded images using multimodal LLMs.
* **`excel.py`**: Excel reading and writing (`read_excel`, `write_excel`).

