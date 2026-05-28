# Creating a GitHub App for Code Review Bot

## Steps:

1. Go to GitHub Settings → Developer settings → GitHub Apps → New GitHub App

2. Fill in:
   - **Name**: AladdinAI Code Review Bot
   - **Homepage URL**: https://github.com/aliyevaladddin/AladdinAI
   - **Webhook**: Uncheck "Active" (we use Actions, not webhooks)
   
3. Permissions:
   - Repository permissions:
     - Pull requests: Read & write
     - Contents: Read-only
   
4. Subscribe to events: (none needed for Actions-based bot)

5. Create the app → Generate private key → Download .pem file

6. Install the app on your repository

7. Update workflow to use GitHub App token instead of PAT:

```yaml
- name: Generate GitHub App Token
  id: generate_token
  uses: tibdex/github-app-token@v1
  with:
    app_id: ${{ secrets.APP_ID }}
    private_key: ${{ secrets.APP_PRIVATE_KEY }}

- name: Run Code Review Agent
  env:
    PATH_TOKEN: ${{ steps.generate_token.outputs.token }}
    # ... rest of env vars
```

8. Add secrets:
   - `APP_ID` - from GitHub App settings
   - `APP_PRIVATE_KEY` - contents of downloaded .pem file

## Benefits:
- Bot appears as "AladdinAI Code Review Bot[bot]" in comments
- Better rate limits than PAT
- More secure (scoped permissions)
- Can be installed on multiple repos
