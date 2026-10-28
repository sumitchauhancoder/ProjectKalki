# PROJECT KALKI: Master Plan

> **How to use this file**
> - **Antigravity:** Place this file at the repo root as `PLAN.md`. Read it before every task. Work on one phase at a time. Do not start a phase until the previous one is committed and its checks pass.
> - **New chat with an AI assistant:** Paste this whole file at the start of the chat, then say which phase you are on. Update the Status Tracker (Section 9) as phases finish.

---

## 1. Project summary

**KALKI** is a free, college-project desktop voice assistant for Windows, inspired by J.A.R.V.I.S. It has:

- An Electron + React desktop HUD (user interface).
- A FastAPI Python backend running on `127.0.0.1`.
- Hands-free voice: wake word, speech-to-text, and text-to-speech.
- An LLM brain with a local fast-path router plus cloud fallback.
- Login and user data.
- Later: tool calling (open apps, search files, set timers), safety confirmations, memory, and reminders.

**Goal:** A working Jarvis-style voice assistant that people can install on Windows with no paid services.

**Repo:** Public GitHub repository (already exists; the college project is not sensitive, but secrets must still never be committed).

---

## 2. Decisions (settled, do not change without asking)

| Topic | Decision | Reason |
|---|---|---|
| Platform | **Windows only** | Halves the testing work. Other platforms are out of scope. |
| Cost | **Free tiers and local tools only** | User has no budget. |
| Primary LLM | **Google Gemini API** (free key from Google AI Studio) | Free tier. |
| Fallback LLM | **Groq API** (free key from Groq console) | Used only when Gemini fails. |
| Who provides the LLM key | **Each user brings their own free Gemini key** | A shared key in the installer can be extracted and abused. Google may disable it. |
| Authentication | **Firebase Authentication** (login and register) | Free, handles passwords and Google sign-in. |
| App database | **Neon PostgreSQL** in development; **local SQLite** in the installed app | Neon is free but its credentials must never ship inside the installer. |
| Firestore | **Not used** | Avoids keeping data in two databases. |
| Wake word | **openWakeWord** (local, Apache 2.0) | Free, offline. |
| Speech-to-text | **faster-whisper** (local, MIT) | Free, offline, does not depend on a Google endpoint. |
| Text-to-speech | **edge-tts** (already in project) | Free, no key. Check Microsoft's terms before public distribution. Use **pyttsx3** as an offline fallback. |
| Vision | **OpenCV** (already in project) | Local and free. |
| Packaging | **PyInstaller** (backend) + **electron-builder** NSIS (installer) | Free. |
| Auto-update | **electron-updater** with **GitHub Releases** | Free. |
| CI/CD | **GitHub Actions** on version tags | Free for public repos. |
| Code signing | **Not required for now** | Unsigned installers show a SmartScreen warning. Testers click "More info", then "Run anyway". SignPath Foundation is an optional free route later. |

### Things the assistant must NOT do

- Do not hardcode, print, log, or commit any API key, password, Neon connection string, or Firebase service account file.
- Do not put Neon credentials or the Firebase service account into the installer.
- Do not use paid services or paid libraries.
- Do not add Firestore.
- Do not redesign the UI unless a phase says so.
- Do not claim "0 ms" for app launches. Say "near-instant" or measure it.

### Model names

Model names change. **Verify every model name against the official docs before use:**
- Gemini: https://ai.google.dev/gemini-api/docs/models
- Groq: https://console.groq.com/docs/models

Keep them in `.env` (`GEMINI_MODEL`, `GROQ_MODEL`), never hardcoded. The name `gemini-3.8-flash` in the original project summary is unverified. Confirm before using.

---

## 3. Architecture

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

### Where things live

