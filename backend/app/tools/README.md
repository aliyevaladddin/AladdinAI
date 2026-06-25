// NOTICE: This file is protected under RCF-PL
# Agent Tools (Function Calling)

This directory contains the tools and capabilities available to AladdinAI's AI Agents. 

These tools utilize LLM function calling to allow agents to interact with databases, communicate with other agents, send messages, analyze files, and interface with external services.

## Architecture & Base Classes
* **`base.py`**: Defies the abstract base class and registration decorators for custom Agent Tools.
* **`capabilities.py`**: Interfaces that define how tools report their arguments schema (using Pydantic models) to LLMs (OpenAI, Anthropic, Gemini, Groq).

## Available Tools

### 💬 Messaging & Communication
* **`messaging.py`**: Enables agents to send emails, publish notifications, or dispatch Telegram channel updates automatically based on triggers.

### 🧠 Agent Memory
* **`memory.py`**: Provides tools for agents to write, read, and search long-term associative memory keys in NoSQL/Vector databases.

### 🤝 Multi-Agent Collaboration
* **`inter_agent.py`**: Implements inter-agent communication tools. This allows multiple specialized agents to collaborate, delegate tasks, query each other, and report progress.

### 👁️ Computer Vision
* **`vision.py`**: Tools for processing media files, scanning documents, and analyzing uploaded images using multimodal LLMs.
