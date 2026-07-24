# 11 — Configuration Reference

## 1. Executive Summary

KAIO utilizes centralized environment configuration managed by `pydantic-settings` (`backend/app/config/settings.py`) and meeting subsystem settings (`backend/app/meeting/config.py`). Environment variables are loaded from `backend/.env`.

---

## 2. Application Settings (`backend/app/config/settings.py`)

The `Settings` class uses `pydantic-settings` with `SettingsConfigDict(env_file=".env", extra="ignore")`.

| Variable Key | Type | Default / Required | Description |
|---|---|---|---|
| `DATABASE_URL` | `str` | **Required** | PostgreSQL connection string. Format: `postgresql://user:password@host:port/dbname` |
| `JWT_SECRET` | `str` | **Required** | Secret key used for signing JWT access tokens. Must be a long random string in production. |
| `JWT_ALGORITHM` | `str` | `"HS256"` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `30` | Access token TTL in minutes. The auth router overrides cookie max_age to 15 min. |
| `SMTP_EMAIL` | `str \| None` | `None` | SMTP sender email address for invitation and notification emails. If `None`, email dispatch is skipped. |
| `SMTP_PASSWORD` | `str \| None` | `None` | SMTP sender account password. |
| `FRONTEND_ORIGINS` | `str` | `"http://localhost:5173,http://localhost:3000"` | Comma-separated list of allowed CORS origins. |

**Example `.env` file**:
```env
DATABASE_URL=postgresql://postgres:Password%40123@localhost:5432/kaio_db
JWT_SECRET=your-very-long-random-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SMTP_EMAIL=noreply@yourapp.com
SMTP_PASSWORD=your-smtp-password
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 3. Cookie Auth Configuration (`backend/app/routers/auth.py`)

These are hardcoded in the `set_auth_cookies()` helper and not environment-driven:

| Cookie | Max Age | Scope | httpOnly | SameSite |
|---|---|---|---|---|
| `access_token` | 15 minutes (900s) | `/` | `true` | `lax` |
| `refresh_token` | 7 days (604800s) | `/api/v1/auth` | `true` | `lax` |

> [!CAUTION]
> `secure=False` is hardcoded for local development. In production with HTTPS, this MUST be set to `True`.

---

## 4. Meeting Subsystem Configuration (`backend/app/meeting/config.py`)

| Setting Key | Type | Default | Description |
|---|---|---|---|
| `MEETING_GOOGLE_EMAIL` | `str` | **Required** | Google Meet bot user email for Playwright login. |
| `MEETING_GOOGLE_PASSWORD` | `str` | **Required** | Google Meet bot user password. |
| `MEETING_PROFILE_DIR` | `str` | `storage/meeting/profile` | Chromium browser profile persistent storage path (for session retention). |
| `MEETING_BOT_NAME` | `str` | `KAIO Bot` | Display name of Playwright bot shown in meeting roster. |
| `MEETING_HEADLESS` | `bool` | `false` | Run Playwright Chromium in headless mode. Set `true` on CI/production servers. |
| `MEETING_JOIN_TIMEOUT` | `int` | `60` | Max seconds to wait for Google Meet room join before timeout. |
| `MEETING_SPEECH_PROVIDER` | `str` | `deepgram` | Speech processing provider key. |
| `MEETING_DEEPGRAM_API_KEY` | `str` | **Required** | Cloud API key for Deepgram Nova-3. |
| `MEETING_DEEPGRAM_MODEL` | `str` | `nova-3` | Deepgram speech model identifier. |
| `RECORDING_OUTPUT_DIR` | `Path` | `storage/meeting/recordings` | Directory where raw `recording.webm` files are saved. |
| `PROCESSING_OUTPUT_DIR` | `Path` | `storage/meeting/processed_audio` | Directory for all pipeline output artifacts per session. |
| `CANONICAL_SAMPLE_RATE` | `int` | `16000` | Target sample rate (Hz) for FFmpeg WAV conversion. |
| `CANONICAL_CHANNELS` | `int` | `1` | Mono audio channel count for FFmpeg output. |
| `MAX_CONCURRENT_SESSIONS` | `int` | `3` | Maximum active concurrent Playwright bot instances. |
| `MEETING_TIMEOUT` | `int` | `3600` | Maximum meeting runtime in seconds before automatic bot teardown. |
| `EXTRACTION_MAX_RETRIES` | `int` | `3` | Maximum retry attempts for transient LLM task extraction errors. |
| `EXTRACTION_CHUNK_TOKEN_LIMIT` | `int` | `4000` | Maximum token window per transcript chunk sent to LLM. |
| `EXTRACTION_MIN_TRANSCRIPT_WORDS` | `int` | `20` | Minimum word count threshold before LLM extraction runs (avoids empty meeting extraction). |

---

## 5. AI / LLM Configuration (`backend/app/ai/config/`)

| Variable Key | Type | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | `str` | `puter` | Active LLM provider. Options: `puter`, `gemini`. |
| `AI_MODEL` | `str` | `gpt-4o-mini` | Model identifier for the active provider. |
| `PUTER_API_KEY` | `str` | Optional | API key for Puter LLM gateway (if using `puter` provider). |
| `GEMINI_API_KEY` | `str` | Optional | Google Gemini API key (if using `gemini` provider). |

---

## 6. Frontend Configuration

The Vite dev server is configured in `frontend/vite.config.ts`. There is no `.env` required on the frontend — API calls go to the backend via relative `/api/v1/...` paths or a proxy configured in Vite.

| Setting | Value | Description |
|---|---|---|
| Dev Server Port | `5173` | Vite default dev server port (`npm run dev`) |
| Backend API Base | `/api/v1` | All API calls prefixed with `/api/v1` |
| Tailwind | v4 via `@tailwindcss/vite` | No `tailwind.config.js` needed in v4 |

---

## 7. CORS Configuration

Configured in `backend/app/main.py` using `CORSMiddleware`:
- **Allowed Origins**: Parsed from `FRONTEND_ORIGINS` env var (comma-separated).
- **Credentials**: `allow_credentials=True` — required for httpOnly cookie auth.
- **Methods/Headers**: `["*"]` — all methods and headers allowed.

> [!WARNING]
> `allow_credentials=True` combined with `allow_origins=["*"]` is forbidden by browsers. Always specify explicit origins in `FRONTEND_ORIGINS`.

---

## 8. Running the Application

### Backend
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

### Database (initial setup)
```powershell
# Apply all 37 migrations (no data loss)
python database/scripts/rebuild.py

# Full reset + seed (destroys data)
python database/scripts/rebuild.py --reset
```
