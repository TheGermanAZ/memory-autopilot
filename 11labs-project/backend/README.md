# Memory Autopilot — Backend

FastAPI service that gives ElevenLabs voice agents persistent memory across calls. Receives post-call webhooks from ElevenLabs, stores structured caller profiles in Postgres, and injects that context back into the agent before the next call starts.

## Architecture

```
Incoming call
     |
     v
ElevenLabs Agent
     |
     | (before call starts)
     v
POST /webhooks/elevenlabs/conversation-init
     |  (returns dynamic_variables: name, issue history, open actions)
     v
ElevenLabs Agent (now context-aware)
     |
     | (after call ends)
     v
POST /webhooks/elevenlabs/post-call   <-- HMAC-verified
     |
     v
FastAPI
     |
     +-- parse data_collection_results from ElevenLabs analysis
     |
     v
Postgres
  caller_profiles    (one row per phone number, updated each call)
  memory_snapshots   (append-only log of every conversation)
```

**Key design choice:** Memory is extracted by ElevenLabs natively via Data Collection — the agent itself decides what to remember. The backend just stores and serves it. The demo extraction path (Claude via `POST /api/demo/extract`) exists only for the interactive demo and is not part of the production call flow.

## API Reference

### POST /webhooks/elevenlabs/post-call

Receives a post-call transcription webhook from ElevenLabs. Parses `analysis.data_collection_results` and upserts the caller profile.

Requires `ElevenLabs-Signature` header (HMAC-SHA256, 5-minute replay window).

**Request body (ElevenLabs schema):**
```json
{
  "agent_id": "agent_abc123",
  "conversation_id": "conv_xyz789",
  "status": "done",
  "transcript": [
    {"role": "user", "message": "Hi, my name is Sarah Chen."},
    {"role": "agent", "message": "Hello Sarah, how can I help?"}
  ],
  "analysis": {
    "transcript_summary": "Customer called about a billing issue.",
    "data_collection_results": {
      "customer_name": "Sarah Chen",
      "issue_type": "billing",
      "issue_summary": "Double charged for premium plan",
      "order_id": "ORD-4521",
      "customer_sentiment": "frustrated",
      "open_actions": "Refund pending"
    }
  },
  "metadata": {
    "phone": {"caller_id": "+15551234567"}
  }
}
```

**Response:**
```json
{"status": "ok", "new": true}
```

`new: false` means the conversation was already stored (idempotent — safe to retry).

**Error responses:**
- `401` — missing or invalid signature
- `422` — payload does not match expected schema

---

### POST /webhooks/elevenlabs/conversation-init

Called by ElevenLabs before a call starts. Returns dynamic variables that are injected into the agent's prompt for that session.

**Request body:**
```json
{
  "caller_id": "+15551234567",
  "agent_id": "agent_abc123"
}
```

**Response (known caller):**
```json
{
  "dynamic_variables": {
    "caller_phone": "+15551234567",
    "customer_name": "Sarah Chen",
    "issue_summary": "Double charged for premium plan",
    "issue_type": "billing",
    "order_id": "ORD-4521",
    "customer_sentiment": "frustrated",
    "open_actions": "Refund pending"
  }
}
```

**Response (unknown caller):** All profile fields are empty strings. `caller_phone` is always set so it round-trips back in the post-call webhook.

- `400` — missing `caller_id`

---

### GET /api/demo/memory/{caller_id}

Fetches the stored caller profile for the demo UI. `caller_id` should be E.164 format (e.g., `+15551234567`).

**Response:**
```json
{
  "caller_id": "+15551234567",
  "customer_name": "Sarah Chen",
  "issue_summary": "Double charged for premium plan",
  "issue_type": "billing",
  "order_id": "ORD-4521",
  "customer_sentiment": "frustrated",
  "open_actions": "Refund pending",
  "first_seen_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:45:00Z"
}
```

- `404` — caller not found

---

### POST /api/demo/extract

Demo-only. Sends a raw transcript to Claude (claude-sonnet-4-6) and returns structured memory fields. Not used in production — the live call path uses ElevenLabs Data Collection instead.

**Request body:**
```json
{
  "transcript": "Customer: Hi, my name is Sarah Chen. I was double charged for my subscription."
}
```

**Response:**
```json
{
  "customer_name": "Sarah Chen",
  "issue_summary": "Double charged for subscription",
  "issue_type": "billing",
  "order_id": "",
  "customer_sentiment": "frustrated",
  "open_actions": ""
}
```

- `500` — extraction failed (Claude error or malformed response)

---

### GET /health

Liveness + database connectivity check.

**Response:**
```json
{"status": "ok", "db": "connected", "version": "0.1.0"}
```

`db` is `"disconnected"` if the Postgres pool is unreachable.

---

## Setup

### Prerequisites

- Python 3.12+
- Docker (required for tests — testcontainers spins up a real Postgres)
- A Postgres instance for local development

### Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` (or set variables directly):

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://localhost:5432/memory_autopilot` | asyncpg connection string |
| `ELEVENLABS_WEBHOOK_SECRET` | Yes | — | Signing secret from ElevenLabs dashboard (Webhook settings) |
| `ELEVENLABS_AGENT_ID` | No | — | Your ElevenLabs agent ID (used for logging) |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated CORS origins |
| `ANTHROPIC_API_KEY` | Yes (demo only) | — | Required only for `POST /api/demo/extract` |
| `LOG_LEVEL` | No | `INFO` | Structlog level |

### Apply Schema

```bash
psql $DATABASE_URL < schema.sql
```

### Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Testing

Tests require Docker (testcontainers pulls `postgres:16-alpine` automatically).

```bash
cd backend
pytest
```

Run a specific test file:

```bash
pytest tests/test_webhooks.py -v
```

### What is tested

| File | Coverage |
|---|---|
| `test_webhooks.py` | Post-call storage, HMAC rejection, malformed payloads, idempotency (both HTTP and DB-level), conversation-init returns correct dynamic vars, unknown caller returns empty profile |
| `test_memory.py` | Profile creation, profile update across calls (latest non-empty value wins) |
| `test_demo_extraction.py` | Claude extraction returns structured fields (Anthropic client is mocked) |

All tests use a real Postgres instance (via testcontainers) and a real ASGI test client (httpx). No mocking of the database layer.

## Deployment

The backend is designed for Railway.

1. Create a new Railway project and add a Postgres plugin.
2. Deploy from the `backend/` directory (Railway auto-detects the Dockerfile).
3. Set the environment variables in Railway's Variables tab.
4. Run the schema migration once via Railway's shell or by connecting to the Postgres instance:
   ```bash
   psql $DATABASE_URL < schema.sql
   ```
5. Configure ElevenLabs:
   - Set the post-call webhook URL to `https://your-app.railway.app/webhooks/elevenlabs/post-call`
   - Set the conversation-init webhook URL to `https://your-app.railway.app/webhooks/elevenlabs/conversation-init`
   - Copy the signing secret into the `ELEVENLABS_WEBHOOK_SECRET` variable

The service starts with `uvicorn app.main:app --host 0.0.0.0 --port 8000` (see Dockerfile).
