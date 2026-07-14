# AladdinAI API

    🧞 **AladdinAI** - Self-hosted AI workspace with multi-agent orchestration, persistent memory, and tool execution.

    ## Features

    * 🤖 **Multi-Agent System** - Create and orchestrate specialized AI agents
    * 🧠 **Persistent Memory** - Vector-based memory with per-agent isolation
    * 🛠️ **Tool Execution** - Extensible tool registry with safety gates
    * 📊 **CRM Integration** - Contacts, deals, and activities management
    * 🔐 **Safety First** - PII detection, content filtering, and audit logging
    * 🔗 **RCF Protocol** - Cryptographic signing for webhook authenticity

    ## Authentication

    Most endpoints require JWT authentication. Include the token in the `Authorization` header:
    ```
    Authorization: Bearer <your_jwt_token>
    ```

    ## Rate Limits

    API endpoints are rate-limited per IP address to prevent abuse.
    Exceeding a limit returns HTTP 429 with a `Retry-After` header.
    

## Version: 2.2.1

### Terms of service
https://github.com/aliyevaladddin/AladdinAI/blob/main/LICENSE

**Contact information:**  
Aladdin Aliyev  
https://github.com/aliyevaladddin/AladdinAI  
aladdin@aliyev.site  

**License:** [Apache 2.0](https://github.com/aliyevaladddin/AladdinAI/blob/main/LICENSE)

### /api/auth/register

#### POST
##### Summary:

Register

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

### /api/auth/login

#### POST
##### Summary:

Login

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/auth/refresh

#### POST
##### Summary:

Refresh

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/auth/me

#### GET
##### Summary:

Me

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/stats

#### GET
##### Summary:

Get Agent Stats

##### Description:

Return real-time agentic stats for an agent.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents

#### GET
##### Summary:

List Agents

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Agent

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}

#### GET
##### Summary:

Get Agent

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PUT
##### Summary:

Update Agent

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Agent

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/start

#### POST
##### Summary:

Start Agent

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/stop

#### POST
##### Summary:

Stop Agent

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/inbox

#### POST
##### Summary:

Agent Inbox

##### Description:

Queue a delegated task for an agent. Worker processes it async.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 202 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/messages

#### GET
##### Summary:

List Agent Messages

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/gates

#### GET
##### Summary:

Get Agent Gates

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PATCH
##### Summary:

Patch Agent Gates

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/safety

#### GET
##### Summary:

Get Agent Safety

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PATCH
##### Summary:

Patch Agent Safety

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/safety/recommendations

#### GET
##### Summary:

Get Agent Safety Recommendations

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/gates/recommendations

#### GET
##### Summary:

Get Agent Gates Recommendations

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/extraction/recommendations

#### GET
##### Summary:

Get Agent Extraction Recommendations

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/extraction

#### GET
##### Summary:

Get Agent Extraction

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PATCH
##### Summary:

Patch Agent Extraction

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/safety/log

#### GET
##### Summary:

Get Agent Safety Log

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |
| check | query |  | No |  |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/gates/log

#### GET
##### Summary:

Get Agent Gates Log

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |
| gate | query |  | No |  |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/activity

#### GET
##### Summary:

Get Agent Activity

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/memories

#### GET
##### Summary:

List Agent Memories

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |
| scope | query |  | No | string |
| q | query |  | No |  |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Agent Memory

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/agents/{agent_id}/memories/{memory_id}

#### DELETE
##### Summary:

Delete Agent Memory

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| agent_id | path |  | Yes | integer |
| memory_id | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat/sessions

#### GET
##### Summary:

List Sessions

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Session

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat/sessions/{session_id}

#### DELETE
##### Summary:

Delete Session

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| session_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat/sessions/{session_id}/messages

#### GET
##### Summary:

Get Messages

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| session_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat/messages/{message_id}/feedback

#### POST
##### Summary:

Submit Feedback

##### Description:

Record a human 👍/👎 on an assistant reply — the strong training signal.

Upserts one row per (message, user); re-clicking flips the value. The
durable record lives in Postgres; a fire-and-forget task mirrors the label
onto the Mongo trace so a later fine-tune set prefers human judgment over
the weak write-time score.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| message_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat/upload

