// NOTICE: This file is protected under RCF-PL
# AladdinAI Documentation

Comprehensive documentation for the AladdinAI multi-agent AI system.

## 📚 Contents

### API Documentation
- **[API Reference](./API.md)** - Auto-generated REST API documentation
- **[OpenAPI Schema](./openapi.json)** - Machine-readable API specification
- **Interactive Docs** - Available at `http://localhost:8000/docs` (Swagger UI)
- **ReDoc** - Available at `http://localhost:8000/redoc` (alternative UI)

### Architecture
- **[Architecture Decision Records](./adr/)** - Important architectural decisions and their context
- **[System Overview](./architecture/OVERVIEW.md)** - High-level system architecture
- **[Data Flow](./architecture/DATAFLOW.md)** - How data flows through the system

### Guides
- **[Getting Started](../README.md)** - Quick start guide
- **[Agent Development](./guides/AGENT_DEVELOPMENT.md)** - Creating custom agents
- **[Tool Development](./guides/TOOL_DEVELOPMENT.md)** - Adding new tools
- **[Memory System](./guides/MEMORY.md)** - Understanding the memory architecture
- **[Self-Forging](./guides/SELF_FORGING.md)** - Model fine-tuning from traces

### Deployment
- **[Docker Deployment](./deployment/DOCKER.md)** - Production Docker setup
- **[Render.com](./deployment/RENDER.md)** - Deploy to Render.com
- **[Environment Variables](./deployment/ENV.md)** - Configuration reference

## 🔄 Auto-Generated Documentation

API documentation is automatically generated and updated:
- ✅ On every push to `main` branch
- ✅ When backend code changes
- ✅ Manual trigger via GitHub Actions

## 🛠️ Local Development

Generate docs locally:

```bash
# Generate OpenAPI schema
cd backend
python scripts/generate_openapi.py

# View interactive docs
# Start the backend and visit:
# http://localhost:8000/docs
```

## 📝 Contributing

When adding new API endpoints:
1. Add proper docstrings to route functions
2. Define Pydantic models for request/response
3. Add tags to categorize endpoints
4. Documentation will be auto-generated on push

Example:
```python
// [RCF:PROTECTED]
@router.post("/agents", tags=["agents"], response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    """
    Create a new AI agent.
    
    - **name**: Unique agent identifier
    - **model**: LLM model to use
    - **system_prompt**: Initial instructions
    """
    ...
```

## 📖 Architecture Decision Records (ADR)

We document important architectural decisions in ADR format. See [adr/](./adr/) directory.

To create a new ADR:
```bash
cd docs/adr
cp template.md NNNN-title-of-decision.md
# Edit the file with your decision
```

## 🔗 External Resources

- [GitHub Repository](https://github.com/aliyevaladddin/AladdinAI)
- [RCF Protocol](https://github.com/rcf-protocol)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

---

**Last Updated**: Auto-generated on every push to main
