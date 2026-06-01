# Telegram → Agent → Email Integration

Complete setup guide for sending emails through agents from Telegram.

## What's Implemented

✅ **send_email tool** — agents can send emails via SMTP  
✅ **Telegram integration** — receive messages via long-polling  
✅ **Smart Routing** — automatic agent selection based on message content  
✅ **Email accounts** — connect SMTP/IMAP accounts  

## Step 1: Connect Email Account

1. Open `/dashboard/settings?tab=email` (or via Settings → Email)
2. Click "Add Email Account"
3. Fill in the details:
   - **Email**: your email address
   - **Provider**: select `imap` (for Gmail/Outlook)
   - **SMTP Host**: `smtp.gmail.com` (for Gmail)
   - **SMTP Port**: `587`
   - **IMAP Host**: `imap.gmail.com`
   - **IMAP Port**: `993`
   - **Password**: app password (not your main password!)

### For Gmail:
1. Enable 2FA in your Google Account
2. Create an App Password: https://myaccount.google.com/apppasswords
3. Use this password in the settings

4. Click "Test Connection" — status should become "Connected"

## Step 2: Create Agent with Email Tool

1. Open `/dashboard/agents`
2. Create a new agent or edit an existing one
3. In the **Tools** section, enable:
   - ✅ `send_email` — send emails
   - ✅ `analyze_image` (optional) — if you need to work with images
4. In **System Prompt**, add instructions:
   ```
   You are an email assistant. When the user asks you to send an email,
   use the send_email tool with the recipient address, subject, and body.
   
   Example:
   User: "Send email to john@example.com with subject 'Meeting' and say hello"
   You: [use send_email tool with to="john@example.com", subject="Meeting", body="Hello!"]
   ```
5. Save the agent

## Step 3: Connect Telegram Channel

1. Create a bot via [@BotFather](https://t.me/BotFather):
   - Send `/newbot`
   - Choose a name and username
   - Get the **Bot Token** (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

2. In AladdinAI, open `/dashboard/channels`
3. Click "Add Channel" → select **Telegram**
4. Paste the Bot Token
5. Select **Default Agent** — the agent from Step 2
6. Save — status should become "Connected"

## Step 4: Configure Smart Routing (Optional)

If you want different messages to go to different agents:

1. Open `/dashboard/settings?tab=routing`
2. Create a rule:
   - **Type**: `keyword` or `llm_classifier`
   - **Keywords**: `["email", "send", "write"]` — if message contains these words
   - **Agent**: select the agent with email tool
   - **Fallback**: default agent for other messages

## Step 5: Testing

1. Open your bot in Telegram
2. Send a message:
   ```
   Send an email to test@example.com with subject "Test" and body "Hello from Telegram!"
   ```

3. The agent should:
   - Recognize the intent to send an email
   - Call the `send_email` tool
   - Send the email via your SMTP account
   - Reply in Telegram that the email was sent

## Checking Logs

If something doesn't work, check backend logs:

```bash
docker logs aladdinai-backend-1 -f | grep -E "orchestrator|send_email|telegram"
```

Look for:
- `orchestrator: incoming telegram sender=...` — message received
- `orchestrator: running agent ...` — agent started
- `send_email tool called` — tool invoked
- `send_email failed` — send error

## Troubleshooting

### Email not sending
- Check that email account status is "Connected"
- Verify you're using App Password, not main password
- Check SMTP settings (host, port)
- Check logs: `grep "send_email" backend.log`

### Agent not calling send_email tool
- Verify the tool is enabled in agent settings
- Check System Prompt — add explicit instruction to use send_email
- Try a more explicit command: "Use send_email tool to send email to..."

### Telegram not receiving messages
- Check Bot Token
- Verify the bot is not blocked
- Check logs: `grep "telegram-poll" backend.log`

## Example Commands

```
Send an email to john@example.com with subject "Meeting tomorrow" and text "Let's meet at 10am"

Send an email to support@company.com asking about the order status

Write an email to boss@work.com with subject "Report" and attach the report
```

## What's Next?

- Add multiple email accounts for different purposes
- Configure routing rules for automatic agent selection
- Add other tools (calendar, CRM, etc.)
- Connect WhatsApp/SMS channels