#### POST
##### Summary:

Upload Attachment

##### Description:

Save an uploaded image, audio clip, or document and return its handle. Client then
passes the returned `filename` back via ChatRequest.attachments.

The cross-cycle handle is `filename` (UUID.ext): it is returned by both
storage backends, round-tripped by the frontend, and used by `get_media`
and the STT path to read the file back. `file_id` (mongodb) / `path`
(local) are included for completeness but are not load-bearing — nothing
keys off them after upload.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat/media/{filename}

#### GET
##### Summary:

Get Media

##### Description:

Serve a previously uploaded attachment by its `filename` handle.

Works for both storage backends:
  - local: stream the file from disk via FileResponse (path-traversal-safe
    through media.resolve).
  - mongodb: read the bytes from GridFS and return them with the stored
    content-type (there is no file on disk to FileResponse).

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| filename | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/chat

#### POST
##### Summary:

Chat

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/dashboard/stats

#### GET
##### Summary:

Get Dashboard Stats

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/providers

#### GET
##### Summary:

List Providers

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Provider

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/providers/{provider_id}/connect

#### POST
##### Summary:

Connect Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/providers/{provider_id}/models

#### GET
##### Summary:

Get Provider Models

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/providers/{provider_id}/disconnect

#### POST
##### Summary:

Disconnect Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/providers/{provider_id}

#### PUT
##### Summary:

Update Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/router

#### GET
##### Summary:

List Configs

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Config

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/router/{config_id}

#### PUT
##### Summary:

Update Config

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| config_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Config

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| config_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/settings

#### GET
##### Summary:

Get Settings

##### Description:

Get current user's system settings.

Read-only: if the user has no row yet, return defaults without
writing to the database (a GET must not mutate state).

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PUT
##### Summary:

Update Settings

##### Description:

Update user's system settings.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/settings/security-audit

#### POST
##### Summary:

Security Audit

##### Description:

Run security audit of tools using NVIDIA SkillSpector.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/sql/schema

#### GET
##### Summary:

Get Schema

##### Description:

Get database schema: all tables with their columns and types.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/sql/execute

#### POST
##### Summary:

Execute Sql

##### Description:

Execute SQL query against Postgres database.

For safety, read_only mode is enforced by default (SELECT only).

Security Note: This endpoint intentionally allows user-provided SQL queries
for analytics and data exploration purposes. Multiple layers of protection:
1. Authentication required (get_current_user dependency)
2. Read-only mode by default (only SELECT/WITH queries)
3. Dangerous keywords/functions blocked (PG_SLEEP, COPY, etc.)
4. Row limit enforced (max 1000)
5. Destructive operations blocked (DROP, TRUNCATE, ALTER)

This is a controlled SQL execution environment for authenticated users only.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/messaging

#### GET
##### Summary:

List Channels

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Channel

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/messaging/{channel_id}

#### PATCH
##### Summary:

Update Channel

##### Description:

Change which agent answers on this channel.

The agent must belong to the same user — otherwise a tenant could point
their channel at someone else's agent. Passing agent_id=null detaches the
channel (it then falls back to the router/default at dispatch time).

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Channel

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/messaging/{channel_id}/test

#### POST
##### Summary:

Test Channel

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/messaging/{channel_id}/webhook-config

#### GET
##### Summary:

Get Webhook Config

##### Description:

Return the webhook URL, secret, and setup instructions for this channel.

For self-hosted providers like WAHA, the secret must be configured
on the provider side too — otherwise the channel runs unsigned and
incoming requests are accepted with a warning. Knowing this is
essential for production deployments.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/messaging/{channel_id}/waha/qr

#### GET
##### Summary:

Get Waha Qr

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/email

#### GET
##### Summary:

List Emails

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Email

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/email/{account_id}/test

#### POST
##### Summary:

Test Email

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| account_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/email/{account_id}/sync

#### POST
##### Summary:

Sync Email

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| account_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/email/{account_id}

#### PUT
##### Summary:

Update Email

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| account_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Email

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| account_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/email/{account_id}/agent

#### PATCH
##### Summary:

Update Email Agent

##### Description:

Bind or detach an agent from an email account.

The agent must belong to the same user. Pass agent_id=null to detach.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| account_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/channels/email/{account_id}/send