| Item | Location |
|---|---|
| Source code | Repo |
| User settings and encrypted key | `%APPDATA%\KALKI\settings.json` |
| Local database | `%APPDATA%\KALKI\kalki.db` |
| Downloaded models (Whisper, wake word) | `%APPDATA%\KALKI\models\` |
| Logs | `%APPDATA%\KALKI\logs\kalki.log` |
| Developer secrets | `backend\.env` (git-ignored) |
| Firebase service account JSON | Outside the repo; only its path is in `.env` |

### Key rules (put in AGENTS.md)

1. Async routes must never block. Use `asyncio.to_thread` for blocking work.
2. Never hardcode or log secrets. Never print partial keys.
3. Every external service is optional and has a graceful fallback.
4. All services must be free-tier or local.
5. LLM chain order is fixed: local router → Gemini → Groq → safe error message.
6. Firebase handles authentication. Postgres stores app data.
7. The installer must never contain database credentials, the Firebase service account, or any API key.

---

## 4. Current project status (from the original summary)

**Working already:**
- FastAPI backend with `/execute-command`, `/listen-voice`, `/process-frame`, `/macros`.
- Local regex router for app launches and typing.
- Gemini calls with a 10 s timeout, run in a thread.
- edge-tts voice output, with voice chosen by Unicode script (Kannada, Hindi, English).
- OpenCV screen-frame analysis.
- SQLAlchemy models (User, VoiceMacro, AuditLog).
- Diagnostics file `backend/test_diagnostics.py` with 5 checks.

**Known problems to fix in the phases below:**
- A hard timeout causes slow replies. Streaming fixes this.
- `.env` contains a leftover Groq key. Groq is now a deliberate fallback.
- Google Speech Recognition depends on an unofficial endpoint. Replaced by faster-whisper.
- Paths point into the repo. Breaks when installed.
- Model name unverified.
- Database guard uses `connect_timeout=2`, too short for Neon cold starts.

---

## 5. Phase order

| # | Phase | Purpose |
|---|---|---|
| 0 | Cleanup and safety | Gitignore, env template, Groq fallback, SQLite default, Neon-ready DB config |
| 1 | Streaming replies | Speech starts on the first sentence |
| 2 | Hands-free voice loop | Wake word, faster-whisper, speech end detection |
| 3 | Login with Firebase | Register/login, link Firebase user to Postgres user |
| 4 | Runtime paths and settings | Data in AppData, setup screen backend, logs |
| 5 | Bundle backend | PyInstaller single exe |
| 6 | Electron installer | First-run setup, safeStorage, NSIS, auto-update |
| 7 | Release pipeline | GitHub Actions on version tags, clean-machine test |
| 8 | Tool calling | Gemini function calling replaces regex routing |
| 9 | Safety confirmations | Spoken yes/no for risky actions, allowlist |
| 10 | Barge-in | User can interrupt the assistant |
| 11 | Memory | Conversation history and preferences |
| 12 | Proactive features | Reminders, timers, morning briefing |

**Recommended order for a working demo first:** 0 → 1 → 2 → 3 → 8 → 9 → 10 → 11 → 12, then 4 → 5 → 6 → 7 for packaging. Packaging last is faster for a college demo. Decide before starting Phase 4.

---

## 6. Phase specifications

Each phase has: **Goal**, **Tasks**, **Constraints**, **Acceptance check** (run by the user), and **Commit message**. Do not add features outside the phase.

### Phase 0: Cleanup and safety

**Goal:** Project is safe to publish, runs with no database server, and has the LLM fallback ready.

**Tasks:**
1. Create `.gitignore` at repo root: `backend/.env`, `backend/.venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `*.db`, `dist/`, `*.mp3`, `*.log`, and any `*service-account*.json`.
2. Create `backend/.env.example` with empty values:
   ```
   GEMINI_API_KEY=
   GEMINI_MODEL=
   GROQ_API_KEY=
   GROQ_MODEL=
   DATABASE_URL=sqlite:///backend/kalki.db
   DB_CONNECT_TIMEOUT=10
   FIREBASE_PROJECT_ID=
   FIREBASE_SERVICE_ACCOUNT_PATH=
   ```
   Add comments: model names change, verify in docs; Groq is an optional fallback; service account file must never be committed.
