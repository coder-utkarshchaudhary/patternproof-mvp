# Pattern Proof – Dark Pattern Audit Service

Detect and report dark patterns on any website. Enter a URL, get a detailed audit.

## Quick Start

```bash
docker compose up --build
```

Services:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **ML Inference**: http://localhost:8001
- **Ollama**: http://localhost:11434

## Architecture

```
User → Next.js (3000) → FastAPI (8000) → Celery Worker
                                             ↓
                                   LangGraph Supervisor
                                   ├── Static DP Agent → YOLO + VLM (8001)
                                   └── Dynamic DP Agents → Playwright
                                             ↓
                                        Report Builder → Web + PDF
```

## Project Structure

```
├── backend/          # FastAPI + LangGraph agents + Celery workers
├── frontend/         # Next.js dashboard
├── ml/               # YOLO inference + VLM explainability
├── docs/             # Documentation
└── docker-compose.yml
```

## Development

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### ML Inference

```bash
cd ml
pip install -e .
uvicorn inference.server:app --port 8001 --reload
```
