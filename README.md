# Memory Autopilot

Persistent memory for ElevenLabs voice agents — callers are recognized on every call.

## The Problem

ElevenLabs agents start each call with no memory of previous sessions. A customer who called last week about a billing issue is a stranger again. Agents ask for names, repeat troubleshooting steps, and lose context about open actions — the exact frustrations that make automated support worse than human support.

## The Solution

Memory Autopilot uses ElevenLabs' own platform primitives to solve the problem without any third-party memory layer:

- **Data Collection** — the agent extracts structured facts during the call (name, issue, order ID, sentiment, open actions)
- **Post-call webhooks** — ElevenLabs sends the extracted data to the backend after every call
- **Dynamic variables** — before the next call starts, the backend injects the stored profile back into the agent's prompt

No fine-tuning. No vector databases. No prompt hacking. The agent natively knows who it is talking to.

## Architecture

```
Incoming call
     |
     v
ElevenLabs Agent
     |
     | 1. conversation-init webhook (before call)
     v
POST /webhooks/elevenlabs/conversation-init
     |  returns: name, issue history, open actions as dynamic variables
     v
ElevenLabs Agent (context-aware for this session)
     |
     | 2. call happens — agent uses Data Collection to extract facts
     |
     | 3. post-call webhook (after call ends)
     v
POST /webhooks/elevenlabs/post-call  <-- HMAC-verified
     |
     v
FastAPI  -->  Postgres
              caller_profiles    (latest state per phone number)
              memory_snapshots   (append-only call log)
```

## How It Works

**Step 1 — Store:** When a call ends, ElevenLabs sends the conversation's `data_collection_results` to `POST /webhooks/elevenlabs/post-call`. The backend upserts a caller profile keyed by phone number.

**Step 2 — Inject:** When a new call starts, ElevenLabs hits `POST /webhooks/elevenlabs/conversation-init` with the caller's phone number. The backend looks up the profile and returns it as dynamic variables.

**Step 3 — Greet:** The agent's system prompt includes `{{customer_name}}`, `{{issue_summary}}`, `{{open_actions}}`, etc. The agent greets the caller by name, references their last issue, and picks up open actions — without asking them to repeat themselves.

## Project Structure

```
residesk/
  backend/        FastAPI service — webhooks, memory storage, demo API
    app/
      routers/    webhooks.py, demo.py, health.py
      services/   memory.py, webhook_auth.py, demo_extraction.py
      models/     schemas.py
    tests/        test_webhooks.py, test_memory.py, test_demo_extraction.py
    schema.sql    Postgres schema (caller_profiles + memory_snapshots)
    Dockerfile
  frontend/       Next.js landing page + interactive demo
    app/
  scripts/        seed_data.py, generate_audio.py
  data/
    transcripts/  sample call transcripts
    memory/       seeded caller profiles
```

## Quick Start

See [backend/README.md](backend/README.md) for full setup instructions, API reference, and deployment guide.

**Short version:**
```bash
cd backend
pip install -r requirements.txt
psql $DATABASE_URL < schema.sql
uvicorn app.main:app --reload
```

## Live Demo

Coming soon.

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI, uvicorn |
| Database | Postgres 16, asyncpg |
| Memory extraction (demo) | Anthropic Claude (claude-sonnet-4-6) |
| Voice agent | ElevenLabs Conversational AI |
| Frontend | Next.js, Tailwind CSS |
| Deployment | Railway (backend), Vercel (frontend) |

## Built By

German Alvarez
