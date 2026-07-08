// NOTICE: This file is protected under RCF-PL
# Tool Development Guide

Complete guide to creating and registering tools for AladdinAI agents.

## 🎯 What is a Tool?

A tool is a function that an AI agent can call to interact with external systems or perform computations. Tools extend agent capabilities beyond text generation.

**Examples:**
- Search CRM contacts
- Send emails
- Execute SQL queries
- Generate images
- Make API calls

## 🏗️ Tool Architecture

```
Agent receives user request
    ↓
LLM decides which tool to use
    ↓
Tool executed with parameters
    ↓
Result returned to LLM
    ↓
LLM generates response with tool results
```

## 🚀 Quick Start

### 1. Create a Simple Tool

```python
# backend/app/tools/weather_tools.py
from app.tools.registry import tool
from app.services.memory import ToolContext
import httpx


@tool(
    name="get_weather",
    description="Get current weather for a city. Use when user asks about weather conditions.",
    requires_auth=False
)
async def get_weather(
    city: str,
    units: str = "celsius",
    ctx: ToolContext = None
) -> dict:
    """
    Get current weather conditions.
    
    Args:
        city: City name (e.g., "San Francisco")
        units: Temperature units ("celsius" or "fahrenheit")
        ctx: Tool context (auto-injected, optional)
    
    Returns:
        Weather data including temperature, conditions, humidity
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.weather.com/v1/current",
            params={"city": city, "units": units}
        )
        data = response.json()
    
    return {
        "temperature": data["temp"],
        "conditions": data["weather"],
        "humidity": data["humidity"],
        "city": city
    }
```

### 2. Tool is Auto-Registered

The `@tool` decorator automatically registers the tool. No manual registration needed!

### 3. Use in Agent

```json
{
  "name": "weather_assistant",
  "tools": ["get_weather"]
}
```

## 📋 Tool Decorator Reference

### Parameters

```python

@tool(
    name: str,                    # Unique tool identifier
    description: str,             # What the tool does (shown to LLM)
    requires_auth: bool = False,  # Does tool need user authentication?
    category: str = "general",    # Tool category for organization
    dangerous: bool = False,      # Requires extra confirmation?
    scoped_to_user: bool = True   # Should tool access be user-scoped?
)
```

### Context Parameter

Every tool receives a `ToolContext` with:

```python

@dataclass

class ToolContext:
    user_id: int           # Current user ID
    agent_id: str         # Agent executing the tool
    conversation_id: str  # Current conversation
    metadata: dict        # Additional context
```

## 🔧 Tool Patterns

### Pattern 1: Read-Only Query Tool

```python

@tool(
    name="search_documentation",
    description="Search technical documentation for answers",
    requires_auth=False
)
async def search_documentation(
    query: str,
    ctx: ToolContext
) -> dict:
    """Search docs and return relevant sections."""
    results = await vector_search(
        collection="docs",
        query=query,
        limit=5
    )
    
    return {
        "results": [
            {
                "title": r.title,
                "content": r.content,
                "url": r.url
            }
            for r in results
        ]
    }
```

### Pattern 2: User-Scoped Write Tool

```python

@tool(
    name="create_contact",
    description="Create a new CRM contact",
    requires_auth=True,
    scoped_to_user=True
)
async def create_contact(
    name: str,
    email: str,
    company: str,
    ctx: ToolContext
) -> dict:
    """Create contact scoped to current user."""
    contact = await db.contacts.insert({
        "user_id": ctx.user_id,  # ✅ Scoped to user
        "name": name,
        "email": email,
        "company": company,
        "created_at": datetime.utcnow()
    })
    
    return {
        "contact_id": contact.id,
        "message": f"Created contact: {name}"
    }
```

### Pattern 3: External API Integration

```python

@tool(
    name="send_slack_message",
    description="Send a message to Slack channel",
    requires_auth=True
)
async def send_slack_message(
    channel: str,
    text: str,
    ctx: ToolContext
) -> dict:
    """Send Slack message using user's token."""
    # Get user's Slack token
    user_token = await get_user_integration(
        user_id=ctx.user_id,
        integration="slack"
    )
    
    if not user_token:
        return {
            "error": "Slack not connected. Visit /settings/integrations"
        }
    
    # Send message
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "channel": channel,
                "text": text
            }
        )
    
    return response.json()
```

### Pattern 4: Dangerous Tool (Requires Confirmation)

```python

@tool(
    name="delete_all_contacts",
    description="Delete all contacts in the CRM. USE WITH EXTREME CAUTION.",
    requires_auth=True,
    dangerous=True  # ✅ Requires explicit user confirmation
)
async def delete_all_contacts(
    confirm: bool,
    ctx: ToolContext
) -> dict:
    """Delete all user's contacts. Requires confirmation."""
    if not confirm:
        return {
            "error": "Confirmation required. Set confirm=True to proceed."
        }
    
    result = await db.contacts.delete_many({
        "user_id": ctx.user_id
    })
    
    return {
        "deleted_count": result.deleted_count,
        "message": "All contacts deleted"
    }
```

## 🔒 Security Best Practices

### 1. Always Scope to User

```python
# ✅ Good - User can only access their data
async def get_contacts(ctx: ToolContext):
    return await db.contacts.find({"user_id": ctx.user_id})

# ❌ Bad - User can access all data
async def get_contacts():
    return await db.contacts.find({})
```

### 2. Validate Input