#### POST
##### Summary:

Send Email Endpoint

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| account_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/contacts

#### GET
##### Summary:

List Contacts

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| search | query |  | No |  |
| tag | query |  | No |  |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Contact

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/contacts/import

#### POST
##### Summary:

Import Contacts From Excel

##### Description:

POST /api/crm/contacts/import
Upload .xlsx / .xls → parse → create contacts with column mapping.

Query params let the frontend pass custom column names from the user's file:
  ?name_col=Full+Name&email_col=Email+Address&company_col=Organization

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| name_col | query |  | No | string |
| email_col | query |  | No | string |
| phone_col | query |  | No | string |
| company_col | query |  | No | string |
| tags_col | query |  | No | string |
| notes_col | query |  | No | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/contacts/export

#### GET
##### Summary:

Export Contacts To Excel

##### Description:

GET /api/crm/contacts/export
Returns a styled .xlsx file with all (filtered) contacts.

Optional filters: ?tag=vip&source=excel_import&created_after=2026-01-01

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| tag | query |  | No |  |
| source | query |  | No |  |
| created_after | query |  | No |  |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/contacts/{contact_id}

#### GET
##### Summary:

Get Contact

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| contact_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PUT
##### Summary:

Update Contact

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| contact_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Contact

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| contact_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/contacts/{contact_id}/activities

#### GET
##### Summary:

Contact Activities

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| contact_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/contacts/{contact_id}/deals

#### GET
##### Summary:

Contact Deals

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| contact_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/deals

#### GET
##### Summary:

List Deals

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| stage | query |  | No |  |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Deal

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/deals/{deal_id}

#### GET
##### Summary:

Get Deal

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| deal_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PUT
##### Summary:

Update Deal

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| deal_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Deal

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| deal_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/deals/{deal_id}/stage

#### PUT
##### Summary:

Move Stage

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| deal_id | path |  | Yes | integer |
| stage | query |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/activities

#### GET
##### Summary:

List Activities

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| type | query |  | No |  |
| channel | query |  | No |  |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Activity

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/activities/{activity_id}

#### PATCH
##### Summary:

Update Activity

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| activity_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/activities/{activity_id}/attachments/{filename}

#### GET
##### Summary:

Download Attachment

##### Description:

Download or preview an email attachment by activity ID and filename.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| activity_id | path |  | Yes | integer |
| filename | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/activities/{activity_id}/suggest-reply

#### POST
##### Summary:

Suggest Reply

##### Description:

Generate a suggested reply draft for the given activity.

Picks an agent via _pick_agent, builds a context-rich prompt from the
activity + thread history + contact profile, and runs the agent. The
draft is plain text, never auto-sent.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| activity_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/products

#### GET
##### Summary:

List Products

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| search | query |  | No |  |
| active | query |  | No |  |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Product

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/products/{product_id}

#### GET
##### Summary:

Get Product

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| product_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PUT
##### Summary:

Update Product

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| product_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Product

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| product_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders/metrics

#### GET
##### Summary:

Order Metrics

##### Description:

Sales + marketing dashboard numbers, all user-scoped.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders

#### GET
##### Summary:

List Orders

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| status | query |  | No |  |
| assigned_agent_id | query |  | No |  |
| mine | query | Only orders assigned to an agent (assigned_agent_id set) | No | boolean |
| source | query |  | No |  |
| campaign | query |  | No |  |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Order

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders/{order_id}

#### GET
##### Summary:

Get Order

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### PUT
##### Summary:

Update Order

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Order

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders/{order_id}/status

#### PUT
##### Summary:

Update Order Status

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |
| status | query |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders/{order_id}/history

#### GET
##### Summary:

Order History

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders/{order_id}/items

#### POST
##### Summary:

Add Order Item

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/crm/orders/{order_id}/items/{item_id}

#### PUT
##### Summary:

Update Order Item

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |
| item_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Order Item

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| order_id | path |  | Yes | integer |
| item_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/vms

#### GET
##### Summary:

List Vms

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Vm

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/vms/{vm_id}/connect

#### POST
##### Summary:

Connect Vm

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| vm_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/vms/{vm_id}/disconnect

#### POST
##### Summary:

