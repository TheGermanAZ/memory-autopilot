# Memory Autopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a spearfish demo showing cross-session memory for ElevenLabs voice agents, with a real Python backend and a polished landing page.

**Architecture:** FastAPI backend on Railway receives ElevenLabs webhooks (post-call + conversation-init), stores caller memory in Postgres, and returns dynamic variables. Next.js frontend on Vercel shows the demo story with pre-computed audio. Demo extraction endpoint lets visitors try the API live.

**Tech Stack:** Python 3.12, FastAPI, asyncpg, Postgres, structlog, Docker | Next.js 14, Tailwind CSS, TypeScript | ElevenLabs TTS API, Claude API (demo extraction only)

**Spec:** `docs/superpowers/specs/2026-03-27-memory-autopilot-design.md`

---

## File Map

### Backend (`backend/`)

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, CORS, lifespan (DB pool init/close), mount routers |
| `app/config.py` | Pydantic Settings: DATABASE_URL, ELEVENLABS_WEBHOOK_SECRET, ELEVENLABS_AGENT_ID, ALLOWED_ORIGINS, ANTHROPIC_API_KEY |
| `app/db.py` | asyncpg connection pool: init, close, get_pool |
| `app/models/schemas.py` | All Pydantic models from spec Section 6 |
| `app/services/webhook_auth.py` | HMAC signature verification using ElevenLabs-Signature header |
| `app/services/memory.py` | Caller profile upsert, snapshot insert, profile lookup, idempotent transaction |
| `app/services/demo_extraction.py` | Demo-only Claude extraction from raw transcript |
| `app/services/phone.py` | E.164 caller ID normalization |
| `app/routers/webhooks.py` | POST /webhooks/elevenlabs/post-call, POST /webhooks/elevenlabs/conversation-init |
| `app/routers/demo.py` | GET /api/demo/memory/{caller_id}, POST /api/demo/extract |
| `app/routers/health.py` | GET /health |
| `schema.sql` | CREATE TABLE statements from spec Section 5 |
| `tests/conftest.py` | Docker Postgres fixture, TestClient factory, HMAC helper |
| `tests/test_webhooks.py` | 8 webhook tests |
| `tests/test_memory.py` | 2 memory service tests |
| `tests/test_demo_extraction.py` | 1 demo extraction test |
| `Dockerfile` | Single-stage Python 3.12 image |
| `requirements.txt` | All dependencies |

### Frontend (`frontend/`)

| File | Responsibility |
|---|---|
| `app/layout.tsx` | Root layout, fonts, metadata |
| `app/page.tsx` | Landing page, assembles all panels |
| `app/components/AudioPlayer.tsx` | Play button for a single audio clip |
| `app/components/TranscriptPanel.tsx` | Panel 1: Call 1 transcript with audio per line |
| `app/components/MemoryCard.tsx` | Panel 2: Animated JSON extraction card |
| `app/components/ComparisonPanel.tsx` | Panel 3: Side-by-side with toggle |
| `app/components/HowItWorks.tsx` | Panel 4: Architecture diagram + code snippets |
| `app/components/TryItYourself.tsx` | Panel 5: Live API demo |
| `public/audio/` | Pre-computed TTS .mp3 files |

### Scripts & Data

