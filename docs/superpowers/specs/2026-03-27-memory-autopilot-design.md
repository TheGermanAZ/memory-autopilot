# Memory Autopilot — Design Spec

**Date:** 2026-03-27
**Purpose:** Spearfish demo for ElevenLabs Full-Stack Engineer (Back-End Leaning) role
**Timeline:** 1 day
**Deploy:** Next.js on Vercel + FastAPI on Railway + Postgres on Railway

---

## 1. Problem

ElevenLabs voice agents have no built-in cross-session memory. Each call starts fresh — the agent doesn't know who's calling or what happened last time. The platform provides the primitives to solve this (Data Collection, post-call webhooks, conversation initiation webhooks, dynamic variables), but the application layer that ties them together doesn't exist.

Memory Autopilot is that application layer: automatic memory extraction after every call, structured storage by caller, and injection via dynamic variables on the next call. Built entirely on ElevenLabs platform primitives.

---

## 2. System Flow

### After a call ends:

```
ElevenLabs Agent — call ends
  │
  ├─ ElevenLabs runs Data Collection (native LLM extraction)
  │    extracts: customer_name, issue_type, issue_summary,
  │              order_id, customer_sentiment, open_actions
  │
  ├─ ElevenLabs sends Post-Call Webhook (HMAC-signed)
  │    payload includes:
  │      data.transcript
  │      data.analysis.transcript_summary
  │      data.analysis.data_collection_results
  │
  └─► FastAPI Backend receives webhook
       ├─ verifies HMAC via ElevenLabs-Signature header
       ├─ in a single transaction:
       │    1. INSERT memory_snapshot (ON CONFLICT DO NOTHING)
       │    2. only if insert succeeded: UPSERT caller_profile
       └─ returns 200
```

### When the next call arrives:

```
Incoming call → ElevenLabs sends Conversation Initiation Webhook
  │  sends: caller_id (E.164 phone), agent_id, called_number, call_sid
  │
  └─► FastAPI Backend
       ├─ single indexed read on caller_profiles by caller_id
       ├─ NO external calls, NO LLM work (this is on the hot path)
       ├─ returns ALL defined dynamic variables:
       │    known caller → populated from profile
       │    unknown caller → all keys present with empty-string defaults
       └─ response: { "dynamic_variables": { ... } }
```

---

## 3. ElevenLabs Agent Configuration

### Data Collection Fields

Configured in the agent's Analysis tab:

| Identifier | Type | Description |
|---|---|---|
| customer_name | string | Full name of the caller as stated in conversation |
| issue_type | string | Category: billing, technical, general, complaint |
| issue_summary | string | One-sentence summary of the caller's primary issue |
| order_id | string | Order or reference number if explicitly mentioned, empty string otherwise |
| customer_sentiment | string | Emotional state: frustrated, neutral, satisfied, angry, anxious |
| open_actions | string | Promised follow-ups or pending items from this call |

### Dynamic Variables in System Prompt

Plain interpolation only — no conditional templating:

```
You are a customer support agent for Acme Corp.

## Caller Context
Caller name: {{customer_name}}
Last issue: {{issue_summary}}
Issue type: {{issue_type}}
Order reference: {{order_id}}
Previous sentiment: {{customer_sentiment}}
Open actions: {{open_actions}}

If the caller name is empty, this is a first-time caller — greet them warmly and ask how you can help. If the caller name is present, greet them by name and reference their prior interaction before asking how to proceed.
```

### Dynamic Variables in First Message

```
Hi {{customer_name}}, welcome back. I can see you called recently about {{issue_summary}}. Let me check on the status for you.
```

Note: For first-time callers, all variables will be empty strings. The prompt instructs the agent to handle this gracefully via the natural language instruction, not via template conditionals.

---

## 4. API Surface

### Platform Integration (the real system)

```
POST /webhooks/elevenlabs/post-call
```
- Receives post-call transcription webhook from ElevenLabs
- Verifies HMAC signature via `ElevenLabs-Signature` header
- Extracts `data_collection_results` from `data.analysis.data_collection_results`
- Extracts `transcript_summary` from `data.analysis.transcript_summary`
- In one transaction: inserts snapshot (idempotent by conversation_id), then upserts caller profile
- Returns 200 on success, 401 on bad signature, 409 silently on duplicate

```
POST /webhooks/elevenlabs/conversation-init
```
- Called by ElevenLabs during Twilio dial tone when a new call arrives
- Receives: `caller_id` (E.164 phone), `agent_id`, `called_number`, `call_sid`
- Single indexed read on `caller_profiles`
- Returns ALL defined dynamic variable keys every time:
  - Known caller: populated from profile
  - Unknown caller: all keys present with empty-string values
