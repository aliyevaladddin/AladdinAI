// NOTICE: This file is protected under RCF-PL
# Agent Delegation System 🤝

Multi-agent coordination system allowing agents to delegate tasks to specialized sub-agents.

## 🎯 What is Agent Delegation?

Agent delegation enables:
- **Complex task decomposition** - Break large tasks into specialized subtasks
- **Parallel execution** - Run multiple agents simultaneously
- **Specialized expertise** - Leverage different agents for different skills
- **Hierarchical structures** - Coordinator → Workers pattern

## 🚀 Quick Start

### 1. Single Delegation

```python
# Agent A delegates to Agent B
result = await delegate_to_agent(
    parent_agent_id="research_coordinator",
    target_agent_id="web_searcher",
    task="Find the latest AI research papers on multi-agent systems",
    context={"max_results": 10},
    user_id=user.id,
    db=db
)

print(result.response)  # Agent B's findings
```

### 2. Parallel Delegation

```python
# Research coordinator delegates to 3 specialists simultaneously
delegations = [
    {
        "target_agent_id": "web_searcher",
        "task": "Search for competitor pricing"
    },
    {
        "target_agent_id": "analyst",
        "task": "Analyze market trends"
    },
    {
        "target_agent_id": "summarizer",
        "task": "Summarize recent news"
    }
]

results = await delegate_parallel(
    parent_agent_id="coordinator",
    delegations=delegations,
    user_id=user.id,
    db=db
)

# All 3 agents run at once, results come back together
for result in results:
    print(f"{result.agent_name}: {result.response}")
```

### 3. Sequential Delegation (Pipeline)

```python
# Pass results from one agent to the next
delegations = [
    {
        "target_agent_id": "researcher",
        "task": "Research topic X"
    },
    {
        "target_agent_id": "analyst",
        "task": "Analyze the findings"  # Gets researcher's results
    },
    {
        "target_agent_id": "writer",
        "task": "Write a report"  # Gets analyzer's results
    }
]

results = await delegate_sequential(
    parent_agent_id="coordinator",
    delegations=delegations,
    user_id=user.id,
    db=db,
    pass_context=True  # Each agent gets previous results
)
```

## 🛠️ Tools for Agents

Agents can use delegation via built-in tools:

### Tool: `delegate_to_agent`

Agent calls this tool to delegate a single task:

```json
{
  "tool": "delegate_to_agent",
  "args": {
    "target_agent_name": "crm_specialist",
    "task": "Find all contacts at Acme Corp and create a deal"
  }
}
```

LLM decides when to delegate based on:
- Task complexity
- Specialized skills needed
- User request pattern

### Tool: `delegate_parallel`

Delegate multiple tasks at once:

```json
{
  "tool": "delegate_parallel",
  "args": {
    "delegations": [
      {
        "agent_name": "email_agent",
        "task": "Draft welcome email"
      },
      {
        "agent_name": "crm_agent",
        "task": "Create contact record"
      },
      {
        "agent_name": "calendar_agent",
        "task": "Schedule follow-up"
      }
    ]
  }
}
```

## 📚 Use Cases

### Use Case 1: Research Team

**Coordinator Agent** delegates to specialists:

```
User: "Research our competitor's product strategy"

Coordinator Agent:
  ├─> Web Researcher: "Find competitor websites and docs"
  ├─> Social Media Analyzer: "Analyze their social presence"
  ├─> Price Tracker: "Track their pricing changes"
  └─> Report Writer: "Compile everything into a report"
```

### Use Case 2: Customer Onboarding

**Onboarding Agent** orchestrates process:

```
User: "Onboard new customer: john@acme.com"

Onboarding Agent:
  1. Email Agent: "Send welcome email"
  2. CRM Agent: "Create contact + deal"
  3. Calendar Agent: "Schedule kickoff call"
  4. Slack Agent: "Notify team in #sales"
```

### Use Case 3: Content Pipeline

**Content Manager** coordinates workflow:

```
User: "Create a blog post about AI trends"

Content Manager:
  1. Researcher → "Research AI trends"
  2. Outline Writer → "Create outline" (uses research)
  3. Draft Writer → "Write first draft" (uses outline)
  4. Editor → "Edit and polish" (uses draft)
  5. SEO Optimizer → "Optimize for SEO"
```

### Use Case 4: Data Analysis Pipeline

**Analytics Coordinator**:

```
User: "Analyze Q4 sales data"

Analytics Coordinator:
  ├─ (Parallel) SQL Analyst: "Query sales data"
  ├─ (Parallel) Trend Analyzer: "Identify patterns"
  ├─ (Parallel) Forecast Agent: "Predict Q1"
  └─ (Sequential) Report Agent: "Combine into executive summary"
```

## 🏗️ Architecture Patterns

### Pattern 1: Fan-Out / Fan-In

Coordinator distributes work, collects results:

```
       Coordinator
       /    |    \
      /     |     \
  Agent1 Agent2 Agent3
      \     |     /
       \    |    /
       Coordinator
      (aggregates)
```

### Pattern 2: Pipeline

Sequential processing with context passing:

```
Agent1 → Agent2 → Agent3 → Agent4
(each gets previous output)
```