| File | Responsibility |
|---|---|
| `scripts/generate_audio.py` | Generate TTS audio via ElevenLabs API |
| `scripts/seed_data.py` | Insert demo caller profile + snapshot into Postgres |
| `data/transcripts/call1.json` | Call 1 transcript (Sarah's billing complaint) |
| `data/transcripts/call2_without_memory.json` | Call 2 without memory |
| `data/transcripts/call2_with_memory.json` | Call 2 with memory |
| `data/memory/sarah_chen.json` | Demo extracted memory |
| `data/agent_config.json` | ElevenLabs agent reference config |

---

## Task 1: Project Scaffold + Schema

**Files:**
- Create: `backend/schema.sql`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/{routers,services,models} backend/tests
touch backend/app/__init__.py backend/app/routers/__init__.py \
      backend/app/services/__init__.py backend/app/models/__init__.py
```

- [ ] **Step 2: Write schema.sql**

Create `backend/schema.sql` with the two-table schema from spec Section 5 exactly.

```sql
CREATE TABLE IF NOT EXISTS caller_profiles (
    caller_id           TEXT PRIMARY KEY,
    customer_name       TEXT NOT NULL DEFAULT '',
    issue_summary       TEXT NOT NULL DEFAULT '',
    issue_type          TEXT NOT NULL DEFAULT '',
    order_id            TEXT NOT NULL DEFAULT '',
    customer_sentiment  TEXT NOT NULL DEFAULT '',
    open_actions        TEXT NOT NULL DEFAULT '',
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_snapshots (
    conversation_id     TEXT PRIMARY KEY,
    caller_id           TEXT NOT NULL REFERENCES caller_profiles(caller_id),
    agent_id            TEXT,
    source              TEXT NOT NULL,
    data_collection     JSONB NOT NULL,
    transcript_summary  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_caller
    ON memory_snapshots (caller_id, created_at DESC);
```

- [ ] **Step 3: Write requirements.txt**

Create `backend/requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
asyncpg==0.30.0
pydantic==2.10.0
pydantic-settings==2.7.0
structlog==24.4.0
httpx==0.28.0
anthropic==0.43.0
pytest==8.3.0
pytest-asyncio==0.25.0
testcontainers[postgres]==4.9.0
```

- [ ] **Step 4: Write config.py**

Create `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost:5432/memory_autopilot"
    elevenlabs_webhook_secret: str = ""
    elevenlabs_agent_id: str = ""
    allowed_origins: str = "http://localhost:3000"
    anthropic_api_key: str = ""
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 5: Write Pydantic models**

Create `backend/app/models/schemas.py` with all models from spec Section 6:

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


class PostCallWebhookPayload(BaseModel):
    """Shape of the ElevenLabs post-call transcription webhook."""
    agent_id: str
    conversation_id: str
    status: str | None = None
    transcript: list[dict] | None = None
    analysis: dict | None = None

    def get_data_collection_results(self) -> dict:
        if self.analysis and "data_collection_results" in self.analysis:
            return self.analysis["data_collection_results"]
        return {}

    def get_transcript_summary(self) -> str | None:
        if self.analysis:
            return self.analysis.get("transcript_summary")
        return None


class ConversationInitPayload(BaseModel):
    caller_id: str
    agent_id: str
    called_number: str | None = None
    call_sid: str | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str
```

- [ ] **Step 6: Commit scaffold**

```bash
git add backend/
git commit -m "feat: backend scaffold — schema, models, config, requirements"
```

---

## Task 2: Database Layer + Phone Normalization

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/services/phone.py`

- [ ] **Step 1: Write db.py**

Create `backend/app/db.py`:

```python
import asyncpg
import structlog
from app.config import settings

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    logger.info("db_pool_initialized")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("db_pool_closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool
```

- [ ] **Step 2: Write phone normalization**

Create `backend/app/services/phone.py`:

```python
import re
import structlog

logger = structlog.get_logger()


def normalize_e164(raw: str) -> str:
    """Normalize a phone number to E.164 format.

    Strips formatting characters. If the result starts with +, returns as-is.
    Otherwise prepends +1 (US default for demo).
    Logs a warning if normalization looks unreliable.
    """
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if not digits:
        logger.warning("phone_normalization_failed", raw=raw)
        return raw.strip()
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    logger.warning("phone_normalization_ambiguous", raw=raw, digits=digits)
    return f"+{digits}"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/db.py backend/app/services/phone.py
git commit -m "feat: database pool + E.164 phone normalization"
```

---

## Task 3: HMAC Webhook Auth

**Files:**
- Create: `backend/app/services/webhook_auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_webhooks.py` (first 2 tests)

- [ ] **Step 1: Write the HMAC verification test (failing)**

Create `backend/tests/conftest.py`:

```python
import asyncio
import hashlib
import hmac
import json
import os
import time
from typing import AsyncGenerator

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

WEBHOOK_SECRET = "test-webhook-secret-1234"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
async def db_pool(postgres_container) -> AsyncGenerator[asyncpg.Pool, None]:
    url = postgres_container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    with open(schema_path) as f:
        await pool.execute(f.read())
    yield pool
    await pool.close()


@pytest.fixture(autouse=True)
async def clean_tables(db_pool):
    yield
    await db_pool.execute("DELETE FROM memory_snapshots")
    await db_pool.execute("DELETE FROM caller_profiles")


@pytest.fixture
async def client(db_pool, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DATABASE_URL", "unused")
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Force settings reload with test env vars
    from app import config as config_module
    config_module.settings = config_module.Settings()

    from app.main import app
    from app import db as db_module
    db_module._pool = db_pool

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def sign_payload(payload: dict, secret: str = WEBHOOK_SECRET) -> dict:
    """Generate ElevenLabs-Signature header for a payload."""
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    sig_payload = f"{timestamp}.{body.decode()}"
    signature = hmac.new(secret.encode(), sig_payload.encode(), hashlib.sha256).hexdigest()
    return {
        "ElevenLabs-Signature": f"t={timestamp},v1={signature}",
        "Content-Type": "application/json",
    }


def make_post_call_payload(
    conversation_id: str = "conv_001",
    caller_id: str = "+15551234567",
    agent_id: str = "agent_test",
) -> dict:
    return {
        "agent_id": agent_id,
        "conversation_id": conversation_id,
        "status": "done",
        "transcript": [
            {"role": "user", "message": "Hi, my name is Sarah Chen."},
            {"role": "agent", "message": "Hello Sarah, how can I help?"},
        ],
        "analysis": {
            "transcript_summary": "Customer called about a billing issue.",
            "data_collection_results": {
                "customer_name": "Sarah Chen",
                "issue_type": "billing",
                "issue_summary": "Double charged for premium plan",
                "order_id": "ORD-4521",
                "customer_sentiment": "frustrated",
                "open_actions": "Refund pending",
            },
        },
        "metadata": {
            "phone": {"caller_id": caller_id},
        },
    }
```

Create `backend/tests/test_webhooks.py` with the first 2 tests:

```python
import pytest
from tests.conftest import sign_payload, make_post_call_payload, WEBHOOK_SECRET

pytestmark = pytest.mark.asyncio


async def test_post_call_webhook_stores_memory(client, db_pool):
    payload = make_post_call_payload()
    headers = sign_payload(payload)
    resp = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp.status_code == 200

    profile = await db_pool.fetchrow(
        "SELECT * FROM caller_profiles WHERE caller_id = $1", "+15551234567"
    )
    assert profile is not None
    assert profile["customer_name"] == "Sarah Chen"
    assert profile["issue_type"] == "billing"

    snapshot = await db_pool.fetchrow(
        "SELECT * FROM memory_snapshots WHERE conversation_id = $1", "conv_001"
    )
    assert snapshot is not None
    assert snapshot["source"] == "webhook"


async def test_post_call_webhook_rejects_invalid_signature(client, db_pool):
    payload = make_post_call_payload()
    headers = sign_payload(payload, secret="wrong-secret")
    resp = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp.status_code == 401

    count = await db_pool.fetchval("SELECT COUNT(*) FROM caller_profiles")
    assert count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_webhooks.py -v`
Expected: ImportError or FAIL — app/main.py and webhook_auth.py don't exist yet.

- [ ] **Step 3: Write webhook_auth.py**

Create `backend/app/services/webhook_auth.py`:

```python
import hashlib
import hmac
import time

import structlog
from fastapi import HTTPException, Request

from app.config import settings

logger = structlog.get_logger()

MAX_TIMESTAMP_AGE_SECONDS = 300  # 5 minutes


async def verify_elevenlabs_signature(request: Request) -> bytes:
    """Verify ElevenLabs webhook HMAC signature. Returns raw body on success."""
    sig_header = request.headers.get("ElevenLabs-Signature", "")
    if not sig_header:
        logger.warning("webhook_auth_failed", reason="missing_signature_header")
        raise HTTPException(status_code=401, detail="Missing signature")

    body = await request.body()

    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t", "")
    signature = parts.get("v1", "")

    if not timestamp or not signature:
        logger.warning("webhook_auth_failed", reason="malformed_signature_header")
        raise HTTPException(status_code=401, detail="Malformed signature")

    # Check timestamp freshness
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > MAX_TIMESTAMP_AGE_SECONDS:
            logger.warning("webhook_auth_failed", reason="stale_timestamp")
            raise HTTPException(status_code=401, detail="Stale timestamp")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    # Verify HMAC
    sig_payload = f"{timestamp}.{body.decode()}"
    expected = hmac.new(
        settings.elevenlabs_webhook_secret.encode(),
        sig_payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        logger.warning("webhook_auth_failed", reason="invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("webhook_auth_success")
    return body
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/webhook_auth.py backend/tests/
git commit -m "feat: HMAC webhook auth + test fixtures"
```

---

## Task 4: Memory Service

**Files:**
- Create: `backend/app/services/memory.py`
- Create: `backend/tests/test_memory.py`

- [ ] **Step 1: Write failing memory tests**

Create `backend/tests/test_memory.py`:

```python
import pytest
from app.services.memory import store_post_call_memory, get_caller_profile

pytestmark = pytest.mark.asyncio


async def test_create_caller_profile(db_pool):
    data_collection = {
        "customer_name": "Sarah Chen",
        "issue_type": "billing",
        "issue_summary": "Double charged",
        "order_id": "ORD-4521",
        "customer_sentiment": "frustrated",
        "open_actions": "Refund pending",
    }
    inserted = await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_100",
        caller_id="+15551234567",
        agent_id="agent_test",
        data_collection=data_collection,
        transcript_summary="Billing issue call.",
    )
    assert inserted is True

    profile = await get_caller_profile(db_pool, "+15551234567")
    assert profile is not None
    assert profile["customer_name"] == "Sarah Chen"


async def test_update_existing_profile(db_pool):
    data1 = {
        "customer_name": "Sarah Chen",
        "issue_type": "billing",
        "issue_summary": "Double charged",
        "order_id": "ORD-4521",
        "customer_sentiment": "frustrated",
        "open_actions": "Refund pending",
    }
    await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_200",
        caller_id="+15559999999",
        agent_id="agent_test",
        data_collection=data1,
        transcript_summary="First call.",
    )

    data2 = {
        "customer_name": "Sarah Chen",
        "issue_type": "technical",
        "issue_summary": "App crashing on login",
        "order_id": "",
        "customer_sentiment": "neutral",
        "open_actions": "Escalated to engineering",
    }
    await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_201",
        caller_id="+15559999999",
        agent_id="agent_test",
        data_collection=data2,
        transcript_summary="Second call.",
    )

    profile = await get_caller_profile(db_pool, "+15559999999")
    assert profile["issue_type"] == "technical"
    assert profile["issue_summary"] == "App crashing on login"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_memory.py -v`
Expected: ImportError — memory.py doesn't exist.

- [ ] **Step 3: Write memory.py**

Create `backend/app/services/memory.py`:

```python
import json

import asyncpg
import structlog

logger = structlog.get_logger()

PROFILE_FIELDS = [
    "customer_name",
    "issue_summary",
    "issue_type",
    "order_id",
    "customer_sentiment",
    "open_actions",
]

DEFAULT_PROFILE = {field: "" for field in PROFILE_FIELDS}


async def store_post_call_memory(
    pool: asyncpg.Pool,
    conversation_id: str,
    caller_id: str,
    agent_id: str | None,
    data_collection: dict,
    transcript_summary: str | None,
) -> bool:
    """Store memory from a post-call webhook. Returns True if new, False if duplicate."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Ensure caller profile exists (FK requirement)
            await conn.execute(
                """
                INSERT INTO caller_profiles (caller_id)
                VALUES ($1)
                ON CONFLICT (caller_id) DO NOTHING
                """,
                caller_id,
            )

            # 2. Insert snapshot (idempotent by conversation_id)
            result = await conn.execute(
                """
                INSERT INTO memory_snapshots
                    (conversation_id, caller_id, agent_id, source, data_collection, transcript_summary)
                VALUES ($1, $2, $3, 'webhook', $4, $5)
                ON CONFLICT (conversation_id) DO NOTHING
                """,
                conversation_id,
                caller_id,
                agent_id,
                json.dumps(data_collection),
                transcript_summary,
            )

            # 3. Only update profile if snapshot was actually inserted
            row_count = int(result.split()[-1])
            if row_count == 0:
                logger.info("duplicate_webhook_ignored", conversation_id=conversation_id)
                return False

            # Update profile with latest data collection fields
            await conn.execute(
                """
                UPDATE caller_profiles SET
                    customer_name = COALESCE(NULLIF($2, ''), customer_name),
                    issue_summary = COALESCE(NULLIF($3, ''), issue_summary),
                    issue_type = COALESCE(NULLIF($4, ''), issue_type),
                    order_id = COALESCE(NULLIF($5, ''), order_id),
                    customer_sentiment = COALESCE(NULLIF($6, ''), customer_sentiment),
                    open_actions = COALESCE(NULLIF($7, ''), open_actions),
                    updated_at = now()
                WHERE caller_id = $1
                """,
                caller_id,
                data_collection.get("customer_name", ""),
                data_collection.get("issue_summary", ""),
                data_collection.get("issue_type", ""),
                data_collection.get("order_id", ""),
                data_collection.get("customer_sentiment", ""),
                data_collection.get("open_actions", ""),
            )

            logger.info(
                "memory_stored",
                conversation_id=conversation_id,
                caller_id=caller_id,
            )
            return True


async def get_caller_profile(pool: asyncpg.Pool, caller_id: str) -> dict | None:
    """Get caller profile. Returns dict or None if unknown caller."""
    row = await pool.fetchrow(
        "SELECT * FROM caller_profiles WHERE caller_id = $1",
        caller_id,
    )
    if row is None:
        return None
    return dict(row)


def profile_to_dynamic_vars(profile: dict | None, caller_id: str = "") -> dict[str, str]:
    """Convert a caller profile to ElevenLabs dynamic variables.
    Always returns ALL keys — empty strings for unknown callers.
    Includes caller_phone so it round-trips back in the post-call webhook."""
    if profile is None:
        result = dict(DEFAULT_PROFILE)
    else:
        result = {field: str(profile.get(field, "")) for field in PROFILE_FIELDS}
    result["caller_phone"] = caller_id
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_memory.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/memory.py backend/tests/test_memory.py
git commit -m "feat: memory service — profile upsert, snapshot storage, idempotent transactions"
```

---

## Task 5: Webhook Router + Remaining Webhook Tests

**Files:**
- Create: `backend/app/routers/webhooks.py`
- Create: `backend/app/main.py`
- Update: `backend/tests/test_webhooks.py` (add remaining 6 tests)

- [ ] **Step 1: Write webhooks router**

Create `backend/app/routers/webhooks.py`:

```python
import json

import structlog
from fastapi import APIRouter, Request, Response

from app.db import get_pool
from app.models.schemas import (
    ConversationInitPayload,
    DynamicVariablesResponse,
    PostCallWebhookPayload,
)
from app.services.memory import get_caller_profile, profile_to_dynamic_vars, store_post_call_memory
from app.services.phone import normalize_e164
from app.services.webhook_auth import verify_elevenlabs_signature

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])


@router.post("/post-call")
async def post_call_webhook(request: Request):
    body = await verify_elevenlabs_signature(request)

    try:
        payload = PostCallWebhookPayload.model_validate_json(body)
    except Exception:
        logger.warning("webhook_malformed_payload")
        return Response(status_code=422, content="Malformed payload")

    data_collection = payload.get_data_collection_results()
    transcript_summary = payload.get_transcript_summary()

    # Extract caller_id from conversation_initiation_client_data.
    # When a call arrives, our conversation-init webhook returns caller_phone
    # as a dynamic variable. ElevenLabs round-trips it back in the post-call payload.
    raw_data = json.loads(body)
    init_data = raw_data.get("conversation_initiation_client_data", {})
    dynamic_vars = init_data.get("dynamic_variables", {})
    raw_caller_id = dynamic_vars.get("caller_phone", "")

    # Fallback: check metadata for phone info (Twilio calls)
    if not raw_caller_id:
        raw_caller_id = raw_data.get("metadata", {}).get("phone", {}).get("caller_id", "")

    if not raw_caller_id:
        logger.warning("post_call_no_caller_id", conversation_id=payload.conversation_id)
        raw_caller_id = f"unknown_{payload.conversation_id}"

    caller_id = normalize_e164(raw_caller_id)

    pool = get_pool()
    inserted = await store_post_call_memory(
        pool=pool,
        conversation_id=payload.conversation_id,
        caller_id=caller_id,
        agent_id=payload.agent_id,
        data_collection=data_collection,
        transcript_summary=transcript_summary,
    )

    logger.info(
        "webhook_received",
        conversation_id=payload.conversation_id,
        caller_id=caller_id,
        new=inserted,
    )
    return {"status": "ok", "new": inserted}


@router.post("/conversation-init")
async def conversation_init(request: Request):
    body = await request.json()

    raw_caller_id = body.get("caller_id", "")
    if not raw_caller_id:
        logger.warning("conversation_init_missing_caller_id")
        return Response(status_code=400, content="Missing caller_id")

    caller_id = normalize_e164(raw_caller_id)
    pool = get_pool()
    profile = await get_caller_profile(pool, caller_id)
    dynamic_vars = profile_to_dynamic_vars(profile, caller_id=caller_id)

    logger.info(
        "conversation_init",
        caller_id=caller_id,
        known=profile is not None,
    )

    return DynamicVariablesResponse(dynamic_variables=dynamic_vars)
```

- [ ] **Step 2: Write main.py**

Create `backend/app/main.py`:

```python
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_pool, close_pool
from app.routers import webhooks, health

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Memory Autopilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(health.router)
```

- [ ] **Step 3: Write health router**

Create `backend/app/routers/health.py`:

```python
from app.db import get_pool
from app.models.schemas import HealthResponse
from fastapi import APIRouter

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health_check() -> HealthResponse:
    try:
        pool = get_pool()
        await pool.fetchval("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(status="ok", db=db_status, version="0.1.0")
```

- [ ] **Step 4: Add remaining 6 webhook tests**

Append to `backend/tests/test_webhooks.py`:

```python
async def test_post_call_webhook_rejects_malformed_payload(client, db_pool):
    payload = {"garbage": True}
    headers = sign_payload(payload)
    resp = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp.status_code == 422

    count = await db_pool.fetchval("SELECT COUNT(*) FROM caller_profiles")
    assert count == 0


async def test_post_call_webhook_idempotent(client, db_pool):
    payload = make_post_call_payload(conversation_id="conv_idem")
    headers = sign_payload(payload)

    resp1 = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["new"] is True

    headers2 = sign_payload(payload)  # re-sign with fresh timestamp
    resp2 = await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers2)
    assert resp2.status_code == 200
    assert resp2.json()["new"] is False

    snapshot_count = await db_pool.fetchval("SELECT COUNT(*) FROM memory_snapshots")
    assert snapshot_count == 1


async def test_post_call_idempotency_enforced_by_db_constraint(db_pool):
    """Verify the UNIQUE constraint on conversation_id catches duplicates at DB level."""
    from app.services.memory import store_post_call_memory

    data = {"customer_name": "Test", "issue_type": "test"}
    await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_unique",
        caller_id="+15550000001",
        agent_id="agent_test",
        data_collection=data,
        transcript_summary="Test",
    )
    # Second insert with same conversation_id should return False, not raise
    result = await store_post_call_memory(
        pool=db_pool,
        conversation_id="conv_unique",
        caller_id="+15550000001",
        agent_id="agent_test",
        data_collection=data,
        transcript_summary="Test",
    )
    assert result is False


async def test_conversation_init_returns_dynamic_vars(client, db_pool):
    # Seed a known caller
    payload = make_post_call_payload(conversation_id="conv_init_test", caller_id="+15553334444")
    headers = sign_payload(payload)
    await client.post("/webhooks/elevenlabs/post-call", json=payload, headers=headers)

    resp = await client.post(
        "/webhooks/elevenlabs/conversation-init",
        json={"caller_id": "+15553334444", "agent_id": "agent_test"},
    )
    assert resp.status_code == 200
    dv = resp.json()["dynamic_variables"]
    assert dv["customer_name"] == "Sarah Chen"
    assert dv["issue_type"] == "billing"
    assert "issue_summary" in dv
    assert "order_id" in dv
    assert "customer_sentiment" in dv
    assert "open_actions" in dv


async def test_conversation_init_unknown_caller(client):
    resp = await client.post(
        "/webhooks/elevenlabs/conversation-init",
        json={"caller_id": "+10000000000", "agent_id": "agent_test"},
    )
    assert resp.status_code == 200
    dv = resp.json()["dynamic_variables"]
    assert dv["customer_name"] == ""
    assert dv["issue_summary"] == ""
    assert dv["caller_phone"] == "+10000000000"
    assert len(dv) == 7  # 6 profile fields + caller_phone


async def test_conversation_init_missing_caller_id(client):
    resp = await client.post(
        "/webhooks/elevenlabs/conversation-init",
        json={"agent_id": "agent_test"},
    )
    assert resp.status_code == 400
```

- [ ] **Step 5: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 10 PASSED (2 webhook + 2 memory + 6 new webhook)

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: webhook router, health check, all 10 tests passing"
```

---

## Task 6: Demo Router (Extract + Memory Lookup)

**Files:**
- Create: `backend/app/services/demo_extraction.py`
- Create: `backend/app/routers/demo.py`
- Update: `backend/app/main.py` (mount demo router)
- Create: `backend/tests/test_demo_extraction.py`

- [ ] **Step 1: Write failing demo extraction test**

Create `backend/tests/test_demo_extraction.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


async def test_extract_returns_structured_fields(client):
    mock_response = AsyncMock()
    mock_response.content = [
        AsyncMock(text='{"customer_name":"Sarah Chen","issue_type":"billing","issue_summary":"Double charged","order_id":"ORD-4521","customer_sentiment":"frustrated","open_actions":"Refund pending"}')
    ]

    with patch("app.services.demo_extraction.get_anthropic_client") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        resp = await client.post(
            "/api/demo/extract",
            json={"transcript": "Customer: Hi, my name is Sarah Chen. I was double charged."},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_name"] == "Sarah Chen"
    assert data["issue_type"] == "billing"
```

- [ ] **Step 2: Write demo_extraction.py**

Create `backend/app/services/demo_extraction.py`:

```python
"""Demo-only extraction. NOT the production path.
Production uses ElevenLabs native Data Collection via post-call webhooks."""

import json
import anthropic
import structlog
from app.config import settings

logger = structlog.get_logger()

EXTRACTION_PROMPT = """Extract structured memory from this support call transcript.
Return ONLY valid JSON with these exact keys:
- customer_name: string (full name or empty string)
- issue_type: string (billing, technical, general, complaint)
- issue_summary: string (one sentence)
- order_id: string (order/reference number or empty string)
- customer_sentiment: string (frustrated, neutral, satisfied, angry, anxious)
- open_actions: string (promised follow-ups or empty string)

Only include facts explicitly stated in the transcript."""


def get_anthropic_client():
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def extract_memory_from_transcript(transcript: str) -> dict:
    """Demo-only: extract structured memory from a raw transcript via Claude."""
    client = get_anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": transcript}],
        system=EXTRACTION_PROMPT,
    )
    text = response.content[0].text
    return json.loads(text)
```

- [ ] **Step 3: Write demo router**

Create `backend/app/routers/demo.py`:

```python
import structlog
from fastapi import APIRouter, HTTPException

from app.db import get_pool
from app.models.schemas import (
    CallerProfile,
    DemoExtractionRequest,
    DemoExtractionResponse,
)
from app.services.demo_extraction import extract_memory_from_transcript
from app.services.memory import get_caller_profile

logger = structlog.get_logger()
router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/memory/{caller_id}")
async def get_demo_memory(caller_id: str) -> CallerProfile:
    pool = get_pool()
    profile = await get_caller_profile(pool, caller_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Caller not found")
    return CallerProfile(**profile)


@router.post("/extract")
async def demo_extract(req: DemoExtractionRequest) -> DemoExtractionResponse:
    """Demo-only endpoint. Production uses ElevenLabs Data Collection."""
    try:
        result = await extract_memory_from_transcript(req.transcript)
        return DemoExtractionResponse(**result)
    except Exception as e:
        logger.error("demo_extraction_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Extraction failed")
```

- [ ] **Step 4: Mount demo router in main.py**

Add to `backend/app/main.py` imports:

```python
from app.routers import webhooks, health, demo
```

Add after existing router includes:

```python
app.include_router(demo.router)
```

- [ ] **Step 5: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 11 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: demo router — extract endpoint + memory lookup"
```

---

## Task 7: Dockerfile + Seed Script

**Files:**
- Create: `backend/Dockerfile`
- Create: `scripts/seed_data.py`
- Create: `data/transcripts/call1.json`
- Create: `data/transcripts/call2_without_memory.json`
- Create: `data/transcripts/call2_with_memory.json`
- Create: `data/memory/sarah_chen.json`

- [ ] **Step 1: Write Dockerfile**

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write transcript data files**

Create `data/transcripts/call1.json`:

```json
{
  "lines": [
    {"role": "customer", "text": "Hi, my name is Sarah Chen. I'm calling about my March invoice — I was charged twice for the premium plan.", "audio": "call1_customer_01.mp3"},
    {"role": "agent", "text": "I'm sorry to hear that, Sarah. Can you give me your order number?", "audio": "call1_agent_01.mp3"},
    {"role": "customer", "text": "It's ORD-4521. This is really frustrating, I've been a customer for two years and this is the second time this has happened.", "audio": "call1_customer_02.mp3"},
    {"role": "agent", "text": "I understand your frustration. Let me look into order ORD-4521. I can see the duplicate charge. I'm going to escalate this to our billing team and they'll process a refund within 48 hours.", "audio": "call1_agent_02.mp3"},
    {"role": "customer", "text": "Okay, thank you. Please make sure someone actually follows up this time.", "audio": "call1_customer_03.mp3"},
    {"role": "agent", "text": "Absolutely, Sarah. I've noted that follow-up is important to you. You'll hear from us within 48 hours. Is there anything else I can help with?", "audio": "call1_agent_03.mp3"},
    {"role": "customer", "text": "No, that's all. Thank you.", "audio": "call1_customer_04.mp3"}
  ]
}
```

Create `data/transcripts/call2_without_memory.json`:

```json
{
  "lines": [
    {"role": "agent", "text": "Thank you for calling support, how can I help you today?", "audio": "call2_no_mem_agent_01.mp3"},
    {"role": "customer", "text": "Hi, this is Sarah Chen. I called two days ago about a double charge on my account.", "audio": "call2_no_mem_customer_01.mp3"},
    {"role": "agent", "text": "I'm sorry to hear that. Can you tell me your order number and what the issue was?", "audio": "call2_no_mem_agent_02.mp3"},
    {"role": "customer", "text": "It's ORD-4521. I was charged twice for the premium plan. Someone was supposed to process a refund.", "audio": "call2_no_mem_customer_02.mp3"}
  ]
}
```

Create `data/transcripts/call2_with_memory.json`:

```json
{
  "lines": [
    {"role": "agent", "text": "Hi Sarah, welcome back. I can see you called two days ago about a double charge on order ORD-4521. Let me check on the status of your refund.", "audio": "call2_mem_agent_01.mp3"},
    {"role": "customer", "text": "Oh wow, yes, that's exactly right. Has the refund been processed?", "audio": "call2_mem_customer_01.mp3"},
    {"role": "agent", "text": "It looks like the refund was processed yesterday. Can you check your account to confirm you see it?", "audio": "call2_mem_agent_02.mp3"},
    {"role": "customer", "text": "Let me check... yes, I see it. Thank you so much for following up.", "audio": "call2_mem_customer_02.mp3"}
  ]
}
```

- [ ] **Step 3: Write extracted memory data**

Create `data/memory/sarah_chen.json`:

```json
{
  "customer_name": "Sarah Chen",
  "issue_type": "billing",
  "issue_summary": "Double charged for premium plan",
  "order_id": "ORD-4521",
  "customer_sentiment": "frustrated",
  "open_actions": "Refund pending — follow up within 48 hours"
}
```

- [ ] **Step 4: Write seed script**

Create `scripts/seed_data.py`:

```python
"""Seed the database with demo caller data."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import asyncpg


async def seed(database_url: str):
    conn = await asyncpg.connect(database_url)

    with open("data/memory/sarah_chen.json") as f:
        memory = json.load(f)

    # Upsert caller profile
    await conn.execute(
        """
        INSERT INTO caller_profiles (caller_id, customer_name, issue_summary, issue_type, order_id, customer_sentiment, open_actions)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (caller_id) DO UPDATE SET
            customer_name = $2, issue_summary = $3, issue_type = $4,
            order_id = $5, customer_sentiment = $6, open_actions = $7,
            updated_at = now()
        """,
        "+15551234567",
        memory["customer_name"],
        memory["issue_summary"],
        memory["issue_type"],
        memory["order_id"],
        memory["customer_sentiment"],
        memory["open_actions"],
    )

    # Insert demo snapshot
    await conn.execute(
        """
        INSERT INTO memory_snapshots (conversation_id, caller_id, agent_id, source, data_collection, transcript_summary)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (conversation_id) DO NOTHING
        """,
        "demo_call_001",
        "+15551234567",
        "demo_agent",
        "demo",
        json.dumps(memory),
        "Customer called about a duplicate charge on premium plan order ORD-4521.",
    )

    await conn.close()
    print("Seeded demo data for Sarah Chen (+15551234567)")


if __name__ == "__main__":
    url = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/memory_autopilot")
    asyncio.run(seed(url))
```

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile scripts/ data/
git commit -m "feat: Dockerfile, transcript data, seed script"
```

---

## Task 8: Audio Generation Script

**Files:**
- Create: `scripts/generate_audio.py`

- [ ] **Step 1: Write audio generation script**

Create `scripts/generate_audio.py`:

```python
"""Generate TTS audio for all transcript lines via ElevenLabs API."""
import json
import os
import sys
from pathlib import Path

from elevenlabs import ElevenLabs

# Voice IDs — pick two distinct stock voices
CUSTOMER_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah (female)
AGENT_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel (male)

OUTPUT_DIR = Path("frontend/public/audio")


def generate_audio(client: ElevenLabs, text: str, voice_id: str, filename: str):
    output_path = OUTPUT_DIR / filename
    if output_path.exists():
        print(f"  Skipping {filename} (already exists)")
        return

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    print(f"  Generated {filename}")


def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: Set ELEVENLABS_API_KEY environment variable")
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcript_files = [
        "data/transcripts/call1.json",
        "data/transcripts/call2_without_memory.json",
        "data/transcripts/call2_with_memory.json",
    ]

    for tf in transcript_files:
        print(f"\nProcessing {tf}...")
        with open(tf) as f:
            data = json.load(f)

        for line in data["lines"]:
            voice_id = CUSTOMER_VOICE_ID if line["role"] == "customer" else AGENT_VOICE_ID
            generate_audio(client, line["text"], voice_id, line["audio"])

    print(f"\nDone! Audio files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/generate_audio.py
git commit -m "feat: ElevenLabs TTS audio generation script"
```

---

## Task 9: Frontend Scaffold + Layout

**Files:**
- Create: `frontend/` via `npx create-next-app`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx` (shell)

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd /Users/thegermanaz/p/js/residesk
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --no-git
```

- [ ] **Step 2: Create component directory**

```bash
mkdir -p frontend/app/components
```

- [ ] **Step 3: Copy transcript data for frontend access**

The frontend imports transcript JSON directly. Ensure `data/` is accessible or copy relevant files:

```bash
mkdir -p frontend/public/audio
# Audio will be generated by scripts/generate_audio.py later
```

- [ ] **Step 4: Commit scaffold**

```bash
git add frontend/
git commit -m "feat: Next.js frontend scaffold"
```

---

## Task 10: Frontend Components — AudioPlayer + TranscriptPanel

**Files:**
- Create: `frontend/app/components/AudioPlayer.tsx`
- Create: `frontend/app/components/TranscriptPanel.tsx`

- [ ] **Step 1: Write AudioPlayer**

Create `frontend/app/components/AudioPlayer.tsx`:

```tsx
"use client";

import { useRef, useState } from "react";

interface AudioPlayerProps {
  src: string;
  size?: "sm" | "md";
}

export function AudioPlayer({ src, size = "sm" }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      audio.currentTime = 0;
      setPlaying(false);
    } else {
      audio.play();
      setPlaying(true);
    }
  };

  return (
    <>
      <audio
        ref={audioRef}
        src={src}
        onEnded={() => setPlaying(false)}
        preload="none"
      />
      <button
        onClick={toggle}
        className={`inline-flex items-center justify-center rounded-full transition-colors ${
          size === "sm" ? "w-7 h-7 text-xs" : "w-9 h-9 text-sm"
        } ${
          playing
            ? "bg-white text-black"
            : "bg-white/10 text-white hover:bg-white/20"
        }`}
        aria-label={playing ? "Stop" : "Play"}
      >
        {playing ? "■" : "▶"}
      </button>
    </>
  );
}
```

- [ ] **Step 2: Write TranscriptPanel**

Create `frontend/app/components/TranscriptPanel.tsx`:

```tsx
"use client";

import { AudioPlayer } from "./AudioPlayer";

interface TranscriptLine {
  role: "customer" | "agent";
  text: string;
  audio: string;
}

interface TranscriptPanelProps {
  title: string;
  lines: TranscriptLine[];
}

export function TranscriptPanel({ title, lines }: TranscriptPanelProps) {
  return (
    <section className="py-20 px-6 max-w-3xl mx-auto">
      <h2 className="text-3xl font-bold mb-8">{title}</h2>
      <div className="space-y-4">
        {lines.map((line, i) => (
          <div key={i} className="flex items-start gap-3">
            <AudioPlayer src={`/audio/${line.audio}`} />
            <div>
              <span
                className={`text-sm font-semibold ${
                  line.role === "customer" ? "text-blue-400" : "text-green-400"
                }`}
              >
                {line.role === "customer" ? "Customer" : "Agent"}:
              </span>
              <p className="text-white/80 mt-0.5">{line.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/AudioPlayer.tsx frontend/app/components/TranscriptPanel.tsx
git commit -m "feat: AudioPlayer + TranscriptPanel components"
```

---

## Task 11: Frontend Components — MemoryCard + ComparisonPanel

**Files:**
- Create: `frontend/app/components/MemoryCard.tsx`
- Create: `frontend/app/components/ComparisonPanel.tsx`

- [ ] **Step 1: Write MemoryCard**

Create `frontend/app/components/MemoryCard.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";

interface MemoryCardProps {
  memory: Record<string, string>;
}

export function MemoryCard({ memory }: MemoryCardProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.3 }
    );
    const el = document.getElementById("memory-card");
    if (el) observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const jsonStr = JSON.stringify(memory, null, 2);

  return (
    <section id="memory-card" className="py-20 px-6 max-w-3xl mx-auto">
      <h2 className="text-3xl font-bold mb-4">What Memory Autopilot Extracted</h2>
      <p className="text-white/50 mb-8">
        Extracted automatically by ElevenLabs Data Collection after the call.
      </p>
      <div
        className={`bg-white/5 border border-white/10 rounded-lg p-6 font-mono text-sm transition-all duration-1000 ${
          visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
        }`}
      >
        <pre className="text-green-400 whitespace-pre-wrap">{jsonStr}</pre>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Write ComparisonPanel**

Create `frontend/app/components/ComparisonPanel.tsx`:

```tsx
"use client";

import { useState } from "react";
import { AudioPlayer } from "./AudioPlayer";

interface ComparisonLine {
  role: "customer" | "agent";
  text: string;
  audio: string;
}

interface ComparisonPanelProps {
  withoutMemory: ComparisonLine[];
  withMemory: ComparisonLine[];
}

export function ComparisonPanel({ withoutMemory, withMemory }: ComparisonPanelProps) {
  const [memoryOn, setMemoryOn] = useState(true);

  const lines = memoryOn ? withMemory : withoutMemory;

  return (
    <section className="py-20 px-6 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold mb-4">The Callback</h2>
      <p className="text-white/50 mb-8">2 days later, Sarah calls back...</p>

      <div className="flex justify-center mb-8">
        <div className="bg-white/10 rounded-full p-1 flex">
          <button
            onClick={() => setMemoryOn(false)}
            className={`px-4 py-2 rounded-full text-sm transition-colors ${
              !memoryOn ? "bg-red-500/80 text-white" : "text-white/50"
            }`}
          >
            Memory OFF
          </button>
          <button
            onClick={() => setMemoryOn(true)}
            className={`px-4 py-2 rounded-full text-sm transition-colors ${
              memoryOn ? "bg-green-500/80 text-white" : "text-white/50"
            }`}
          >
            Memory ON
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {lines.map((line, i) => (
          <div key={`${memoryOn}-${i}`} className="flex items-start gap-3">
            <AudioPlayer src={`/audio/${line.audio}`} />
            <div>
              <span
                className={`text-sm font-semibold ${
                  line.role === "customer" ? "text-blue-400" : "text-green-400"
                }`}
              >
                {line.role === "customer" ? "Customer" : "Agent"}:
              </span>
              <p className="text-white/80 mt-0.5">{line.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/MemoryCard.tsx frontend/app/components/ComparisonPanel.tsx
git commit -m "feat: MemoryCard + ComparisonPanel with toggle"
```

---

## Task 12: Frontend Components — HowItWorks + TryItYourself

**Files:**
- Create: `frontend/app/components/HowItWorks.tsx`
- Create: `frontend/app/components/TryItYourself.tsx`

- [ ] **Step 1: Write HowItWorks**

Create `frontend/app/components/HowItWorks.tsx` — three-step diagram with code snippets showing the webhook handler and conversation-init response. Use static JSX with Tailwind, code blocks styled with `bg-white/5` and `font-mono`.

- [ ] **Step 2: Write TryItYourself**

Create `frontend/app/components/TryItYourself.tsx` — textarea for transcript input, "Extract Memory" button, calls `POST ${API_URL}/api/demo/extract`, displays JSON result. Includes loading state and error handling. Labeled: "Demo extraction endpoint — the production system uses ElevenLabs native Data Collection."

Use `NEXT_PUBLIC_API_URL` env var for the backend URL.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/HowItWorks.tsx frontend/app/components/TryItYourself.tsx
git commit -m "feat: HowItWorks + TryItYourself components"
```

---

## Task 13: Frontend — Assemble Landing Page

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Update layout.tsx**

Set dark background, custom fonts, metadata:

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Memory Autopilot — Cross-Session Memory for ElevenLabs Voice Agents",
  description: "Automatic memory extraction and injection for ElevenLabs voice agents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-black text-white`}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Assemble page.tsx**

Import all components, load transcript data from JSON, assemble the scroll-through narrative:

1. Hero section with title, subtitle, CTAs
2. TranscriptPanel (Call 1)
3. "2 days later..." transition
4. MemoryCard
5. ComparisonPanel (Call 2 with toggle)
6. HowItWorks
7. TryItYourself
8. Footer with GitHub link

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds (audio files may be missing, that's ok)

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: assemble landing page — all panels wired up"
```

---

## Task 14: Pre-Compute Audio + Backend README

**Files:**
- Run: `scripts/generate_audio.py`
- Create: `backend/README.md`
- Create: `README.md` (root)

- [ ] **Step 1: Generate audio**

```bash
ELEVENLABS_API_KEY=your-key python scripts/generate_audio.py
```

Expected: ~15 mp3 files in `frontend/public/audio/`

- [ ] **Step 2: Write backend README**

Create `backend/README.md` with: architecture overview, API docs for all endpoints, setup instructions, how to run tests, environment variables reference.

- [ ] **Step 3: Write root README**

Create `README.md` with: project overview, system diagram, quick start, link to live demo and backend README. Lead with architecture, not the demo page.

- [ ] **Step 4: Commit**

```bash
git add frontend/public/audio/ backend/README.md README.md
git commit -m "feat: pre-computed audio, README documentation"
```

---

## Task 15: Deploy Backend to Railway

- [ ] **Step 1: Create Railway project**

```bash
railway login
railway init
```

- [ ] **Step 2: Add Postgres**

```bash
railway add --plugin postgresql
```

- [ ] **Step 3: Set environment variables**

```bash
railway variables set ELEVENLABS_WEBHOOK_SECRET=<secret>
railway variables set ELEVENLABS_AGENT_ID=<agent_id>
railway variables set ALLOWED_ORIGINS=https://memory-autopilot.vercel.app,http://localhost:3000
railway variables set ANTHROPIC_API_KEY=<key>
```

- [ ] **Step 4: Deploy**

```bash
cd backend && railway up
```

- [ ] **Step 5: Run schema**

Connect to Railway Postgres and run schema.sql.

- [ ] **Step 6: Seed demo data**

```bash
DATABASE_URL=<railway-url> python scripts/seed_data.py
```

- [ ] **Step 7: Run deploy smoke checklist**

- [ ] `GET /health` returns 200 with `"db": "connected"`
- [ ] `POST /webhooks/elevenlabs/post-call` with bad signature → 401
- [ ] `POST /webhooks/elevenlabs/post-call` with valid fixture → 200
- [ ] `POST /webhooks/elevenlabs/conversation-init` with known caller → populated vars
- [ ] `POST /webhooks/elevenlabs/conversation-init` with unknown caller → empty-string vars

- [ ] **Step 8: Commit any deploy fixes**

---

## Task 16: Deploy Frontend to Vercel + ElevenLabs Agent Setup

- [ ] **Step 1: Deploy to Vercel**

```bash
cd frontend && vercel --prod
```

Set env var: `NEXT_PUBLIC_API_URL` → Railway backend URL

- [ ] **Step 2: Verify frontend works**

Open the deployed URL. Check:
- Audio plays
- Panels render
- "Try it yourself" hits the real API (check browser network tab)
- No CORS errors

- [ ] **Step 3: Create ElevenLabs agent**

In ElevenLabs dashboard:
1. Create agent with customer support persona
2. Configure Data Collection fields (6 fields from spec Section 3)
3. Set dynamic variables in system prompt and first message (spec Section 3)
4. Configure post-call webhook URL → `https://<railway-url>/webhooks/elevenlabs/post-call`
5. Configure conversation initiation webhook → `https://<railway-url>/webhooks/elevenlabs/conversation-init`

- [ ] **Step 4: Save agent config reference**

Create `data/agent_config.json` with the agent ID and configuration for reference.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: deploy config, ElevenLabs agent reference"
```