- Response: `{ "dynamic_variables": { "customer_name": "...", "issue_summary": "...", ... } }`
- Must be fast — single DB read, no external calls, no LLM

### Demo Endpoints (for the landing page)

```
GET /api/demo/memory/{caller_id}
```
- Returns stored caller profile for the landing page display

```
POST /api/demo/extract
```
- **Demo-only endpoint.** Not the production path.
- Takes a raw transcript, runs a simple LLM extraction (Claude), returns structured fields
- This is a separate code path from the webhook handler — the webhook handler receives pre-extracted data from ElevenLabs Data Collection
- Exists solely for the "Try it yourself" section on the landing page
- Clearly labeled in code and docs as demo-only

### Ops

```
GET /health
```
- Returns API status + DB connectivity check

---

## 5. Data Model

Two-table design: profiles (read model for conversation-init) + snapshots (append-only audit trail).

```sql
-- Caller profile: the runtime read model
-- conversation-init returns these fields as dynamic variables
CREATE TABLE caller_profiles (
    caller_id           TEXT PRIMARY KEY,    -- E.164 phone number
    customer_name       TEXT NOT NULL DEFAULT '',
    issue_summary       TEXT NOT NULL DEFAULT '',
    issue_type          TEXT NOT NULL DEFAULT '',
    order_id            TEXT NOT NULL DEFAULT '',
    customer_sentiment  TEXT NOT NULL DEFAULT '',
    open_actions        TEXT NOT NULL DEFAULT '',
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Memory snapshots: one per conversation, append-only
CREATE TABLE memory_snapshots (
    conversation_id     TEXT PRIMARY KEY,    -- from ElevenLabs
    caller_id           TEXT NOT NULL REFERENCES caller_profiles(caller_id),
    agent_id            TEXT,
    source              TEXT NOT NULL,        -- 'webhook' | 'demo'
    data_collection     JSONB NOT NULL,       -- raw data_collection_results from webhook
    transcript_summary  TEXT,                 -- from data.analysis.transcript_summary
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_snapshots_caller
    ON memory_snapshots (caller_id, created_at DESC);
```

### Identity Model

- `caller_id` is an E.164 phone number, matching ElevenLabs' `system__caller_id`
- `conversation_id` is the unique identifier from ElevenLabs, used as natural PK for snapshots
- No synthetic IDs — we use what the platform gives us
- Limitation: phone number identity doesn't handle shared lines or callers using different numbers. Acceptable for a demo; a production system would need a richer identity resolution layer.

### Idempotency

Duplicate webhook deliveries are handled in a single transaction:
1. `INSERT INTO memory_snapshots ... ON CONFLICT (conversation_id) DO NOTHING`
2. Check if insert happened (row count)
3. Only if insert succeeded: `INSERT INTO caller_profiles ... ON CONFLICT (caller_id) DO UPDATE`

This prevents double-counting on profile updates when the same webhook is delivered twice.

### Data Retention

- **Transcripts are NOT stored.** Only structured data_collection results and transcript_summary are persisted.
- The `memory_snapshots.data_collection` column stores the structured extraction output, not raw transcript text.
- In production: configurable retention policy and PII redaction would be next steps.

---

## 6. Pydantic Models

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class CallerProfile(BaseModel):
    caller_id: str
    customer_name: str
    issue_summary: str
    issue_type: str
    order_id: str
    customer_sentiment: str
    open_actions: str
    first_seen_at: datetime
    updated_at: datetime


class DynamicVariablesResponse(BaseModel):
    dynamic_variables: dict[str, str]


class MemorySnapshot(BaseModel):
    conversation_id: str
    caller_id: str
    agent_id: str | None
    source: Literal["webhook", "demo"]
    data_collection: dict
    transcript_summary: str | None
    created_at: datetime


class DemoExtractionRequest(BaseModel):
    transcript: str


class DemoExtractionResponse(BaseModel):
    """Demo-only. Not used by the webhook path."""
    customer_name: str
    issue_summary: str
    issue_type: str
    order_id: str
    customer_sentiment: str
    open_actions: str