### Pattern 3: Hierarchical

Multi-level delegation:

```
        CEO Agent
        /       \
   Manager1   Manager2
    /    \      /    \
  W1    W2    W3    W4
```

### Pattern 4: Dynamic Routing

Coordinator decides which agents to use:

```python
if task_type == "research":
    delegate_to("researcher")
elif task_type == "email":
    delegate_to("email_agent")
else:
    delegate_parallel([agent1, agent2, agent3])
```

## ⚡ Performance Considerations

### Parallel vs Sequential

**Use Parallel when**:
- Tasks are independent
- Need results fast
- No dependencies between tasks

**Use Sequential when**:
- Tasks depend on previous results
- Need to pass context forward
- Order matters

### Timeout Handling

```python
try:
    result = await asyncio.wait_for(
        delegate_to_agent(...),
        timeout=30.0  # 30 seconds
    )
except asyncio.TimeoutError:
    # Handle timeout
    pass
```

### Error Recovery

```python
results = await delegate_parallel(...)

# Check for failures
failed = [r for r in results if not r.success]
if failed:
    # Retry failed delegations
    for result in failed:
        await retry_delegation(result.agent_id, ...)
```

## 🔒 Security & Permissions

### User Scoping

All delegations are user-scoped:

```python
# Agent can only delegate to agents owned by same user
delegate_to_agent(
    target_agent_id="other_agent",
    user_id=current_user.id  # ← Enforced
)
```

### Delegation Limits

Prevent infinite loops:

```python
MAX_DELEGATION_DEPTH = 3  # Max 3 levels deep

if delegation_depth >= MAX_DELEGATION_DEPTH:
    raise AgentDelegationError("Max delegation depth reached")
```

### Tool Permissions

Sub-agents inherit parent's tool restrictions:

```python
if tool not in parent_agent.allowed_tools:
    # Sub-agent can't use this tool either
    raise PermissionError(...)
```

## 📊 Monitoring & Logging

### Delegation Tracking

```python
# Each delegation logged
logger.info(
    f"Agent {parent_id} → {target_id}: {task}",
    extra={
        "delegation_id": delegation_id,
        "parent_agent": parent_id,
        "target_agent": target_id,
        "user_id": user_id
    }
)
```

### Result Aggregation

```python
summary = format_delegation_summary(results)
# Output:
# ✓ researcher: Found 10 papers on multi-agent systems...
# ✓ analyst: Key trends identified: collaborative AI...
# ✗ summarizer: Error: Rate limit exceeded
```

## 🧪 Testing

### Test Single Delegation

```python
async def test_delegation():
    result = await delegate_to_agent(
        parent_agent_id="test_parent",
        target_agent_id="test_target",
        task="Test task",
        context={},
        user_id=1,
        db=db
    )
    
    assert result.success
    assert "response" in result.response
```

### Test Parallel Execution

```python
async def test_parallel():
    start = time.time()
    
    results = await delegate_parallel(
        parent_agent_id="test_parent",
        delegations=[...],  # 3 delegations
        user_id=1,
        db=db
    )
    
    duration = time.time() - start
    
    # Should be faster than sequential
    assert duration < 10  # 3 tasks in < 10 seconds
    assert len(results) == 3
```

## 🚨 Common Pitfalls

### 1. Circular Delegation

```python
# ❌ Bad: Agent A → Agent B → Agent A (infinite loop)
# ✅ Good: Track delegation chain, prevent cycles
```

### 2. No Error Handling

```python
# ❌ Bad: Assume all delegations succeed
# ✅ Good: Check result.success, handle errors
```

### 3. Context Explosion

```python
# ❌ Bad: Pass entire context to every sub-agent
# ✅ Good: Pass only relevant context subset
```

## 📖 API Reference

### `delegate_to_agent()`

```python
async def delegate_to_agent(
    parent_agent_id: str,
    target_agent_id: str,
    task: str,
    context: Optional[Dict[str, Any]],
    user_id: int,
    db: AsyncSession
) -> DelegationResult
```

### `delegate_parallel()`

```python
async def delegate_parallel(
    parent_agent_id: str,
    delegations: List[Dict[str, Any]],
    user_id: int,
    db: AsyncSession
) -> List[DelegationResult]
```

### `delegate_sequential()`

```python
async def delegate_sequential(
    parent_agent_id: str,
    delegations: List[Dict[str, Any]],
    user_id: int,
    db: AsyncSession,
    pass_context: bool = True
) -> List[DelegationResult]
```

### `DelegationResult`

```python

class DelegationResult:
    agent_id: str
    agent_name: str
    success: bool
    response: str
    metadata: Dict[str, Any]
    tool_calls: List[Dict[str, Any]]
    error: Optional[str]
    completed_at: datetime
```

## 🔗 Related

- [Agent Development Guide](./AGENT_DEVELOPMENT.md)
- [Tool Development Guide](./TOOL_DEVELOPMENT.md)
- [Memory System](./MEMORY.md)
- [ADR-0001: Self-Forging](../adr/0001-self-forging-training.md)

---

**Agent delegation enables true multi-agent orchestration! 🚀**
