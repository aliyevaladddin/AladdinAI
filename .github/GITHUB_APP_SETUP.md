# GitHub App Setup Guide

Этот гайд объясняет как настроить GitHub App ботов для AladdinAI.

## Создание GitHub App

### 1. Создайте новый GitHub App

Перейдите: GitHub Settings → Developer settings → GitHub Apps → New GitHub App

### 2. Базовая информация

- **Name**: AladdinAI[bot] или NVIDIA Code Review[bot]
- **Homepage URL**: https://github.com/aliyevaladddin/AladdinAI
- **Webhook**: Uncheck "Active" (используем Actions, не webhooks)

### 3. Разрешения (Permissions)

#### Для AladdinAI[bot]:
- **Contents**: Read & write
- **Issues**: Read & write
- **Pull requests**: Read & write
- **Metadata**: Read-only (автоматически)

#### Для NVIDIA Code Review[bot]:
- **Contents**: Read-only
- **Pull requests**: Read & write
- **Metadata**: Read-only (автоматически)

### 4. Создание и установка

1. Нажмите "Create GitHub App"
2. Сгенерируйте private key → скачайте .pem файл
3. Установите app на ваш репозиторий (Install App)

## Получение Installation ID

После установки GitHub App на репозиторий, нужно получить Installation ID:

### Способ 1: Через URL установки

Когда устанавливаете App, GitHub редиректит на URL вида:
```
https://github.com/settings/installations/INSTALLATION_ID
```

`INSTALLATION_ID` — это число в конце URL.

### Способ 2: Через GitHub API

```bash
# Замените YOUR_APP_ID и YOUR_PRIVATE_KEY_PATH
curl -i -H "Authorization: Bearer $(python3 -c "
import jwt
import time

app_id = 'YOUR_APP_ID'
private_key = open('YOUR_PRIVATE_KEY_PATH').read()

payload = {
    'iat': int(time.time()) - 60,
    'exp': int(time.time()) + (10 * 60),
    'iss': app_id
}

token = jwt.encode(payload, private_key, algorithm='RS256')
print(token)
")" \
-H "Accept: application/vnd.github+json" \
https://api.github.com/app/installations
```

Ответ содержит массив установок, найдите нужный репозиторий и скопируйте `id`.

## Настройка Backend

### 1. Добавьте в `.env` файл:

```bash
# AladdinAI[bot]
ALADDINAI_BOT_APP_ID=123456
ALADDINAI_BOT_INSTALLATION_ID=12345678
ALADDINAI_BOT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"

# NVIDIA Code Review[bot]
NVIDIA_BOT_APP_ID=234567
NVIDIA_BOT_INSTALLATION_ID=23456789
NVIDIA_BOT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
```

**Важно**: Private key должен быть в одну строку с `\n` вместо реальных переносов.

### 2. Добавьте GitHub Secrets для Actions:

В настройках репозитория (Settings → Secrets and variables → Actions):

- `ALADDINAI_BOT_APP_ID`
- `ALADDINAI_BOT_PRIVATE_KEY`
- `NVIDIA_BOT_APP_ID`
- `NVIDIA_BOT_PRIVATE_KEY`

## Использование в Workflows

```yaml
- name: Generate GitHub App Token
  id: generate_token
  uses: tibdex/github-app-token@v1
  with:
    app_id: ${{ secrets.ALADDINAI_BOT_APP_ID }}
    private_key: ${{ secrets.ALADDINAI_BOT_PRIVATE_KEY }}

- name: Use Token
  run: |
    curl -H "Authorization: Bearer ${{ steps.generate_token.outputs.token }}" \
         https://api.github.com/repos/${{ github.repository }}/issues
```

## Использование в Backend Agents

Боты доступны через tools в `backend/app/tools/github_tools.py`:

- `github_create_issue` — создать issue (AladdinAI[bot])
- `github_comment_on_issue` — комментарий в issue (AladdinAI[bot])
- `github_create_pr` — создать PR (AladdinAI[bot])
- `github_review_pr` — code review (NVIDIA Code Review[bot])
- `github_list_issues` — список issues (AladdinAI[bot])

Агенты автоматически получают доступ к этим инструментам через tool registry.

## Проверка работы

### Проверка AladdinAI[bot]:
```bash
gh workflow run bot-commits.yml
```

### Проверка NVIDIA Code Review[bot]:
Создайте PR с изменениями в коде — бот автоматически оставит review.

## Преимущества GitHub Apps

- Боты появляются как "AladdinAI[bot]" в коммитах и комментариях
- Лучшие rate limits чем PAT
- Более безопасно (scoped permissions)
- Можно установить на несколько репозиториев
- Токены автоматически обновляются (1 час TTL)
