// NOTICE: This file is protected under RCF-PL
# Interactive Setup Wizard ✨

Added interactive configuration wizard to CLI for easier onboarding.

## 🎉 What's New

### Automatic Wizard on Install
When you run `npx aladdin-ai`, the setup wizard automatically starts after services are up:

```bash
npx aladdin-ai
# After services start...

✨ AladdinAI Setup Wizard

Configure your AI workspace in a few steps.

? Run setup wizard? (Y/n)
```

### Manual Wizard
Run the wizard anytime:

```bash
cd aladdin-ai
npx aladdin-ai setup
```

## 📋 Wizard Steps

### 1. 📡 LLM Provider Setup
Select which providers to configure:

```
? Select providers (Space to select, Enter to continue):
  ● NVIDIA NIM (Recommended) - Free tier, 70B+ models
    OpenAI - GPT-4, GPT-3.5 Turbo
    Anthropic - Claude 3.5 Sonnet, Opus
    Local (BentoML) - Self-hosted models
```

For each provider:
- Prompts for API keys
- Shows where to get keys
- Updates `.env` automatically

**NVIDIA NIM** (Recommended):
- Free tier available
- 70B+ parameter models
- Best performance
- Get key: https://build.nvidia.com

**OpenAI**:
- GPT-4, GPT-3.5 Turbo
- Get key: https://platform.openai.com/api-keys

**Anthropic**:
- Claude 3.5 Sonnet, Opus, Haiku
- Get key: https://console.anthropic.com/settings/keys

**Local (BentoML)**:
- Self-hosted models
- No API key needed
- Full control

### 2. 🗄️ MongoDB Atlas Setup
Configure vector memory storage:

```
? Configure MongoDB Atlas now? (Y/n)

MongoDB Atlas is used for vector memory and media storage.

Get connection string from:
1. https://cloud.mongodb.com
2. Connect → Drivers → Connection string

? MongoDB connection string: mongodb+srv://...
```

**Skip MongoDB?**
- Memory features disabled
- Can configure later
- Get free $500 credits: https://www.mongodb.com/startups

### 3. 🤖 Create Your First Agent
Choose from pre-built templates:

```
? Choose agent template:
  💬 General Assistant - Helpful chatbot for general tasks
  📊 CRM Assistant - Sales and contact management
  📧 Email Assistant - Email drafting and responses
  🔍 Research Assistant - Web search and analysis

? Agent name: my_assistant
```

**Templates included**:

**General Assistant**
- Helpful chatbot
- No tools
- Good starting point

**CRM Assistant**
- Contact management
- Deal tracking
- Activity logging
- Tools: search_contacts, create_contact, create_deal

**Email Assistant**
- Email drafting
- Professional tone
- Tools: send_email, search_contacts

**Research Assistant**
- Web search
- Analysis
- Tools: web_search, analyze_image

## 🔧 What It Does

1. **Updates `.env` file** with your configuration
2. **Saves agent config** to `.aladdin-setup.json`
3. **Ready to use** - agents created on next login

## 📝 Configuration File

After wizard, `.env` updated:

```bash
# Providers
NIM_API_KEY=nvapi-xxxxx
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_MODEL=meta/llama-3.1-70b-instruct

# MongoDB
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/

# Or OpenAI
OPENAI_API_KEY=sk-xxxxx

# Or Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

Agent config saved to `.aladdin-setup.json`:

```json
{
  "agentConfig": {
    "name": "my_assistant",
    "display_name": "General Assistant",
    "system_prompt": "You are a helpful AI assistant...",
    "model": "meta/llama-3.1-70b-instruct",
    "memory_enabled": true,
    "tools": []
  }
}
```

## 🚀 Usage Examples

### First-time Setup
```bash
npx aladdin-ai
# Follow prompts...
# ✓ Services running
# ✨ Setup wizard runs automatically
```

### Re-run Wizard
```bash
cd aladdin-ai
npx aladdin-ai setup
# Configure additional providers
# Create more agents
```

### Skip Wizard on Install
```bash
npx aladdin-ai --yes
# Skips all prompts including wizard
```

### Manual Configuration
Edit `.env` directly if you prefer:
```bash
cd aladdin-ai
nano .env
npx aladdin-ai restart
```

## 🎯 Benefits

### Before (Old Way)
1. `npx aladdin-ai`
2. Open http://localhost:3000
3. Navigate to Settings → Providers
4. Add API key manually
5. Navigate to Agents
6. Create agent from scratch
7. Configure tools, memory, etc.

**8 steps, 5+ minutes**

### After (With Wizard)
1. `npx aladdin-ai`
2. Answer 3-4 questions
3. Done!

**2 steps, 1 minute**

## 🔐 Security

- API keys stored in `.env` (not committed)
- Secure random secrets generated
- No keys sent anywhere
- All configuration local

## 🆘 Troubleshooting

### Wizard doesn't start
```bash
# Manually run:
cd aladdin-ai
npx aladdin-ai setup
```

### Wrong API key entered
```bash
# Edit .env:
nano .env
# Change NIM_API_KEY=...
npx aladdin-ai restart backend
```

### Want to add more providers
```bash
# Run wizard again:
npx aladdin-ai setup
# Select additional providers
```

### Agent not appearing
```bash
# Check config file:
cat .aladdin-setup.json
# Restart services:
npx aladdin-ai restart
# Check logs:
npx aladdin-ai logs backend
```

## 📚 Next Steps

After wizard completes:

1. **Open dashboard**: http://localhost:3000
2. **Register account**: First user auto-admin
3. **Test your agent**: Go to Chat
4. **Explore features**: CRM, Channels, Settings

## 🔗 Related Commands

```bash
npx aladdin-ai setup     # Run wizard
npx aladdin-ai doctor    # Diagnose issues
npx aladdin-ai logs      # View logs
npx aladdin-ai restart   # Restart services
```

---

**Wizard makes AladdinAI setup 5x faster! 🚀**