3. Do not print, move, or modify the real `backend/.env`.
4. **LLM fallback** in `backend/llm_engine.py`:
   - Gemini model from `GEMINI_MODEL`. Verify the default from current Google docs.
   - Keep the 10 s timeout on Gemini.
   - On Gemini failure (timeout, 429, 5xx, missing key), retry on Groq if `GROQ_API_KEY` is set. Verify the Groq SDK/endpoint and model in Groq docs.
   - If both fail, return a short, speakable error. Never crash the request.
   - Log which provider answered. Never log keys.
   - Local regex router stays first and unchanged.
   - Run blocking SDK calls with `asyncio.to_thread`.
5. **Database** (`DATABASE_URL`):
   - Unset → SQLite at `backend/kalki.db`.
   - `postgresql://` → PostgreSQL (Neon). Add `sslmode=require` if missing.
   - `DB_CONNECT_TIMEOUT` (default 10) used for PostgreSQL `connect_timeout`. Not hardcoded to 2.
   - If DB is unreachable, app still starts. DB-dependent routes return a clear error.
   - Never print the connection string.
6. Create `AGENTS.md` (repo root) with architecture summary, run commands, test command, and the key rules from Section 3.
7. `backend/test_diagnostics.py` runnable with `python backend/test_diagnostics.py`, printing PASS/FAIL per check. Checks:
   - `.env` loads from the backend folder.
   - App starts with no PostgreSQL running.
   - Gemini failure triggers Groq (mocked, no real network call).
   - Local router answers an app-launch command with no cloud call.

**Constraints:** No paid dependencies. Keep changes minimal. Existing endpoint behavior unchanged except as listed.

**Acceptance check (user):**
- Diagnostics pass.
- Backend starts with no PostgreSQL running.
- `git status` does not list `backend/.env`.
- Start with `DATABASE_URL` set to Neon: connects after a pause.
- Start with `DATABASE_URL` unset: uses SQLite.

**Commit:** `Phase 0 done`

**Before Phase 0:** Run `git log --all --oneline -- backend/.env` and `git log -p --all -S "neon.tech" --oneline`. If either shows results, rotate the Gemini and Groq keys and reset the Neon password before continuing.

---

### Phase 1: Streaming replies

**Goal:** Speech starts on the first complete sentence while the LLM is still generating.

**Tasks:**
1. In `llm_engine.py`, add a streaming function using the current Gemini streaming method. Keep the timeout and the local router.
2. Add a sentence splitter that buffers streamed text. Handle English `.?!`, Hindi danda `।`, and Kannada punctuation. Handle sentences split across chunks.
3. In `tts_engine.py`, add an asyncio queue with a single worker so sentences play in order and never overlap.
4. Add `POST /chat-stream` (Server-Sent Events): `token` events and a final `done` event. Keep `/execute-command` working.
5. In React, add a consumer that appends tokens to the chat panel as they arrive. No UI redesign.
6. If streaming fails, fall back to the non-streaming path and log the error.

**Tests:** Sentence splitter (English, Hindi, mixed, split across chunks). Queue ordering.

**Acceptance check:** Ask a long question. Speech begins before the text finishes.

**Commit:** `Phase 1 done`

---

### Phase 2: Hands-free voice loop

**Goal:** Say the wake word, ask a question, hear the answer, return to waiting. All local except the LLM.

**Tasks:**
1. Add `backend/voice_loop.py`, running in its own thread:
   - Continuous microphone capture with `sounddevice` at 16 kHz mono.
   - Wake word via `openwakeword`. Default pretrained model, configurable with `WAKE_WORD_MODEL` in `.env`.
   - After wake word, record until about 1.2 s of silence (energy-based VAD with numpy).
   - Transcribe with `faster-whisper`. Model from `WHISPER_MODEL` (default `base`). Language auto-detect with hint list en, hi, kn.
   - Send transcript through the same pipeline as `/chat-stream`. Speak the reply.
2. Endpoints: `POST /voice/start`, `POST /voice/stop`, `GET /voice/status`.
3. Make faster-whisper the default. Keep Google SpeechRecognition only as an optional fallback, or remove it.
4. HUD shows states: idle, listening for wake word, recording, thinking, speaking.
5. Document model download sizes and the privacy note in AGENTS.md: audio is processed locally; only the transcript goes to the LLM.