```python
from pydantic import BaseModel, EmailStr, validator


class ContactInput(BaseModel):
    name: str
    email: EmailStr  # ✅ Validates email format
    phone: str
    

    @validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^\+?1?\d{10,15}$", v):
            raise ValueError("Invalid phone format")
        return v


@tool(name="create_contact")
async def create_contact(
    contact: ContactInput,  # ✅ Pydantic validates
    ctx: ToolContext
):
    ...
```

### 3. Handle Errors Gracefully

```python

@tool(name="external_api_call")
async def external_api_call(url: str, ctx: ToolContext):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    except httpx.TimeoutException:
        return {"error": "API request timed out"}
    
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}"}
    
    except Exception as e:
        # ✅ Log but don't expose internals
        logger.error(f"Tool error: {e}", exc_info=True)
        return {"error": "Internal error occurred"}
```

### 4. Rate Limiting

```python
from app.services.rate_limiter import check_rate_limit


@tool(name="send_email")
async def send_email(to: str, subject: str, body: str, ctx: ToolContext):
    # ✅ Rate limit per user
    await check_rate_limit(
        user_id=ctx.user_id,
        action="send_email",
        max_requests=10,
        period_seconds=3600  # 10 emails per hour
    )
    
    # Send email...
```

## 🧪 Testing Tools

### Unit Test

```python
# backend/tests/test_tools.py
import pytest
from app.tools.weather_tools import get_weather
from app.services.memory import ToolContext


@pytest.mark.asyncio
async def test_get_weather():
    ctx = ToolContext(
        user_id=1,
        agent_id="test_agent",
        conversation_id="test_conv",
        metadata={}
    )
    
    result = await get_weather(
        city="San Francisco",
        units="celsius",
        ctx=ctx
    )
    
    assert "temperature" in result
    assert "conditions" in result
    assert result["city"] == "San Francisco"
```

### Integration Test with Agent

```python

@pytest.mark.asyncio
async def test_agent_uses_tool():
    # Create agent with tool
    agent = await create_agent(
        name="test_agent",
        tools=["get_weather"]
    )
    
    # Run agent
    result = await run_agent(agent.id, {
        "message": "What's the weather in Paris?"
    })
    

    # Verify tool was called
    assert any(tc.name == "get_weather" for tc in result.tool_calls)
    assert "Paris" in result.response
```

## 📊 Tool Registry

### List All Tools

```python
from app.tools.registry import get_all_tools

tools = get_all_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")
```

### Get Tool by Name

```python
from app.tools.registry import get_tool

tool = get_tool("get_weather")

print(tool.signature)
```

### Tool Metadata

```python
{
    "name": "get_weather",
    "description": "Get current weather...",
    "parameters": {
        "city": {"type": "string", "required": true},
        "units": {"type": "string", "default": "celsius"}
    },
    "category": "external_api",
    "requires_auth": false,
    "dangerous": false
}
```

## 🔌 Integration Examples

### Database Tool

```python

@tool(name="execute_sql", dangerous=True)
async def execute_sql(query: str, ctx: ToolContext) -> dict:
    """Execute read-only SQL query."""
    # ✅ Restrict to SELECT only
    if not query.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries allowed"}
    
    # ✅ Row-level security
    query = f"""
        SELECT * FROM ({query}) subquery
        WHERE user_id = {ctx.user_id}
    """
    
    result = await db.execute(query)
    return {"rows": result.fetchall(), "count": len(result)}
```

### File Upload Tool

```python

@tool(name="upload_file")
async def upload_file(
    file_content: bytes,
    filename: str,
    ctx: ToolContext
) -> dict:
    """Upload file to user's storage."""
    # Store in GridFS
    file_id = await gridfs.put(
        file_content,
        filename=filename,
        user_id=ctx.user_id,
        uploaded_at=datetime.utcnow()
    )
    
    return {
        "file_id": str(file_id),
        "url": f"/api/files/{file_id}",
        "size": len(file_content)
    }
```

### Webhook Tool

```python

@tool(name="trigger_webhook")
async def trigger_webhook(
    url: str,
    payload: dict,
    ctx: ToolContext
) -> dict:

    """Send webhook with RCF signature."""

    from app.services.rcf_service import sign_payload
    

    # Sign payload

    signature = sign_payload(
        payload=json.dumps(payload),
        secret=settings.RCF_SECRET_KEY,
        timestamp=int(time.time())
    )
    
    # Send webhook
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={

                "X-RCF-Signature": signature,
                "X-User-ID": str(ctx.user_id)
            }
        )
    
    return {"status": response.status_code}
```

## 🚨 Troubleshooting

### Tool Not Available to Agent
- Check tool is in agent's `tools` list

- Verify tool file is in `backend/app/tools/`
- Check `@tool` decorator is applied

### Tool Execution Fails

- Check tool signature matches LLM's call

- Verify required parameters are provided
- Review error logs in `agent_messages` table

### Permission Errors
- Ensure `ctx.user_id` is used for scoping
- Check `requires_auth=True` if needed

- Verify user has necessary integrations connected

## 🔗 Related

- [Agent Development Guide](./AGENT_DEVELOPMENT.md)
- [Memory System](../ARCHITECTURE.md#memory)
- [API Reference](../API.md)
- [Tool Base & Registry Code](../../backend/app/tools/base.py)

---

**Questions?** Open an issue on [GitHub](https://github.com/aliyevaladddin/AladdinAI/issues)
