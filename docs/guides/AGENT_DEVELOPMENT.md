// NOTICE: This file is protected under RCF-PL
# Agent Development Guide

Complete guide to creating custom AI agents in AladdinAI.

## 🎯 What is an Agent?

An agent in AladdinAI is an autonomous AI entity with:
- **Identity** - Name, description, role
- **Brain** - LLM model and system prompt
- **Memory** - Private memory space with vector search
- **Tools** - Functions it can execute
- **Safety** - PII detection and content filtering

## 🚀 Quick Start

### 1. Create Agent via API

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sales_assistant",
    "display_name": "Sales Assistant",
    "system_prompt": "You are a helpful sales assistant. Help users track leads and close deals.",
    "model": "meta/llama-3.1-8b-instruct",
    "tools": ["search_contacts", "create_deal"],
    "memory_enabled": true
  }'
```

### 2. Create Agent via UI

1. Navigate to `/dashboard/agents`
2. Click "Create Agent"
3. Fill in the form:
   - **Name**: Unique identifier (lowercase, no spaces)
   - **Display Name**: Human-readable name
   - **Model**: Choose from connected providers
   - **System Prompt**: Agent's instructions
   - **Tools**: Select available tools
4. Click "Create"

## 📝 Agent Configuration

### System Prompt Best Practices

```python
# ✅ Good - Specific, actionable
system_prompt = """
You are a CRM sales assistant specialized in B2B lead qualification.

Your responsibilities:
1. Qualify inbound leads based on company size (>50 employees) and budget (>$10k)
2. Update contact records with qualification notes
3. Create deals only for qualified leads
4. Schedule follow-ups for nurturing

Always ask clarifying questions before taking actions.

Use tools to verify information in the CRM.
"""

# ❌ Bad - Too vague
system_prompt = "You are a helpful assistant."
```

### Model Selection

| Model | Use Case | Speed | Cost |
|-------|----------|-------|------|
| `meta/llama-3.1-8b-instruct` | Fast responses, simple tasks | ⚡️⚡️⚡️ | Free |
| `meta/llama-3.1-70b-instruct` | Complex reasoning | ⚡️⚡️ | Free |
| `nvidia/nemotron-4-340b-instruct` | Enterprise accuracy | ⚡️ | Free |
| `anthropic/claude-3-sonnet` | Best reasoning (BYOK) | ⚡️⚡️ | Paid |

## 🛠️ Tools

### Available Built-in Tools

```python
# Search and retrieval
- search_contacts(query: str)
- search_deals(status: str)
- get_contact_by_email(email: str)

# CRM operations
- create_contact(name: str, email: str, ...)
- update_contact(contact_id: int, ...)
- create_deal(title: str, value: float, ...)
- add_activity(type: str, description: str, ...)

# Communication
- send_email(to: str, subject: str, body: str)
- send_telegram_message(chat_id: str, text: str)

# Analysis
- analyze_image(image_url: str, prompt: str)
- generate_image(prompt: str)
- execute_sql(query: str)
```

### Creating Custom Tools

1. Create tool in `backend/app/tools/`:

```python
# backend/app/tools/slack_tools.py
from app.tools.registry import tool
from app.services.memory import ToolContext


@tool(
    name="send_slack_message",
    description="Send a message to a Slack channel",
    requires_auth=True
)
async def send_slack_message(
    channel: str,
    text: str,
    ctx: ToolContext
) -> dict:
    """
    Args:
        channel: Channel name or ID (e.g., "#general")
        text: Message content
        ctx: Tool context (auto-injected)
    """
    # Scope to user
    user_slack_token = get_user_slack_token(ctx.user_id)
    
    # Execute
    result = await slack_client.post_message(
        token=user_slack_token,
        channel=channel,
        text=text
    )
    
    return {"success": True, "timestamp": result.ts}
```

2. Tool is auto-registered via `@tool` decorator

3. Use in agent configuration:
```json
{
  "tools": ["send_slack_message"]
}
```

## 🧠 Memory System

### How Memory Works

```
User Input
    ↓
Agent processes with context
    ↓
Extracts key facts → Vector embedding
    ↓
Stored in agent_memory (MongoDB)
    ↓
Future queries → Vector search → Relevant context injected
```

### Memory Configuration

```python
# Enable memory for agent
agent_config = {
    "memory_enabled": True,
    "memory_window": 10,  # Last 10 messages in context
    "memory_relevance_threshold": 0.7  # Similarity score
}
```

### Memory API

```python
# Manual memory storage
POST /api/agents/{agent_id}/memory
{
  "content": "Customer prefers email communication, timezone PST",
  "metadata": {"contact_id": 123, "category": "preference"}
}