Disconnect Vm

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| vm_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/vms/{vm_id}

#### PUT
##### Summary:

Update Vm

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| vm_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Vm

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| vm_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/mongodb

#### GET
##### Summary:

List Mongo

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Mongo

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/mongodb/{conn_id}/test

#### POST
##### Summary:

Test Mongo

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/mongodb/{conn_id}

#### PUT
##### Summary:

Update Mongo

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Mongo

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/bentoml

#### GET
##### Summary:

Get Bentoml Connections

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Bentoml Connection

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/bentoml/{conn_id}/deploy

#### POST
##### Summary:

Deploy Service

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/bentoml/{conn_id}

#### PUT
##### Summary:

Update Bentoml Connection

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Bentoml Connection

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/bentoml/{conn_id}/test

#### POST
##### Summary:

Test Bentoml

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| conn_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/webhooks/outgoing

#### GET
##### Summary:

List Outgoing Webhooks

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Outgoing Webhook

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/webhooks/outgoing/{webhook_id}

#### DELETE
##### Summary:

Delete Outgoing Webhook

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| webhook_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/webhooks/telegram/{channel_id}

#### POST
##### Summary:

Telegram Webhook

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/webhooks/whatsapp/{channel_id}

#### GET
##### Summary:

Verify Whatsapp Webhook

##### Description:

Meta verifies the webhook URL by calling GET with hub.verify_token —
it must match `channel.webhook_secret`. No fallback: an unconfigured
channel returns 503 instead of accepting a hardcoded value.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

#### POST
##### Summary:

Whatsapp Webhook

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/webhooks/whatsapp_waha/{channel_id}

#### POST
##### Summary:

Waha Webhook

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/webhooks/sms/{channel_id}

#### POST
##### Summary:

Sms Webhook

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| channel_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/webhooks/github

#### POST
##### Summary:

Github Webhook

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### /api/ssh/exec

#### POST
##### Summary:

Ssh Exec

##### Description:

Execute a command on a remote VM via SSH.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/ssh/vms-list

#### GET
##### Summary:

List Vms For Terminal

##### Description:

List available VMs for the terminal SSH connect command.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/triggers/presets

#### GET
##### Summary:

List Presets

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### /api/triggers/templates

#### GET
##### Summary:

List Trigger Templates

##### Description:

Predefined trigger templates for common use cases.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### /api/triggers/preview

#### GET
##### Summary:

Preview Cron

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| cron | query |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

### /api/triggers

#### GET
##### Summary:

List Triggers

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Create Trigger

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/triggers/{trigger_id}

#### PATCH
##### Summary:

Update Trigger

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| trigger_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### DELETE
##### Summary:

Delete Trigger

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| trigger_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/triggers/{trigger_id}/run

#### POST
##### Summary:

Run Trigger Now

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| trigger_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 202 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/notifications

#### GET
##### Summary:

List Notifications

##### Description:

Return recent notifications, newest first.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/notifications/unread-count

#### GET
##### Summary:

Unread Count

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/notifications/{notification_id}/read

#### POST
##### Summary:

Mark Read

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| notification_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/notifications/read-all

#### POST
##### Summary:

Mark All Read

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/search

#### GET
##### Summary:

Global Search

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| q | query |  | Yes | string |
| limit | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/marketplace

#### GET
##### Summary:

Marketplace

##### Description:

Catalogue of builtin manifests this backend can install.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/providers

#### GET
##### Summary:

List Providers

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

#### POST
##### Summary:

Install Provider

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/providers/{provider_id}

#### DELETE
##### Summary:

Delete Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/providers/{provider_id}/start

#### POST
##### Summary:

Start Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/providers/{provider_id}/stop

#### POST
##### Summary:

Stop Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/providers/{provider_id}/set_active

#### POST
##### Summary:

Set Active Provider

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/providers/{provider_id}/logs

#### GET
##### Summary:

Provider Logs

##### Description:

Last `tail` lines of combined stdout/stderr from this provider's
container. Useful when a provider stops with `last_error` set and the
user wants to know what crashed inside. Soft-fails to a string body if
docker is unreachable — the UI just renders whatever we return.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_id | path |  | Yes | integer |
| tail | query |  | No | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/session

#### POST
##### Summary:

