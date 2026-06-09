# ShikshaSetu

**AI Administrative Assistant for Government School Teachers** — v3.0 (MVP)

Reduces administrative burden by automating attendance management, PM POSHAN administration, and audit preparation through Agentic AI (Gemini Vision + LangGraph).

See `Siksha.md` for the full product specification.

---

## Architecture

```
React (Vite + Tailwind + ShadCN UI)
        │
        ▼
FastAPI ── JWT auth
        │
        ▼
LangGraph Supervisor ─► Attendance Agent ─┐
                       ─► PM POSHAN Agent ─┼─► SQLite (SQLAlchemy)
                       ─► Audit Agent     ─┘
        │
        ▼
Gemini 2.5 Vision (register OCR + structured extraction)
```

## Quick start

### 1. Get a Gemini API key

Visit https://aistudio.google.com/app/apikey and create one.

### 2. Run everything

```bash
# Option A — single command (uses two run.sh scripts in parallel)
./run-all.sh

# Option B — manual
# Terminal 1 — backend
cd backend
cp .env.example .env       # then paste your GOOGLE_API_KEY into .env
./run.sh

# Terminal 2 — frontend
cd frontend
./run.sh
```

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173
- Demo login: **teacher@demo.in / password**

---

## Project layout

```
.
├── backend/
│   ├── app/
│   │   ├── agents/         # LangGraph supervisor + 3 specialists
│   │   ├── api/            # FastAPI routers
│   │   ├── core/           # config, db, security (JWT)
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── schemas/        # Pydantic DTOs
│   │   ├── services/       # gemini_vision, analytics, validation
│   │   └── main.py
│   ├── data/               # SQLite db lives here
│   ├── uploads/            # register images + audit docs
│   ├── seed.py             # seeds demo teacher + 15 students + 20 days data
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/          # Login, Dashboard, Chat, Upload, Attendance, Poshan, Audit
│   │   ├── components/ui/  # ShadCN-style primitives (Button, Card, Tabs, …)
│   │   ├── context/        # AuthContext
│   │   └── lib/api.ts      # typed API client
│   └── package.json
└── Siksha.md               # original product spec
```

---

## What works in the MVP

- **Teacher dashboard** — attendance %, PM POSHAN utilization, audit score, stock alerts, recent uploads
- **Register upload** — drop in an image of attendance/PM POSHAN/stock/audit; Gemini Vision extracts structured JSON; validation layer flags issues; data is persisted automatically
- **AI chat** — natural-language questions routed by Supervisor → Attendance / PM POSHAN / Audit / General agent
- **Attendance** — daily marking UI, monthly summaries, <75% anomaly detection
- **PM POSHAN** — meal recording, stock status, low-stock alerts
- **Audit readiness** — composite 100-point score, missing-document detection, document upload, recommendations

## Tech stack

- **Backend:** FastAPI 0.115, SQLAlchemy 2, Pydantic 2, python-jose (JWT), passlib (bcrypt)
- **AI:** LangGraph 0.2, LangChain 0.3, `google-generativeai` (Gemini 2.5 Flash + Vision)
- **DB:** SQLite (file-based — `backend/data/shikshasetu.db`)
- **Frontend:** Vite + React 18 + TypeScript, Tailwind CSS 3, ShadCN-style components, React Router 6

---

## Notes

- Register upload + chat require `GOOGLE_API_KEY` in `backend/.env`. Without it the API still works; Gemini calls return a mock response.
- The DB and uploads are local — delete `backend/data/` and `backend/uploads/` to reset.
- This is an MVP — see `Siksha.md §16` for what's intentionally out-of-scope, and `§17` for the planned phases.