**Constraints:** Models download once, then run offline. No microphone found → log a clear message, app keeps running. Never block the event loop.

**Tests:** Diagnostic that loads the wake word and Whisper models and transcribes a bundled short WAV file, without a microphone.

**Acceptance check:** Say the wake word, ask a question, get a spoken answer.

**Commit:** `Phase 2 done`

---

### Phase 3: Login with Firebase

**Goal:** Users register and log in. Each Firebase user maps to one row in the app's database.

**Tasks:**
1. Create a Firebase project (free Spark plan). Enable **Email/Password** sign-in (and Google sign-in if wanted). Create a service account key for the backend. Store it outside the repo.
2. Frontend: Firebase JS SDK in React. Register, login, logout screens. Get the ID token after login.
3. Backend: `firebase-admin` verifies the ID token on protected routes. Reads `FIREBASE_SERVICE_ACCOUNT_PATH` and `FIREBASE_PROJECT_ID` from `.env`.
4. Database: `users` table gets a `firebase_uid` column (unique). On first valid login, create the row. Subsequent logins reuse it.
5. Protected routes return 401 without a valid token. Public routes: `/health`, and `/setup/status` if needed.
6. Frontend sends `Authorization: Bearer <token>` on every backend request, refreshing the token as Firebase does.
7. Document the flow in AGENTS.md.

**Constraints:** Service account JSON never committed or bundled. No passwords stored by the app. Firestore not used.

**Tests:** Token verification with a mocked token. Reject missing, malformed, and expired tokens.

**Acceptance check:** Register, log out, log in again. Same user row is used. A request without a token is rejected.

**Commit:** `Phase 3 done`

---

### Phase 4: Runtime paths and settings

**Goal:** Backend runs from any folder. Data lives in `%APPDATA%\KALKI`.

**Tasks:**
1. `backend/paths.py`: `get_data_dir()` returns `%APPDATA%\KALKI` and creates it. Used for database, mp3 cache, models, logs.
2. Settings loaded in this order: `<data_dir>\settings.json`, then environment variables, then defaults. No paths relative to the working directory or source file.
3. `resource_path(name)` helper: works in development and in a PyInstaller bundle (`sys._MEIPASS`).
4. Gemini key from settings or environment. With no key, return status `setup_required`. Do not crash.
5. `GET /setup/status`: reports key present, models present.
6. `POST /setup/key`: saves the key to `settings.json`. Never echoes the key back.
7. Rotating log file at `<data_dir>\logs\kalki.log`, plus console.

**Constraints:** Never log or print the key, even partially.

**Tests:** Data dir created. Starts with no key and returns `setup_required`. Saving a key is reflected by `/setup/status`.

**Acceptance check:** Run the backend from `C:\`. It starts, creates `%APPDATA%\KALKI`, reports `setup_required`.

**Commit:** `Phase 4 done`

---

### Phase 5: Bundle the backend

**Goal:** One `kalki-backend.exe` that runs without Python installed.

**Tasks:**
1. `backend/entry.py`: starts Uvicorn on `127.0.0.1`, port from `KALKI_PORT` (default 8765). Prints the port at startup.
2. `backend/kalki-backend.spec` (PyInstaller, onefile). Console off for release, on for a debug flag. Include hidden imports for uvicorn, sqlalchemy, edge-tts, openwakeword, firebase-admin.
3. `scripts/build_backend.ps1`: creates venv, installs requirements and pyinstaller, builds, copies exe to `electron/resources/backend/`.
4. Build script runs the exe from a temp folder and checks `GET /health`.
5. `GET /health` returns `{"status":"ok","version":"..."}`.

**Constraints:** Do not bundle `.env`, settings, Firebase service account, or any key. Do not bundle Whisper or wake-word models; they download on first run.

**Acceptance check:** Run the build script. Run the exe from another folder. `http://127.0.0.1:8765/health` responds.

**Commit:** `Phase 5 done`

---

### Phase 6: Electron installer and first-run setup

**Goal:** Installable Windows app that guides a new user through setup.

