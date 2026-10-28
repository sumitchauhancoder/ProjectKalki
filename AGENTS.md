# AGENTS.md — Developer and AI Agent Guidelines for Project KALKI

## 1. Architecture Summary (from PLAN.md Section 3)

```
┌─────────────────────────────────────────────────────────┐
│ Electron shell (main.js, preload.js)                    │
│   - Launches backend, handles installer, auto-update    │
│   - Stores user's Gemini key with safeStorage           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ React HUD (src/)                                    │ │
│ │   - Login (Firebase), setup screen, chat, voice     │ │
│ │   - Shows states: idle, listening, recording,       │ │
│ │     thinking, speaking                              │ │
│ └─────────────────────────────────────────────────────┘ │
└───────────────┬─────────────────────────────────────────┘
                │ HTTP / SSE on 127.0.0.1:<port>
┌───────────────▼─────────────────────────────────────────┐
│ FastAPI backend (backend/)                              │
│   /health /setup/status /setup/key                      │
│   /execute-command /chat-stream /process-frame          │
│   /voice/start /voice/stop /voice/status                │
│                                                         │
│  LLM chain:  local regex router                         │
│              → Gemini (10 s timeout)                    │
│              → Groq (fallback)                          │
│              → safe spoken error message                │
│                                                         │
│  Voice:  openWakeWord → faster-whisper → LLM → edge-tts │
│  Data:   SQLite (installed app) or Neon Postgres (dev)  │
│  Auth:   Firebase ID token verified on backend          │
└─────────────────────────────────────────────────────────┘
```

### Where Things Live

| Item | Location |
|---|---|
| Source code | Repository root (`src/`, `backend/`, `main.js`) |
| User settings and encrypted key | `%APPDATA%\KALKI\settings.json` |
| Local database (standalone) | `%APPDATA%\KALKI\kalki.db` (or `backend/kalki.db` in dev fallback) |
| Downloaded models (Whisper, wake word) | `%APPDATA%\KALKI\models\` |
| Logs | `%APPDATA%\KALKI\logs\kalki.log` |
| Developer secrets | `backend\.env` (git-ignored) |
| Firebase service account JSON | Kept strictly outside the repo; path set in `.env` |

---

## 2. Key Rules & Constraints (Mandatory for all agents)

1. **Async routes must not block:** Never run blocking network, database, or SDK calls synchronously on the FastAPI event loop. Always use `asyncio.to_thread` for blocking operations.
2. **Never hardcode or log secrets:** Never log any API key, password, connection string, or token, even partially. Never print `DATABASE_URL` as it contains credentials.
3. **Every external service is optional with a graceful fallback:** The app must start and run if PostgreSQL is offline, if the internet is disconnected, or if API keys are missing.
4. **All services must be free-tier or local:** Project KALKI is budget-free; no paid libraries or paid service tiers are allowed.
5. **The LLM chain is strictly ordered:**
   `Local Regex Router (0ms)` &rarr; `Gemini (10s timeout)` &rarr; `Groq (fallback)` &rarr; `Safe spoken error message`.
6. **Authentication and Data roles are separated:** Firebase handles user authentication. PostgreSQL (or local SQLite) stores application data. Firestore is not used.
7. **The installer must never contain database credentials, the Firebase service account, or any API key:** Each user brings their own free Gemini key, stored securely using Electron `safeStorage`.

---

## 3. How to Run

### Run Backend Server (FastAPI)
From repository root using the virtual environment:
```powershell
.\venv\Scripts\python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Or directly via Python:
```powershell
.\venv\Scripts\python.exe backend/app.py
```

### Run Frontend Desktop App (Electron + React)
```powershell
npm run dev
```
Or run the React Vite dev server alone:
```powershell
npm run dev:react
```

### Run Verification & Diagnostics
From repository root:
```powershell
.\venv\Scripts\python.exe backend/test_diagnostics.py
```
Or with system Python if the environment is activated:
```bash
python backend/test_diagnostics.py
```
Each check outputs `[PASS]` or `[FAIL]`. All checks must pass before moving to the next phase.
