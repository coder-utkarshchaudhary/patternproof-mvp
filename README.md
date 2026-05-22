# Pattern Proof – Dark Pattern Audit Service

Detect and report **static dark patterns** on any website and certify compliance
with India's **DPDP Act** and the **CCPA 2023 dark-pattern guidelines**. Enter a
URL, get a detailed PDF audit.

## Architecture

```
User → Next.js (3000) → FastAPI (8000) ──enqueue──► Redis ──► Celery Worker
                            │                                     │
                            │                          LangGraph Manager (Claude)
   Supabase (Postgres+JSONB │                          ├── Planner   (task tickets)
   + Storage)               │                          ├── Crawler   → Apify
                            │                          ├── StaticDPDetector
   Slack / WhatsApp ◄───────┘                          │     ├ Visual  → YOLO (8001) + Claude vision
   (notify)                                            │     └ Semantic→ cheap LLM (HTML parse)
                                                       └── ReportGenerator → Exa + Claude → PDF
```

**Stack:** FastAPI · Celery/Redis · LangGraph · Claude (agents+vision) ·
OpenAI `gpt-4o-mini` (HTML parsing) · Supabase (DB + Storage) · Apify (crawl) ·
Exa (references) · PyTorch/YOLO (visual detection) · Next.js · WeasyPrint (PDF).

## Setup

1. Copy env and fill in keys (Supabase, Anthropic, OpenAI, Apify, Exa, Slack, Twilio):

   ```bash
   cp .env.example .env
   ```

2. Apply the Supabase schema (SQL editor or CLI) from `supabase/migrations/`:
   `0001_init.sql` then `0002_storage_buckets.sql`.

3. Bring up the stack:

   ```bash
   docker compose up --build
   ```

Services:

- **Frontend**: http://localhost:3000
- **Backend API / docs**: http://localhost:8000 · http://localhost:8000/docs
- **ML Inference**: http://localhost:8001

## ML model

The YOLO detector runs in **stub mode** (returns no boxes) until weights exist at
`ml/models/dark_patterns.pt`. Semantic LLM detection works without it. To train:

```bash
cd ml
pip install -e .
# 1. Prepare public datasets (AidUI/ContextDP, arXiv) into YOLO format
python training/data_prep.py --src datasets/raw/aidui --out datasets/dark_patterns
# 2. Fine-tune
python training/train_yolo.py --data datasets/dark_patterns/dark_patterns.yaml --epochs 100
```

## Local development

```bash
# Backend
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
# Worker
celery -A app.worker worker --loglevel=info
# Frontend
cd frontend && npm install && npm run dev
# ML inference
cd ml && pip install -e . && uvicorn inference.server:app --port 8001 --reload
```

## Project Structure

```
├── backend/    # FastAPI + LangGraph agents + Celery worker + Supabase
├── frontend/   # Next.js dashboard
├── ml/         # YOLO training + inference
├── supabase/   # SQL migrations (schema + storage buckets)
└── docker-compose.yml
```

## Scope

MVP detects **static** dark patterns (visual + semantic). Dynamic multi-page flow
detection (checkout/cancellation obstruction) is scaffolded in the graph but
deferred.
