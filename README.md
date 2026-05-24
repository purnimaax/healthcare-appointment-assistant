# Mykare AI — Healthcare Front-Desk Assistant

Multi-agent AI assistant for a clinic — handles appointment booking, healthcare Q&A, document analysis, and works in multiple languages.

> **Stack:** FastAPI · LangGraph · Groq (llama-3.3-70b) · ChromaDB · SQLite · Vite + React + TypeScript + Tailwind

---

## What it can do

- **Book/cancel/reschedule appointments** — natural language, no forms
- **Answer healthcare questions** — pulls from a knowledge base using RAG
- **Analyse uploaded documents** — PDFs and images (lab reports, prescriptions)
- **Multilingual** — tested with English, Hindi, Malayalam
- **Live agent activity panel** — every tool call shows up in real time on the right side
- **REST API** — all appointment ops also available at `/docs` if you want to skip the chat

---

## Architecture

```
┌─────────────────┐     ┌────────────────────────────────────────────────────┐
│   React + TS    │ ── ▶│  FastAPI                                           │
│   Vite SPA      │ ◀──│   /api/chat            (single-shot)                │
│   (Tailwind)    │  SSE│   /api/chat/stream    (live tool-call updates)     │
│                 │     │   /api/appointments/* (direct REST)                │
│  ChatInput      │     │   /api/documents/upload                            │
│  MessageBubble  │     │   /docs               (Swagger)                    │
│  AgentTimeline  │     └──────────────────┬─────────────────────────────────┘
│  Appointments   │                        │
└─────────────────┘                        ▼
                              ┌────────────────────────────────┐
                              │  LangGraph workflow            │
                              │                                │
                              │           ┌──── appointment ──┐│
                              │           │                   ││
                              │  router ──┼──── rag ──────────┤│── ▶ END
                              │           │                   ││
                              │           ├──── document ─────┤│
                              │           ├──── summary ──────┤│
                              │           └──── smalltalk ────┘│
                              │                                │
                              │  conversation memory:          │
                              │    SqliteSaver checkpointer    │
                              └────┬───────────┬───────────┬───┘
                                   ▼           ▼           ▼
                            ┌─────────┐  ┌──────────┐  ┌────────────────┐
                            │ SQLite  │  │ ChromaDB │  │ Groq API       │
                            │ (appts, │  │ (kb +    │  │ (chat + vision │
                            │  users) │  │  uploads)│  │  + embeddings) │
                            └─────────┘  └──────────┘  └────────────────┘
```

### Agents (LangGraph nodes)

| Node | What it does |
|---|---|
| **router** | Classifies intent + detects language. Routes to: `appointment`, `rag`, `document`, `summary`, or `smalltalk`. |
| **appointment** | ReAct agent with 6 tools: `fetch_slots`, `book_appointment`, `cancel_appointment`, `modify_appointment`, `retrieve_appointments`, `list_departments`. |
| **rag** | Searches the healthcare KB + user uploads, generates a grounded answer. |
| **document** | Same as rag but only searches the user's uploaded files. |
| **summary** | Summarises the conversation when asked. |
| **smalltalk** | Handles greetings and off-topic messages without triggering retrieval. |

Chat history is stored by LangGraph's `SqliteSaver` checkpointer, keyed on `session_id`. Memory persists across server restarts.

---

## What's implemented

### Must-have

- [x] AI assistant with multi-turn memory
- [x] Appointment workflow — book, cancel, reschedule, list, identify patients by phone or email
- [x] Multi-agent LangGraph workflow — 5 specialist nodes + router
- [x] RAG pipeline — ChromaDB + sentence-transformers + RecursiveCharacterTextSplitter, 8 KB docs auto-ingested on startup
- [x] Tool/function calling — 7 LangChain tools
- [x] Groq LLM integration (`llama-3.3-70b-versatile`) for chat, vision model for image analysis
- [x] Live tool-call UI via SSE — every tool shows `running` → `done`/`error` with args and results
- [x] Swagger at `/docs`, ReDoc at `/redoc`
- [x] Clean layering: api / agents / services / tools / db

### Bonus

- [x] Multimodal — PDFs via pypdf, images via Groq vision, both indexed in ChromaDB for follow-up questions
- [x] Multilingual — router detects language, agents reply in kind
- [x] 13 passing unit tests, env-based config, CORS, structured logging

---

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Free Groq API key — get one at https://console.groq.com

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Add your Groq key to GROQ_API_KEY in .env

uvicorn app.main:app --reload --port 8000
```

Swagger at http://localhost:8000/docs. The KB gets auto-ingested on first startup.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173. Vite proxies `/api/*` to port 8000.

### Tests

```bash
cd backend
pytest -q
```

---

## Design notes

**Why Groq + ChromaDB + SQLite?** Groq has a generous free tier and is fast. ChromaDB runs locally so there's nothing to provision. SQLite is zero-setup — the SQLAlchemy layer makes switching to Postgres a one-liner if needed.

**Why a service layer separate from the tools?** Booking logic is reachable two ways — via the AI agent and via the REST API. Keeping validation in `services/appointments.py` means it runs regardless of which path is used.

**Why SSE instead of WebSockets?** The tool calls needed to show up live in the UI. SSE is simpler for one-way server-to-browser streaming — WebSockets would have been overkill.

**Why structured output for the router?** `.with_structured_output(RouterDecision)` gives a typed Pydantic object back instead of free text, so there's no JSON parsing or schema mismatch issues. The router runs on every message so reliability matters.

**Why local embeddings?** `sentence-transformers` runs fully offline — no API key, no rate limits, no cost. Works well enough for a healthcare KB of this size.

### Things I'd improve with more time

- Token-by-token streaming from the final LangGraph node (currently the full reply waits until the graph finishes)
- Remembering patients across sessions so they don't have to give their phone number every time
- A proper eval suite — fixed prompts with assertions on intent classification and tool calls
- Auto-expiry for uploaded documents (PII concern in production)

---

## Project layout

```
mykare-ai-assistant/
├── backend/
│   ├── app/
│   │   ├── agents/      # LangGraph nodes
│   │   ├── api/         # FastAPI routers + schemas
│   │   ├── core/        # config, logging
│   │   ├── db/          # SQLAlchemy models + session
│   │   ├── services/    # business logic
│   │   ├── tools/       # LangChain @tool wrappers
│   │   └── main.py
│   ├── data/kb/         # Markdown KB files (auto-ingested)
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   └── types.ts
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Deployment

### Docker Compose

```bash
GROQ_API_KEY=your_key docker compose up --build
```

Frontend: http://localhost:5173 · Backend: http://localhost:8000/docs

### Render + Vercel

**Backend (Render):** connect repo, root `backend/`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `GROQ_API_KEY` and `ALLOWED_ORIGINS`.

**Frontend (Vercel):** root `frontend/`, framework Vite, build `npm run build`, output `dist`. Set `VITE_API_BASE_URL` to your Render URL.
