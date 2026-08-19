# SwarmShield

Autonomous multi-agent AI security framework for red-teaming agentic AI systems
(APIs, tools, workflows) against the OWASP Top 10 for LLM Applications.

## Directory Structure

```
swarmshield/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, CORS, router mounting
│   │   ├── core/
│   │   │   ├── config.py            # Settings (env vars, API keys, DB url)
│   │   │   └── security.py          # API key/auth helpers
│   │   ├── db/
│   │   │   ├── base.py              # SQLAlchemy Base + session factory
│   │   │   └── init_db.py           # create_all / seed helper
│   │   ├── models/
│   │   │   ├── target.py            # TargetProfile
│   │   │   ├── scan.py              # ScanRun
│   │   │   ├── attack.py            # AttackLog
│   │   │   ├── vulnerability.py     # Vulnerability
│   │   │   └── patch.py             # RemediationPatch
│   │   ├── schemas/                 # Pydantic request/response models
│   │   │   ├── target.py
│   │   │   ├── scan.py
│   │   │   ├── attack.py
│   │   │   ├── vulnerability.py
│   │   │   └── patch.py
│   │   ├── agents/
│   │   │   ├── base.py              # BaseAgent w/ Gemini call wrapper
│   │   │   ├── planner.py           # Planner Agent
│   │   │   ├── sentinel.py          # Sentinel Agent
│   │   │   ├── orchestrator.py      # Swarm loop / adaptive feedback controller
│   │   │   └── specialists/
│   │   │       ├── prompt_injection.py
│   │   │       ├── jailbreak.py
│   │   │       ├── tool_abuse.py
│   │   │       ├── data_exfiltration.py
│   │   │       └── privilege_escalation.py
│   │   ├── services/
│   │   │   ├── gemini_client.py     # Google Gemini API wrapper
│   │   │   ├── target_client.py     # Generic HTTP client to call the target system
│   │   │   └── scan_manager.py      # Runs a scan, streams events, persists results
│   │   └── api/
│   │       └── routes/
│   │           ├── targets.py       # CRUD for target profiles
│   │           ├── scans.py         # start/stop scan, SSE log stream
│   │           ├── vulnerabilities.py
│   │           └── patches.py
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.jsx        # Vulnerability scorecard + summary
    │   │   ├── ScanRunner.jsx       # Live scan trigger + streaming log console
    │   │   └── AttackGraph.jsx      # React Flow attack chain visualization
    │   ├── components/
    │   │   ├── ScorecardCard.jsx
    │   │   ├── VulnerabilityTable.jsx
    │   │   ├── PatchSuggestionPanel.jsx
    │   │   ├── AgentLogConsole.jsx
    │   │   └── flow/
    │   │       ├── AttackFlowCanvas.jsx
    │   │       └── nodeTypes.jsx
    │   ├── hooks/
    │   │   └── useScanStream.js     # SSE hook for live agent logs
    │   ├── lib/
    │   │   └── api.js               # fetch wrappers to FastAPI backend
    │   └── store/
    │       └── scanStore.js         # Zustand store for scan/vuln state
    ├── package.json
    └── tailwind.config.js
```

## Why this shape (hackathon rationale)

- **`agents/`** is isolated from **`services/`**: agents contain *prompting/reasoning
  logic only*; services contain *I/O* (Gemini calls, HTTP calls to the target,
  DB writes). This split lets you swap Gemini for another model in 5 minutes
  and keeps agent prompt logic easy to demo/explain to judges.
- **`orchestrator.py`** is the single place implementing the adaptive feedback
  loop (Attacker → Sentinel → mutate → retry). Judges will want to see this
  file — keep it readable.
- **SSE over WebSockets** for the live log stream: simpler to implement in
  FastAPI + fetch on the frontend, good enough for a hackathon demo, no extra
  infra.
- **n8n** is treated as an *optional* external orchestrator that can call
  `/api/scans/start` via webhook — not required for the core loop to work,
  so the demo isn't dependent on an n8n instance being up.

## Build status

1. ✅ Step 1: Project structure
2. ✅ Step 2: SQLAlchemy models (`backend/app/models/`) — verified against a real Postgres instance
3. ✅ Step 3: FastAPI endpoints (`backend/app/api/routes/`, `main.py`) — verified end-to-end with `TestClient`
4. ✅ Step 4: Agent prompts (`backend/app/agents/`) — orchestrator's adaptive feedback loop verified with a mocked Gemini + target, including mutation lineage
5. ✅ Step 5: React frontend (`frontend/src/`) — production build verified clean

## Running it locally

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in GEMINI_API_KEY and DATABASE_URL

# make sure Postgres is running and the DB in DATABASE_URL exists, e.g.:
#   createuser swarmshield -P
#   createdb swarmshield -O swarmshield

uvicorn app.main:app --reload --port 8000
```
Tables are created automatically on startup (`init_db()` in the app's lifespan).
Visit http://localhost:8000/docs for interactive API docs.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173. The Vite dev server proxies `/api/*` to `http://localhost:8000`.

### Demo flow
1. In the left panel, click **+ New target**, give it a name, an endpoint URL
   (point it at any HTTP endpoint that accepts `{"input": "..."}` and returns
   `{"output": "..."}` — including a quick mock server for the demo), and a
   comma-separated list of tool names to declare.
2. Click **Launch swarm scan**. The Planner Agent maps the attack surface,
   then the attacker swarm + Sentinel run the adaptive feedback loop live —
   watch it in the center attack-lineage graph and the right-hand console.
3. Confirmed findings land in the left-hand vulnerability list; expand one
   and click **Generate remediation patch** for an AI-written fix suggestion.

### n8n (optional)
To trigger scans from an n8n workflow instead of the UI, add an HTTP Request
node that `POST`s to `http://localhost:8000/api/scans` with
`{"target_id": "<uuid>"}`. `N8N_WEBHOOK_URL` in `.env` is reserved if you want
the backend to *notify* n8n on scan completion — wire that call into the end
of `orchestrator.run_scan` if needed for your workflow.

## What's stubbed / hackathon-scope simplifications

- **Auth**: none. Add an API-key dependency in `core/security.py` before
  deploying this anywhere real.
- **Event bus**: in-memory, single-process (`services/event_bus.py`). Fine
  for a demo; swap for Redis pub/sub if you run multiple backend workers.
- **DB migrations**: `create_all()` on startup instead of Alembic, for speed.
- **Target response parsing**: `TargetClient._extract_output` guesses common
  JSON response shapes (`output`/`response`/`text`/...). Adjust it if your
  actual target's API differs.