**Tasks:**
1. `main.js`: when packaged, spawn `resources/backend/kalki-backend.exe`. In development, keep the Python spawn. Read the port from stdout. Kill the backend on quit. Show an error window if it fails to start.
2. First-run screen (React): explains how to get a free Gemini key, button opens Google AI Studio via `shell.openExternal`, password-style input, Save via IPC to `POST /setup/key`. Never redisplay the saved key.
3. Settings screen to change the key later.
4. Store the key with Electron `safeStorage` in main.js. If unavailable, store with a visible warning. Pass the decrypted key to the backend via an environment variable at spawn, or the simplest documented method.
5. `electron-builder` in `package.json`: target NSIS, appId `com.kalki.assistant`, productName `KALKI`, per-user install (no admin), `extraResources` for the backend. Script `dist:win` writes to `dist/`.
6. `electron-updater`: check on launch, download in background, prompt restart. Publish to GitHub Releases. Leave a comment where owner and repo are set.
7. Add a Privacy section to AGENTS.md: where the key is stored; what leaves the machine (transcripts to the LLM, screen frames only when that feature is used).

**Constraints:** No secrets in repo or build. Grep the built app for the key to confirm. Keep HUD design unchanged.

**Acceptance check:** `npm run dist:win` produces an installer. Install it (test in Windows Sandbox). Setup screen appears. Valid key saves and chat answers.

**Commit:** `Phase 6 done`

---

### Phase 7: Release pipeline

**Goal:** Installers are built automatically when a version tag is pushed.

**Tasks:**
1. `.github/workflows/release.yml`: on tags `v*`, on `windows-latest`: set up Python 3.11 and Node LTS, run `build_backend.ps1`, `npm ci`, `npm run dist:win`, create a GitHub Release, attach the installer and `latest.yml`. Use only the built-in `GITHUB_TOKEN`.
2. CI on push: run `python backend/test_diagnostics.py` with no microphone and no keys.
3. `RELEASING.md`: bump version in `package.json`, tag, push. Clean-machine test checklist.
4. No step echoes environment variables.

**Constraints:** Do not publish on every push, only tags.

**Acceptance check:** Push tag `v0.1.0`. Release appears with the installer.

**Commit:** `Phase 7 done`

---

### Phase 8: Tool calling

**Goal:** The LLM decides which action to take by calling defined tools, replacing most regex routing.

**Tasks:**
1. Create `backend/tools/` with one file per tool. Each tool has: name, description, JSON schema, permission level (`safe`, `confirm`, `blocked`), and a Python function.
2. Starter tools: open application (allowlist of names → paths), set volume, get time/date, create timer, search files in user-chosen folders.
3. Gemini function calling: send tool schemas, execute the requested tool, return the result to the model, stream the final answer.
4. Keep the regex router as a fast path for simple, known commands.
5. Log every tool call to the audit log table (tool name, arguments, result status). Do not log secrets.

**Constraints:** No generic shell execution. No arbitrary file deletion. `type <text>` path removed or restricted to an allowlist.

**Tests:** Each tool with mocked execution. Unknown tool name rejected. Blocked tools never run.

**Acceptance check:** "Open Notepad" and "What time is it" work by voice. Unknown requests get a sensible answer.

**Commit:** `Phase 8 done`

---

### Phase 9: Safety confirmations

**Goal:** Risky actions require a spoken yes or no.

**Tasks:**
1. Tools marked `confirm` ask the user before running. The assistant speaks the question, listens for yes or no (Whisper transcript, keyword match), then acts or cancels.
2. Timeout: no answer within 10 s means cancel.
3. Confirmation state is shown in the HUD.

**Acceptance check:** A confirm-level tool asks first. "No" cancels. Silence cancels.

**Commit:** `Phase 9 done`

---

### Phase 10: Barge-in

**Goal:** User can speak over the assistant to stop it.

**Tasks:**
1. While speaking, keep the mic loop listening for voice activity.
2. On detected speech, stop TTS playback and clear the sentence queue.
3. Process the new speech as a new request.

**Acceptance check:** Interrupt a long answer. It stops within about a second and answers the new question.