Issue Session

##### Description:

Drawer entry point: hand back a URL the iframe can navigate to.

Provider selection logic:
  - If vm_id is provided: find a running SSH-capable provider (wetty) with
    that vm_id in its config. If multiple match, prefer is_active=True.
  - If vm_id is None: find a running local-shell provider (ttyd). If
    multiple exist, prefer is_active=True.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/session/{provider_session_id}

#### DELETE
##### Summary:

End Session

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| provider_session_id | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 204 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/terminal/auth

#### GET
##### Summary:

Forward Auth

##### Description:

Auth probe for Traefik's forward-auth middleware.

Wired in Traefik via:
    traefik.http.middlewares.aladdin-auth.forwardauth.address=
        http://backend:8000/api/terminal/auth
    traefik.http.middlewares.aladdin-auth.forwardauth.authResponseHeaders=
        Set-Cookie,X-Aladdin-User,X-Aladdin-Provider

`authResponseHeaders` is critical — without it Traefik strips our
`Set-Cookie` from the response and the iframe never picks up the
session cookie.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### /api/reports/excel

#### GET
##### Summary:

Download Excel Report

##### Description:

GET /api/reports/excel?type=all|deals|contacts|activities
Returns a styled multi-sheet Excel workbook for the authenticated user.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| type | query |  | No | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |
| 422 | Validation Error |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /api/digest/trigger

#### POST
##### Summary:

Trigger Daily Digest

##### Description:

Trigger daily digest manually for the authenticated user and send via Telegram/Email.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

##### Security

| Security Schema | Scopes |
| --- | --- |
| OAuth2PasswordBearer | |

### /

#### GET
##### Summary:

Root

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### /health

#### GET
##### Summary:

Health

##### Description:

Health check endpoint for load balancers and container orchestration.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### /api/edition

#### GET
##### Summary:

Edition

##### Description:

Open-core edition marker. Lets the frontend / CLI / `doctor` learn the
commercial boundary (e.g. whether to surface forge UI). Public, non-secret.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Successful Response |

### Models


#### ActivityCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contact_id |  |  | No |
| deal_id |  |  | No |
| type | string |  | Yes |
| channel |  |  | No |
| subject |  |  | No |
| content |  |  | No |
| metadata_json |  |  | No |

#### ActivityResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| contact_id |  |  | Yes |
| deal_id |  |  | Yes |
| type | string |  | Yes |
| channel |  |  | Yes |
| subject |  |  | Yes |
| content |  |  | Yes |
| metadata_json |  |  | Yes |
| created_at | dateTime |  | Yes |

#### ActivityUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contact_id |  |  | No |

#### AgentCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| role | string |  | Yes |
| model | string |  | Yes |
| system_prompt | string |  | Yes |
| tools_config |  |  | No |
| llm_provider_id |  |  | No |
| port |  |  | No |

#### AgentResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| role | string |  | Yes |
| model | string |  | Yes |
| system_prompt | string |  | Yes |
| tools_config |  |  | Yes |
| llm_provider_id |  |  | Yes |
| port |  |  | Yes |
| status | string |  | Yes |

#### AgentUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name |  |  | No |
| role |  |  | No |
| model |  |  | No |
| system_prompt |  |  | No |
| tools_config |  |  | No |
| llm_provider_id |  |  | No |
| port |  |  | No |

#### BentoMLCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| endpoint_url | string |  | Yes |
| api_key |  |  | No |

#### BentoMLDeployRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| service_name | string |  | No |
| port | integer |  | No |

#### Body_import_contacts_from_excel_api_crm_contacts_import_post

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| file | string |  | Yes |

#### Body_upload_attachment_api_chat_upload_post

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| file | string |  | Yes |

#### ChatMessageResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| role | string |  | Yes |
| content | string |  | Yes |
| model |  |  | Yes |
| attachments |  |  | No |
| created_at | string |  | Yes |
| feedback |  |  | No |

#### ChatRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| message | string |  | No |
| agent_id |  |  | No |
| session_id |  |  | No |
| attachments |  |  | No |
| voice_reply | boolean |  | No |
| stream | boolean |  | No |

#### ChatSessionResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| agent_id | integer |  | Yes |
| title | string |  | Yes |
| created_at | string |  | Yes |
| updated_at | string |  | Yes |

#### ContactCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| email |  |  | No |
| phone |  |  | No |
| company |  |  | No |
| tags |  |  | No |
| source |  |  | No |
| notes |  |  | No |

#### ContactResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| email |  |  | Yes |
| phone |  |  | Yes |
| company |  |  | Yes |
| tags |  |  | Yes |
| source |  |  | Yes |
| notes |  |  | Yes |
| created_at | dateTime |  | Yes |
| updated_at | dateTime |  | Yes |

#### ContactUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name |  |  | No |
| email |  |  | No |
| phone |  |  | No |
| company |  |  | No |
| tags |  |  | No |
| notes |  |  | No |

#### DealCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contact_id | integer |  | Yes |
| title | string |  | Yes |
| stage | string |  | No |
| amount |  |  | No |
| currency | string |  | No |
| probability | integer |  | No |
| assigned_agent_id |  |  | No |
| notes |  |  | No |

#### DealResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| contact_id | integer |  | Yes |
| title | string |  | Yes |
| stage | string |  | Yes |
| amount |  |  | Yes |
| currency | string |  | Yes |
| probability | integer |  | Yes |
| assigned_agent_id |  |  | Yes |
| notes |  |  | Yes |
| created_at | dateTime |  | Yes |
| updated_at | dateTime |  | Yes |

#### DealUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| title |  |  | No |
| stage |  |  | No |
| amount |  |  | No |
| currency |  |  | No |
| probability |  |  | No |
| assigned_agent_id |  |  | No |
| notes |  |  | No |

#### EmailAccountCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| provider | string |  | Yes |
| email | string |  | Yes |
| imap_host |  |  | No |
| imap_port |  |  | No |
| smtp_host |  |  | No |
| smtp_port |  |  | No |
| password |  |  | No |
| access_token |  |  | No |
| refresh_token |  |  | No |

#### EmailAccountResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| provider | string |  | Yes |
| email | string |  | Yes |
| status | string |  | Yes |
| agent_id |  |  | Yes |
| last_synced_at |  |  | Yes |
| created_at | dateTime |  | Yes |

#### EmailAccountUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| email |  |  | No |
| imap_host |  |  | No |
| imap_port |  |  | No |
| smtp_host |  |  | No |
| smtp_port |  |  | No |
| password |  |  | No |

#### EmailAgentUpdate

Lightweight PATCH — only updates the agent binding on an email account.

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| agent_id |  |  | No |

#### ExtractionUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| enabled |  |  | No |
| model |  |  | No |
| max_facts |  |  | No |

#### FeedbackRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| value | string |  | Yes |

#### FeedbackResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| message_id | integer |  | Yes |
| value | string |  | Yes |

#### GatesUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| default_gate_model |  |  | No |
| gates |  |  | No |