# Search memory
GET /api/agents/{agent_id}/memory/search?q=communication+preference
```

## 🔒 Safety and Gates

### PII Detection

Automatically redacts:
- Email addresses
- Phone numbers
- Credit card numbers
- Social security numbers

```python
# Controlled via safety_service.py
result = await safety_pii(
    text=user_input,
    phase="ingress"  # or "egress"
)
```

### Content Filtering

Uses NeMo Guardrails + Llama Guard:
- Toxicity detection
- Prompt injection prevention
- Off-topic detection

### Tool Restrictions

```python
# Restrict tools per agent
agent_config = {
    "allowed_tools": ["search_contacts", "create_deal"],
    "denied_tools": ["execute_sql", "delete_*"]
}
```

## 📊 Monitoring

### Execution Logs

All agent runs logged to `agent_messages`:

```sql
SELECT * FROM agent_messages
WHERE agent_id = 'sales_assistant'
ORDER BY created_at DESC
LIMIT 100;
```

### Tracing (Internal Edition)

```python
# Set ALADDIN_EDITION=internal
# Traces saved to agent_traces for self-forging
```

## 🔄 Multi-Agent Patterns

### Sequential Handoff

```python
# Agent 1: Lead Qualifier
result = await run_agent("lead_qualifier", input)

# Agent 2: Sales Assistant (receives qualified leads)
if result.metadata.get("qualified"):
    await run_agent("sales_assistant", {
        "lead_id": result.lead_id,
        "qualification": result.notes
    })
```

### Parallel Execution

```python
# Run multiple agents concurrently
results = await asyncio.gather(
    run_agent("market_researcher", {"company": "Acme Corp"}),
    run_agent("competitor_analyzer", {"company": "Acme Corp"}),
    run_agent("tech_stack_detector", {"company": "Acme Corp"})
)
```

## 🧪 Testing Agents

### CLI Testing

```bash
npx aladdin-ai agent test sales_assistant \
  --input "Find contacts at Acme Corp" \
  --verbose
```

### API Testing

```bash
curl -X POST http://localhost:8000/api/agents/sales_assistant/run \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{
    "message": "Find contacts at Acme Corp",
    "context": {}
  }'
```

### Unit Tests

```python
# backend/tests/test_agents.py
async def test_agent_with_tools():
    agent = await create_agent(
        name="test_agent",
        tools=["search_contacts"]
    )
    
    result = await run_agent(agent.id, {
        "message": "Find John at Acme"
    })
    
    assert result.tool_calls[0].name == "search_contacts"
    assert "John" in result.response
```

## 📚 Examples

### Customer Support Agent

```json
{
  "name": "support_agent",
  "display_name": "Support Assistant",
  "model": "meta/llama-3.1-70b-instruct",
  "system_prompt": "You are a customer support agent. Help users with technical issues. Always check the knowledge base before responding. Escalate to human if issue is complex.",
  "tools": [
    "search_knowledge_base",
    "create_ticket",
    "send_email"
  ],
  "memory_enabled": true
}
```

### Data Analyst Agent

```json
{
  "name": "analyst_agent",
  "display_name": "Data Analyst",
  "model": "nvidia/nemotron-4-340b-instruct",
  "system_prompt": "You are a data analyst. Generate SQL queries, analyze results, create visualizations. Always explain your methodology.",
  "tools": [
    "execute_sql",
    "create_chart",
    "export_csv"
  ],
  "memory_enabled": false
}
```

## 🚨 Troubleshooting

### Agent Not Responding
- Check provider connection: `GET /api/providers/connect`

- Verify model availability
- Check logs: `docker logs aladdinai-backend`

### Tools Not Working

- Verify tool is registered: Check `backend/app/tools/`
- Check tool permissions in agent config
- Review tool execution logs in `agent_messages`

### Memory Issues
- Ensure MongoDB connection is healthy
- Check Atlas Vector Search index exists

- Verify `memory_enabled: true` in agent config

## 🔗 Related

- [Tool Development Guide](./TOOL_DEVELOPMENT.md)
- [Memory System](./MEMORY.md)
- [API Reference](../API.md)
- [ADR-0001: Self-Forging](../adr/0001-self-forging-training.md)

---

**Questions?** Open an issue on [GitHub](https://github.com/aliyevaladddin/AladdinAI/issues)
