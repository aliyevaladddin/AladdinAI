// NOTICE: This file is protected under RCF-PL
# 📚 AladdinAI Documentation

**Version**: 2.1.5  
**Last Updated**: 2026-06-06

Welcome to the complete documentation for AladdinAI - a self-hosted multi-agent AI workspace.

## 🚀 Getting Started

- **[Quick Start](../README.md)** - Get AladdinAI running in 5 minutes
- **[Installation](../README.md#installation)** - Detailed setup instructions
- **[CLI Usage](../cli/README.md)** - Using `npx aladdin-ai`

## 📖 Documentation Index

### 📘 API Reference
- **[API Documentation](./API.md)** - Auto-generated REST API reference
- **[OpenAPI Schema](./openapi.json)** - Machine-readable specification
- **[Interactive Docs](http://localhost:8000/docs)** - Swagger UI (when running)
- **[ReDoc](http://localhost:8000/redoc)** - Alternative documentation UI

### 🏗️ Architecture

- **[Architecture Decision Records](./adr/)** - Important design decisions
  - [ADR-0001: Self-Forging Training](./adr/0001-self-forging-training.md)
  - [ADR-0002: MongoDB vs Postgres](./adr/0002-mongodb-vs-postgres.md)
  - [ADR-0003: RCF Webhook Auth](./adr/0003-rcf-webhook-auth.md)

### 📚 Developer Guides
- **[Agent Development](./guides/AGENT_DEVELOPMENT.md)** - Creating custom AI agents
- **[Tool Development](./guides/TOOL_DEVELOPMENT.md)** - Building agent tools
- **[Memory System](./guides/MEMORY.md)** - Understanding memory architecture *(coming soon)*
- **[Self-Forging](./guides/SELF_FORGING.md)** - Model fine-tuning from traces *(coming soon)*

### 🚢 Deployment
- **[Docker Deployment](./deployment/DOCKER.md)** - Production setup *(coming soon)*
- **[Render.com](./deployment/RENDER.md)** - Cloud deployment *(coming soon)*
- **[Environment Variables](./deployment/ENV.md)** - Configuration reference *(coming soon)*

## 🎯 Quick Links by Role

### 👨‍💻 Backend Developer
1. [API Reference](./API.md)
2. [Tool Development Guide](./guides/TOOL_DEVELOPMENT.md)
3. [ADR-0002: Database Strategy](./adr/0002-mongodb-vs-postgres.md)

### 🤖 AI Engineer
1. [Agent Development Guide](./guides/AGENT_DEVELOPMENT.md)
2. [ADR-0001: Self-Forging](./adr/0001-self-forging-training.md)
3. [Memory System](./guides/MEMORY.md) *(coming soon)*

### 🔐 Security Engineer
1. [ADR-0003: RCF Protocol](./adr/0003-rcf-webhook-auth.md)
2. [Safety Gates Documentation](./guides/AGENT_DEVELOPMENT.md#safety-and-gates)

### 🚀 DevOps Engineer
1. [Docker Deployment](./deployment/DOCKER.md) *(coming soon)*
2. [Environment Variables](./deployment/ENV.md) *(coming soon)*

## 🛠️ Features Overview

### ✅ Implemented
- 🤖 **Multi-Agent System** - Create and orchestrate specialized AI agents
- 🧠 **Persistent Memory** - Vector-based memory with per-agent isolation
- 🛠️ **Tool Execution** - Extensible tool registry with 20+ built-in tools
- 📊 **CRM Integration** - Full contact, deal, and activity management
- 🔐 **Safety First** - PII detection, content filtering, audit logging

- 🔗 **RCF Protocol** - Cryptographic webhook signing
- 🎨 **Modern UI** - Next.js dashboard with real-time updates
- 📦 **CLI Tool** - `npx aladdin-ai` for quick setup
- 🐙 **GitHub Bots** - 2 automated bots for code review and issues
- 🗄️ **GridFS Media** - MongoDB storage for files and images
- 🧪 **Self-Forging** - Train custom models from agent traces

### 🚧 In Progress
- 📈 **Grafana Dashboard** - Metrics and monitoring
- 🔄 **Continuous Training** - Automated model fine-tuning
- 📱 **Mobile App** - iOS and Android clients

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│  Dashboard │ Agents │ Chat │ CRM │ Settings         │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────────┐
│                 Backend (FastAPI)                    │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Orchestrator │  │ Agent Runner │  │ Tools     │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Memory       │  │ Safety       │  │ RCF       │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────┬──────────────────────────────────┬───────┘
          │                                  │
    ┌─────▼────────┐                  ┌─────▼──────┐
    │   Postgres   │                  │  MongoDB   │
    │              │                  │   Atlas    │
    │ • Chat msgs  │                  │ • Vectors  │
    │ • CRM data   │                  │ • GridFS   │
    │ • Traces     │                  │ • Memory   │
    └──────────────┘                  └────────────┘
```

## 🔄 Auto-Generated Documentation

Documentation is automatically updated:
- ✅ **On every push to main** - API docs regenerated
- ✅ **On backend changes** - OpenAPI schema updated
- ✅ **Manual trigger** - Via GitHub Actions workflow

Generate locally:
```bash
cd backend
python scripts/generate_openapi.py
```

## 📝 Contributing to Docs

### Adding API Documentation
When adding new endpoints, include:
```python

@router.post("/endpoint", tags=["category"])
async def endpoint(data: RequestModel) -> ResponseModel:
    """
    Brief description.
    
    Detailed explanation of what this does.
    
    - **param1**: What it means
    - **param2**: What it means
    """
```

### Creating an ADR
```bash
cd docs/adr
cp template.md NNNN-decision-title.md
# Edit with your decision
# Update README.md index
```

### Writing a Guide
1. Create in `docs/guides/`
2. Follow existing structure (Quick Start → Details → Examples)
3. Include code samples
4. Add to this index

## 🔗 External Resources

- **[GitHub Repository](https://github.com/aliyevaladddin/AladdinAI)**
- **[RCF Protocol](https://github.com/rcf-protocol)**
- **[npm Package](https://www.npmjs.com/package/aladdin-ai)**
- **[Docker Hub](https://github.com/aliyevaladddin/AladdinAI/pkgs/container/aladdinai)**

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/aliyevaladddin/AladdinAI/issues)
- **Email**: aladdin@aliyev.site
- **Discussions**: [GitHub Discussions](https://github.com/aliyevaladddin/AladdinAI/discussions)

## 📄 License

Apache 2.0 - See [LICENSE](../LICENSE)

---

**Made with 🧞 by the AladdinAI team**