#### HTTPValidationError

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| detail | [ [ValidationError](#validationerror) ] |  | No |

#### InboxRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| task | string |  | Yes |
| context |  |  | No |
| parent_session_id |  |  | No |

#### InboxResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| message_id | integer |  | Yes |
| status | string |  | Yes |

#### LLMProviderCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| type | string |  | Yes |
| api_key |  |  | No |
| base_url | string |  | Yes |

#### LLMProviderResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| type | string |  | Yes |
| base_url | string |  | Yes |
| status | string |  | Yes |

#### LoginRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| email | string (email) |  | Yes |
| password | string |  | Yes |

#### MarketplaceEntry

One row in the dashboard marketplace — read straight from a YAML manifest.

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| type | string |  | Yes |
| name | string |  | Yes |
| description |  |  | No |
| image | string |  | Yes |
| internal_port | integer |  | Yes |
| requires_ssh_proxy | boolean |  | No |

#### MemoryCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| fact | string |  | Yes |
| visibility | string |  | No |
| tags |  |  | No |

#### MessagingChannelCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| type | string |  | Yes |
| name | string |  | Yes |
| config | object |  | Yes |
| agent_id |  |  | No |

#### MessagingChannelResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| type | string |  | Yes |
| name | string |  | Yes |
| agent_id |  |  | Yes |
| status | string |  | Yes |
| created_at | dateTime |  | Yes |

#### MessagingChannelUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| agent_id |  |  | No |

#### MongoCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| connection_string |  |  | No |
| db_name | string |  | Yes |

#### MongoResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| db_name | string |  | Yes |
| status | string |  | Yes |

#### OrderCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contact_id | integer |  | Yes |
| deal_id |  |  | No |
| currency | string |  | No |
| assigned_agent_id |  |  | No |
| source |  |  | No |
| campaign |  |  | No |
| notes |  |  | No |
| items | [ [OrderItemCreate](#orderitemcreate) ] |  | No |

#### OrderItemCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| product_id |  |  | No |
| product_name |  |  | No |
| quantity | integer |  | No |
| unit_price |  |  | No |

#### OrderItemResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| product_id |  |  | Yes |
| product_name | string |  | Yes |
| quantity | integer |  | Yes |
| unit_price | number |  | Yes |
| line_total | number |  | Yes |

#### OrderMetricsResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| realized_revenue | number |  | Yes |
| booked_revenue | number |  | Yes |
| order_count | integer |  | Yes |
| count_by_status | object |  | Yes |
| revenue_by_status | object |  | Yes |
| pipeline_value | number |  | Yes |
| funnel | object |  | Yes |
| win_rate | number |  | Yes |
| revenue_by_source | object |  | Yes |
| revenue_by_campaign | object |  | Yes |

#### OrderResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| contact_id | integer |  | Yes |
| deal_id |  |  | Yes |
| status | string |  | Yes |
| total | number |  | Yes |
| currency | string |  | Yes |
| assigned_agent_id |  |  | Yes |
| source |  |  | Yes |
| campaign |  |  | Yes |
| notes |  |  | Yes |
| created_at | dateTime |  | Yes |
| updated_at | dateTime |  | Yes |
| items | [ [OrderItemResponse](#orderitemresponse) ] |  | No |

#### OrderUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| deal_id |  |  | No |
| currency |  |  | No |
| assigned_agent_id |  |  | No |
| source |  |  | No |
| campaign |  |  | No |
| notes |  |  | No |

#### OutgoingWebhookCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| url | string |  | Yes |
| secret |  |  | No |
| events | [ string ] |  | Yes |
| is_active | boolean |  | No |

#### OutgoingWebhookResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| url | string |  | Yes |
| secret |  |  | No |
| events | [ string ] |  | Yes |
| is_active | boolean |  | No |
| id | integer |  | Yes |
| created_at | dateTime |  | Yes |

#### ProductCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| sku | string |  | Yes |
| name | string |  | Yes |
| description |  |  | No |
| price | number |  | No |
| currency | string |  | No |
| active | boolean |  | No |

#### ProductResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| sku | string |  | Yes |
| name | string |  | Yes |
| description |  |  | Yes |
| price | number |  | Yes |
| currency | string |  | Yes |
| active | boolean |  | Yes |
| created_at | dateTime |  | Yes |
| updated_at | dateTime |  | Yes |

#### ProductUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| sku |  |  | No |
| name |  |  | No |
| description |  |  | No |
| price |  |  | No |
| currency |  |  | No |
| active |  |  | No |

#### ProviderInstall

Install request — picks an entry from the marketplace by `type`.

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| type | string | Manifest type, e.g. 'ttyd' | Yes |
| name |  | Display name; defaults to manifest name | No |
| config |  |  | No |
| vm_id |  | VM to connect to (for SSH-based providers like wetty) | No |

#### ProviderResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| type | string |  | Yes |
| source | string |  | Yes |
| image | string |  | Yes |
| internal_port | integer |  | Yes |
| requires_ssh_proxy | boolean |  | Yes |
| is_active | boolean |  | Yes |
| status | string |  | Yes |
| container_id |  |  | No |
| last_health_at |  |  | No |
| last_error |  |  | No |
| created_at | dateTime |  | Yes |

#### RefreshRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| refresh_token | string |  | Yes |

#### RegisterRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| email | string (email) |  | Yes |
| password | string |  | Yes |
| name | string |  | Yes |

#### RouterConfigCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| type | string |  | Yes |
| config | object |  | Yes |
| is_active | boolean |  | No |

#### RouterConfigResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| type | string |  | Yes |
| config | object |  | Yes |
| is_active | boolean |  | Yes |

#### RouterConfigUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name |  |  | No |
| type |  |  | No |
| config |  |  | No |
| is_active |  |  | No |

#### SQLQueryRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| query | string |  | Yes |
| read_only | boolean |  | No |
| limit | integer |  | No |

#### SQLQueryResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| success | boolean |  | Yes |
| rows | [ object ] |  | Yes |
| columns | [ string ] |  | Yes |
| row_count | integer |  | Yes |
| error |  |  | No |
| message |  |  | No |

#### SSHExecRequest

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| vm_id | integer |  | Yes |
| command | string |  | Yes |

#### SSHExecResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| stdout | string |  | Yes |
| stderr | string |  | Yes |
| exit_code | integer |  | Yes |

#### SafetyUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| default_safety_model |  |  | No |
| safety_block_response |  |  | No |
| safety |  |  | No |

#### SchemaResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| tables | [ [TableSchema](#tableschema) ] |  | Yes |

#### SearchResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contacts | [ [SearchResult](#searchresult) ] |  | Yes |
| deals | [ [SearchResult](#searchresult) ] |  | Yes |
| activities | [ [SearchResult](#searchresult) ] |  | Yes |
| agents | [ [SearchResult](#searchresult) ] |  | Yes |
| memories | [ [SearchResult](#searchresult) ] |  | Yes |
| total | integer |  | Yes |

#### SearchResult

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| kind | string |  | Yes |
| id | integer |  | Yes |
| title | string |  | Yes |
| subtitle |  |  | No |
| snippet |  |  | No |
| contact_id |  |  | No |
| activity_type |  |  | No |
| channel |  |  | No |
| created_at |  |  | No |

#### SendEmailBody

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| to_email | string |  | Yes |
| subject | string |  | Yes |
| body | string |  | Yes |
| contact_id |  |  | No |

#### SessionRequest

`POST /terminal/session` — what the drawer sends.

`vm_id` is reserved for adapters with `requires_ssh_proxy=true`; the MVP
ttyd adapter ignores it.

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| vm_id |  |  | No |

#### SessionResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| url | string |  | Yes |
| expires_at | dateTime |  | Yes |
| provider_type | string |  | Yes |
| provider_session_id |  |  | No |

#### SuggestReplyResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| draft | string |  | Yes |
| agent_id | integer |  | Yes |
| agent_name | string |  | Yes |

#### SystemSettingsResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id |  |  | Yes |
| user_id | integer |  | Yes |
| media_storage_backend | string |  | Yes |
| created_at | dateTime |  | Yes |
| updated_at | dateTime |  | Yes |

#### SystemSettingsSchema

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| media_storage_backend | string |  | Yes |

#### TableSchema

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| table_name | string |  | Yes |
| columns | [ object ] |  | Yes |

#### TokenResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| access_token | string |  | Yes |
| refresh_token | string |  | Yes |
| token_type | string |  | No |

#### TriggerCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| schedule_kind | string |  | No |
| schedule_preset |  |  | No |
| cron |  |  | No |
| agent_ids | [ integer ] |  | Yes |
| task_template | string |  | Yes |
| context_template |  |  | No |
| enabled | boolean |  | No |

#### TriggerUpdate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name |  |  | No |
| schedule_kind |  |  | No |
| schedule_preset |  |  | No |
| cron |  |  | No |
| agent_ids |  |  | No |
| task_template |  |  | No |
| context_template |  |  | No |
| enabled |  |  | No |

#### UserResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| email | string |  | Yes |
| name | string |  | Yes |

#### VMCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string |  | Yes |
| host | string |  | Yes |
| port | integer |  | No |
| username | string |  | No |
| ssh_key |  |  | No |
| password |  |  | No |

#### VMResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer |  | Yes |
| name | string |  | Yes |
| host | string |  | Yes |
| port | integer |  | Yes |
| username | string |  | Yes |
| status | string |  | Yes |

#### ValidationError

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| loc | [  ] |  | Yes |
| msg | string |  | Yes |
| type | string |  | Yes |
| input |  |  | No |
| ctx | object |  | No |