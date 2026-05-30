# AladdinAI Cloudflare Functions

Serverless functions for AladdinAI GitHub bot, deployed on Cloudflare Pages.

## Structure

```
.github/functions/
└── api/
    └── webhooks/
        └── github.js    # GitHub App webhook handler
```

## Deployment

### 1. Deploy to Cloudflare Pages

**Option A: Connect GitHub repo**
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) → Pages
2. Create new project → Connect to Git
3. Select `aliyevaladddin/AladdinAI` repository
4. Build settings:
   - Framework preset: `None`
   - Build command: (leave empty)
   - Build output directory: `/`
5. Deploy

**Option B: Direct upload**
```bash
npm install -g wrangler
wrangler login
wrangler pages deploy . --project-name=aladdinai
```

### 2. Configure Environment Variables

In Cloudflare Pages → Settings → Environment variables, add:

| Variable | Description | Required |
|----------|-------------|----------|
| `WEBHOOK_SECRET` | GitHub App webhook secret | ✅ Yes |
| `GITHUB_TOKEN` | GitHub App installation token or PAT | ✅ Yes |

**Getting GitHub App Token:**

Option 1 - Installation Token (recommended):
```bash
# Generate JWT from GitHub App private key
# Then exchange for installation token
# See: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app
```

Option 2 - Personal Access Token:
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Scopes: `repo`, `write:discussion`

### 3. Update GitHub App Webhook URL

1. Go to GitHub App settings: https://github.com/settings/apps
2. Select your app (AladdinAI[bot] or NVIDIA Code Review[bot])
3. Update Webhook URL to:
   ```
   https://aliyev.site/api/webhooks/github
   ```
   Or your custom domain:
   ```
   https://your-domain.pages.dev/api/webhooks/github
   ```
4. Webhook secret: use the same value as `WEBHOOK_SECRET` env var

### 4. Subscribe to Events

In GitHub App settings → Permissions & events → Subscribe to events, enable:

- ✅ Issues
- ✅ Issue comments
- ✅ Pull requests
- ✅ Pull request reviews
- ✅ Pull request review comments

## Testing

### Test webhook locally with Wrangler

```bash
cd /workspaces/AladdinAI
wrangler pages dev . --port 8788

# In another terminal, send test webhook
curl -X POST http://localhost:8788/api/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -H "X-Hub-Signature-256: sha256=test" \
  -d '{"zen": "Design for failure."}'
```

### Test on production

```bash
# Trigger a test event from GitHub App settings
# Or create a test issue/PR in your repo
```

## Bot Behavior

### Pull Requests
- **Opened**: Welcome message with PR stats (files changed, additions, deletions)
- **Closed (merged)**: Celebration message
- **Closed (not merged)**: Acknowledgment message

### Issues
- **Opened**: Acknowledgment and tracking confirmation
- **Closed**: Closure confirmation

### Comments
- **@AladdinAI mention**: Bot responds to direct mentions

## Monitoring

Check webhook deliveries in GitHub App settings:
1. Go to your GitHub App
2. Advanced → Recent Deliveries
3. View request/response for each webhook

Check Cloudflare logs:
1. Cloudflare Dashboard → Pages → your project
2. Functions → Logs

## Troubleshooting

**Bot not responding:**
1. Check webhook URL is correct in GitHub App settings
2. Verify `WEBHOOK_SECRET` matches in both places
3. Check Cloudflare Functions logs for errors
4. Verify events are subscribed in GitHub App settings

**Signature verification failed:**
- Webhook secret mismatch between GitHub App and Cloudflare env var
- Check Recent Deliveries in GitHub App for error details

**GitHub API errors:**
- Check `GITHUB_TOKEN` is valid and has correct permissions
- Token might be expired (installation tokens expire after 1 hour)

## Architecture

```
GitHub Event
    ↓
GitHub Webhook
    ↓
Cloudflare Pages Function (aliyev.site/api/webhooks/github)
    ↓
Verify signature (HMAC-SHA256)
    ↓
Route to handler (PR/Issue/Comment)
    ↓
Generate response
    ↓
Post comment via GitHub API
```

## Security

- ✅ Webhook signature verification (HMAC-SHA256)
- ✅ CORS headers configured
- ✅ Secrets stored in Cloudflare environment variables (encrypted at rest)
- ✅ No secrets in code or git

## Cost

Cloudflare Pages Functions:
- **Free tier**: 100,000 requests/day
- **Paid**: $0.50 per million requests after free tier

For typical GitHub bot usage (< 1000 events/day), this stays **free forever**.