**Commit:** `Phase 10 done`

---

### Phase 11: Memory

**Goal:** Remember the conversation and simple preferences.

**Tasks:**
1. Tables: `conversations`, `messages`, `preferences` (per user, linked to `users`).
2. Send recent messages (last N, configurable) to the LLM as context.
3. Voice commands to set and read preferences ("my name is ...", "call me ..."). Stored, not hardcoded.
4. A "forget everything" command that clears the user's memory after a confirmation.

**Acceptance check:** Tell it your name, restart the app, ask for your name. It remembers.

**Commit:** `Phase 11 done`

---

### Phase 12: Proactive features

**Goal:** Jarvis-style reminders and briefings.

**Tasks:**
1. Timers and reminders stored in the database. A local scheduler (APScheduler, free) checks them every few seconds and speaks them when due.
2. Morning briefing on wake-up command or at a set time: time, date, reminders for the day, a short weather line if a free weather source is configured.
3. Settings to turn proactive features on or off.

**Acceptance check:** "Remind me in two minutes" speaks the reminder after two minutes, including after a restart if the reminder is still pending.

**Commit:** `Phase 12 done`

---

## 7. Testing checklist (every phase)

1. `python backend/test_diagnostics.py` passes.
2. Backend starts with no internet and no keys (returns setup status, not a crash).
3. `git status` shows no secret files.
4. The phase's acceptance check passes on the user's machine.
5. Commit with the phase name. If a phase breaks things: `git reset --hard` to the last good commit.

**Before the public release (Phase 7):** Test the installer in Windows Sandbox. The Sandbox has no Python or Node, so it proves the installer is standalone.

---

## 8. Setup the user does once

1. Install Python 3.11 or 3.12, Node.js LTS, Git, and Antigravity.
2. Get a free Gemini key from Google AI Studio. Get a free Groq key from the Groq console (optional fallback). Keep both out of chats and Git.
3. Create the Neon project and copy its connection string into `backend/.env` only.
4. Create the Firebase project, enable Email/Password sign-in, and download the service account JSON to a folder **outside** the repo.
5. Run `git log --all --oneline -- backend/.env` and `git log -p --all -S "neon.tech" --oneline`. If either shows output, rotate the affected keys or passwords.
6. Turn on Windows Sandbox (Windows Features) for installer testing, when reaching Phase 7.

---

## 9. Status tracker

Update this section after each phase. Paste the updated file into new chats so the assistant knows where the project stands.

| Phase | Status | Date | Notes |
|---|---|---|---|
| 0 Cleanup and safety | COMPLETED | 2026-10-28 | Phase 0 tasks verified; all 5 diagnostics passing |
| 1 Streaming replies | NOT STARTED | | |
| 2 Hands-free voice loop | NOT STARTED | | |
| 3 Firebase login | NOT STARTED | | |
| 4 Runtime paths and settings | NOT STARTED | | |
| 5 Bundle backend | NOT STARTED | | |
| 6 Electron installer | NOT STARTED | | |
| 7 Release pipeline | NOT STARTED | | |
| 8 Tool calling | NOT STARTED | | |
| 9 Safety confirmations | NOT STARTED | | |
| 10 Barge-in | NOT STARTED | | |
| 11 Memory | NOT STARTED | | |
| 12 Proactive features | NOT STARTED | | |

**Open issues:** (list here as they come up)

**Last known good commit:** (fill in)

---

## 10. Glossary

- **Wake word:** A phrase like "hey jarvis" that starts listening.
- **VAD:** Voice activity detection. Detects when speech starts and stops.
- **Whisper:** Speech-to-text model. faster-whisper is a fast local version.
- **SSE:** Server-Sent Events. Lets the server push text to the browser as it's generated.
- **Function calling / tool use:** The LLM requests an action (like opening an app) and the app runs it.
- **Barge-in:** Interrupting the assistant while it talks.
- **safeStorage:** Electron's built-in way to encrypt small secrets using the Windows user account.
- **PyInstaller:** Packs Python code into one executable.
- **NSIS:** Installer format used by electron-builder.