```

---

## 7. Repo Structure

```
memory-autopilot/
├── backend/                        ← The star of the repo
│   ├── app/
│   │   ├── main.py                 FastAPI app, CORS, lifespan
│   │   ├── routers/
│   │   │   ├── webhooks.py         post-call + conversation-init
│   │   │   └── demo.py             demo memory lookup + demo extract
│   │   ├── services/
│   │   │   ├── memory.py           profile upsert + snapshot storage
│   │   │   ├── demo_extraction.py  demo-only LLM extraction (Claude)
│   │   │   └── webhook_auth.py     HMAC signature verification
│   │   ├── models/
│   │   │   └── schemas.py          Pydantic models
│   │   ├── db.py                   async Postgres connection
│   │   └── config.py               Settings via env vars
│   ├── tests/
│   │   ├── test_webhooks.py        7 tests — the backbone
│   │   ├── test_memory.py          2 tests — storage logic
│   │   └── test_demo_extraction.py 1 test — demo endpoint
│   │   └── conftest.py             Local Docker Postgres fixture
│   ├── schema.sql                  Raw SQL schema (no Alembic for v1)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md                   API docs, setup, architecture
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                Landing page
│   │   ├── components/
│   │   │   ├── TranscriptPanel.tsx
│   │   │   ├── MemoryCard.tsx
│   │   │   ├── ComparisonPanel.tsx
│   │   │   ├── TryItYourself.tsx
│   │   │   └── AudioPlayer.tsx
│   │   └── layout.tsx
│   ├── public/audio/               Pre-computed TTS files
│   └── package.json
│
├── scripts/
│   ├── generate_audio.py           ElevenLabs TTS generation
│   └── seed_data.py                Populate DB with demo caller
│
├── data/
│   ├── transcripts/                Call 1 + Call 2 scripts
│   ├── memory/                     Demo caller profile JSON
│   └── agent_config.json           ElevenLabs agent setup reference
│
└── README.md                       Opens with architecture + backend
```

---

## 8. Demo Page Layout

Scroll-through narrative, top to bottom:

1. **Hero** — "Memory Autopilot. Automatic cross-session memory for ElevenLabs voice agents. Your agents forget every caller. This fixes that." CTA: "See the demo" + "View on GitHub"

2. **Panel 1: "The First Call"** — Customer support transcript. Sarah Chen calls about a double charge on order ORD-4521. Each line has an audio play button (pre-computed ElevenLabs TTS).

3. **Panel 2: "What Memory Autopilot Extracted"** — Animated card showing the structured data that ElevenLabs Data Collection extracted: customer_name, issue_type, issue_summary, order_id, customer_sentiment, open_actions. One-liner: "Extracted automatically by ElevenLabs Data Collection after the call."

4. **Panel 3: "The Callback" — Side by Side** — Two columns: Memory OFF ("How can I help you today?") vs Memory ON ("Hi Sarah, I can see you called about order ORD-4521..."). Toggle switch. Audio play buttons on each version. This is the "aha" moment.

5. **Panel 4: "How It Works"** — Three-step diagram: Post-call webhook → Store by caller → Inject via dynamic variables. Code snippets showing the webhook handler and conversation-init response.

6. **Panel 5: "Try It Yourself"** — Paste a transcript, hit the real API, see structured extraction. Labeled as "Demo extraction endpoint — the production system uses ElevenLabs native Data Collection."

---

## 9. Testing Strategy

~10 tests, focused on webhook correctness and failure modes:

### test_webhooks.py (7 tests — the backbone)
- `test_post_call_webhook_stores_memory` — valid HMAC + payload → profile + snapshot created
- `test_post_call_webhook_rejects_invalid_signature` — bad HMAC → 401, nothing written
- `test_post_call_webhook_rejects_malformed_payload` — valid HMAC but bad payload shape → 422, nothing written
- `test_post_call_webhook_idempotent` — same conversation_id twice → no duplicate, profile not double-updated
- `test_post_call_idempotency_enforced_by_db_constraint` — verify the UNIQUE constraint on conversation_id catches duplicates even if app logic fails
- `test_conversation_init_returns_dynamic_vars` — known caller → populated dynamic_variables with all keys
- `test_conversation_init_unknown_caller` — unknown caller → all keys present with empty-string defaults
- `test_conversation_init_missing_caller_id` — missing/malformed caller_id → clean 400, no crash

### test_memory.py (2 tests)
- `test_create_caller_profile`
- `test_update_existing_profile` — second call updates fields correctly

### test_demo_extraction.py (1 test)
- `test_extract_returns_structured_fields`

### Approach
- pytest with FastAPI TestClient (httpx under the hood)
- **Local Docker Postgres** for tests — fast, disposable, no remote flake. Not Railway.
- Webhook payloads as fixtures matching real ElevenLabs payload shape (`data.analysis.data_collection_results`, etc.)
- Tests run locally in <10 seconds

---

## 10. Deployment

### Frontend — Vercel
- Next.js App Router
- `vercel --prod`
- Env: `NEXT_PUBLIC_API_URL` → Railway backend URL
- Static assets: pre-computed audio in `/public/audio/`

### Backend — Railway
- Docker (Python 3.12), simple single-stage Dockerfile
- FastAPI + Postgres in same Railway project
- `railway up`
- Env: `DATABASE_URL`, `ELEVENLABS_WEBHOOK_SECRET`, `ELEVENLABS_AGENT_ID`, `ALLOWED_ORIGINS`
- Health check endpoint configured

---

## 11. Build Timeline (Backend-First)

The build order prioritizes backend credibility. Frontend is the flex layer — it absorbs time pressure, not the backend.

| Phase | Time | What |
|---|---|---|
| Pre-compute | 2 hrs | Write call scripts, generate audio via ElevenLabs TTS API, seed demo data |
| **Backend** | **4-5 hrs** | FastAPI app, webhook handlers, HMAC auth, memory service, schema, tests, Dockerfile, structured logging |
| **Deploy + validate backend** | **1.5 hrs** | Railway: FastAPI + Postgres, env vars, run deploy smoke checklist |
| ElevenLabs agent | 30 min | Create agent, configure Data Collection fields, dynamic variables in prompt |
| Frontend | 2-3 hrs | Next.js landing page, panels, audio playback, Tailwind |
| Deploy + polish | 1 hr | Vercel deploy, README, final check |
| **Total** | **~11-13 hrs** | |

### Deploy Smoke Checklist (run after Railway deploy)

- [ ] `GET /health` returns 200 with `"db": "connected"`
- [ ] `POST /webhooks/elevenlabs/post-call` with bad signature → 401
- [ ] `POST /webhooks/elevenlabs/post-call` with valid fixture → 200, profile + snapshot created
- [ ] `POST /webhooks/elevenlabs/conversation-init` with known caller → returns populated dynamic_variables
- [ ] `POST /webhooks/elevenlabs/conversation-init` with unknown caller → returns all keys with empty strings
- [ ] Frontend `NEXT_PUBLIC_API_URL` resolves correctly (no CORS errors)

### Cut list (if time runs short, in order)

1. "Try it yourself" live extraction → replace with static JSON display + note that the production path uses ElevenLabs Data Collection
2. Reduce frontend from 5 panels to 3 (hero + side-by-side comparison + how it works)
3. Mobile responsiveness → reviewer is on laptop
4. Multi-stage Docker → simple single-stage Dockerfile
5. Last resort: trim to 8 tests — but never below webhook + idempotency + conversation-init coverage

### Never cut
- HMAC verification
- Idempotency (transaction ordering + DB constraint)
- Conversation-init webhook with full variable defaults
- Malformed payload rejection
- At least the side-by-side audio comparison (the "aha" moment)

---

## 12. Operational Concerns

### Structured Logging

All webhook events are logged with structured JSON:
- Webhook received: `{ "event": "webhook_received", "conversation_id": "...", "caller_id": "..." }`
- Verification failed: `{ "event": "webhook_auth_failed", "reason": "invalid_signature" }`
- Memory stored: `{ "event": "memory_stored", "caller_id": "...", "conversation_id": "..." }`
- Conversation init served: `{ "event": "conversation_init", "caller_id": "...", "known": true }`

Uses Python `structlog` or standard `logging` with JSON formatter.

### Caller ID Normalization

Inbound `caller_id` is normalized to E.164 on receipt:
- Strip whitespace, dashes, parentheses
- Ensure leading `+` and country code
- If normalization fails, log a warning and use the raw value

This prevents the same caller from creating duplicate profiles due to formatting differences (e.g., `+15551234567` vs `(555) 123-4567`).

### Error Behavior

- Webhook HMAC failure → 401, nothing stored, logged
- Malformed payload → 422, nothing stored, logged
- DB write failure → 500, transaction rolled back, logged
- Conversation-init with unknown caller → 200 with empty-string defaults (not an error)
- Conversation-init with missing caller_id → 400, logged

---

## 13. The Email

**Subject:** Built something for ElevenLabs agents — cross-session memory using your platform primitives

Hi [name],

Your agents forget every caller. The Mem0 integration relies on tool-calling — which means it sometimes doesn't fire.

I built Memory Autopilot: it uses Data Collection to extract structured memory after every call, stores it by caller, and injects it via dynamic variables through the conversation initiation webhook. No tool-calling. No external extraction. Just your platform, wired together.

Demo: [link]
Code: [github link]

30 seconds — click any scenario and hear the difference between memory off and memory on.

German Alvarez

---

## 14. What's Real vs. Pre-Computed

- **Real:** FastAPI backend deployed on Railway. Webhook endpoints work with real HMAC verification. ElevenLabs agent exists with Data Collection configured. "Try it yourself" hits a live API. Postgres stores real data.
- **Pre-computed:** Audio files (ElevenLabs TTS). Transcript display. Demo caller profile seeded in DB.
- **Runnable:** The repo includes documented setup steps. With an ElevenLabs agent, Twilio number, and Railway deploy, it produces working cross-session memory.
