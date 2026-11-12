# Beihang SmartFind

**北航校园智能失物招领系统** — an independent AI-powered, bilingual campus lost-and-found project for the Beihang University Artificial Intelligence Practice course.

> This is an independent student project. It is not an official Beihang University service and has no access to official university systems or real student records. The included demonstration records are synthetic.

## What is implemented

- Student registration, login, JWT sessions, student/admin roles and profile retrieval.
- Lost and found listing creation, browsing, search, update and soft close.
- Public listing photos with server-generated filenames, decoded-content/extension matching, a 25-megapixel limit, size limits and EXIF-stripping re-encoding.
- Private claim evidence storage and administrator-only access to claim verification details.
- Gemini integration through the official Google Gen AI Python SDK, with structured item analysis, description assistance and evidence-grounded match explanations. It is optional at startup and degrades transparently when credentials or the SDK are unavailable.
- Optional multilingual E5 text embeddings and OpenCLIP ViT-B/32 image embeddings. When those large model packages or weights are not available, the backend labels and uses a bilingual rule-hash text fallback and an HSV histogram image fallback; these are not represented as E5 or CLIP inference.
- Hybrid LOST-to-FOUND matching with configurable weights, missing-signal weight redistribution, top-five ranking, evidence explanations and deduplicated notifications.
- Same-status duplicate warnings. Possible duplicates are never deleted automatically.
- Student claims, administrator review, linked LOST/FOUND recovery state transitions, audit events and in-app notifications.
- Student and administrator dashboards, category/zone analytics, and English/Simplified Chinese translation for navigation, landing, authentication, reporting and key workflow labels. Remaining admin/secondary copy still needs final translation QA.
- Synthetic demonstration dataset, repeatable seed script, evaluation script, CSV/JSON outputs and a chart.
- PostgreSQL + pgvector schema and HNSW cosine indexes for production/local Docker; SQLite is the zero-service development/test fallback.

## Repository layout

```text
frontend/       Next.js + React + TypeScript + Tailwind UI
backend/        FastAPI, SQLAlchemy, Alembic, Gemini and embedding services
backend/tests/  API and workflow tests
backend/migrations/  database migrations
data/demo/      generated synthetic item images and sample data
scripts/        seed, evaluation, source-line counting and local development
 docs/          architecture, API, security and evaluation notes
report/         academic report draft and final outputs
```

## Requirements

- Python 3.11+
- Node.js 22+
- PostgreSQL 16 with pgvector for the full vector-database deployment, or SQLite for the local smoke-test path
- Optional: Google Gemini API key, plus model dependencies/weights for multilingual E5 and OpenCLIP

## Local development on macOS

```bash
# 1. From the project root
cp .env.example .env

# 2. Create a Python environment and install the backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Optional live AI/model packages (large downloads)
pip install -r backend/requirements-ai.txt

# 4. Install the Next.js dependencies
cd frontend
npm install
cd ..

# 5. Seed synthetic demo accounts, zones, listings and images
make seed

# 6. Start FastAPI and Next.js together
make dev
```

Open:

- Frontend: http://localhost:3000
- FastAPI health: http://localhost:8000/health/ready
- Interactive API docs: http://localhost:8000/docs

The default local database is SQLite. The backend creates its tables on startup for the quick-start path. Use `make migrate` to apply the Alembic migration explicitly.

## Docker Compose (PostgreSQL + pgvector)

```bash
cp .env.example .env
# Edit .env and set a strong JWT_SECRET_KEY, a unique ADMIN_PASSWORD,
# and GEMINI_API_KEY if live Gemini is required.
docker compose up --build
# In a second terminal, seed the synthetic demo records:
docker compose exec backend python /app/scripts/seed_demo.py
```

The Compose database uses `pgvector/pgvector:pg16`, a persistent database volume and a persistent upload volume. The backend image installs core dependencies by default. To include the large AI packages in the image, set `INSTALL_AI_DEPS=true` in `.env` before building. Model weights are downloaded lazily on first use and may require network access and substantial disk space.

## AI configuration

Set these in `.env`:

```dotenv
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.1-flash-lite
TEXT_EMBEDDING_MODEL=intfloat/multilingual-e5-small
IMAGE_EMBEDDING_MODEL=ViT-B-32
AI_DEVICE=auto
```

All Gemini requests run on the backend. The API key is never sent to the browser. The model identifier is configurable because provider model availability can change; verify that the selected model is enabled for your Google AI Studio/API account before a live integration test. No Gemini key was included in this source package.

`AI_DEVICE=auto` selects CUDA, Apple Silicon MPS or CPU when available. If E5 or OpenCLIP weights cannot be loaded, the API exposes the fallback method name in its responses. The fallback methods are useful for a basic demonstration but are not equivalent to the requested pretrained models.

## Demo accounts

After `make seed`:

| Role | Email | Password |
|---|---|---|
| Student | `student@example.edu` | `StudentDemo123!` |
| Student / finder | `finder@example.edu` | `FinderDemo123!` |
| Administrator | `admin@example.edu` | value of `ADMIN_PASSWORD` in `.env` (default local-only value: `ChangeThisAdminPassword!`) |

Change the administrator password and JWT secret before sharing or deploying the project. The default credentials are for local synthetic demonstration only.

## Useful commands

```bash
make test        # backend API/workflow tests
make seed        # seed synthetic demo data
make migrate     # Alembic migration
make evaluation  # run synthetic retrieval evaluation and generate CSV/JSON/chart
make count       # count meaningful first-party source lines
make build       # Python compile check + Next.js production build
```

## API overview

All application APIs are versioned under `/api/v1/`.

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `GET/POST /listings`, `GET /listings/mine`, `GET /listings/{id}`, `PATCH/DELETE /listings/{id}`
- `POST /listings/{id}/images`, `GET /listings/zones/list`
- `GET /ai/status`, `POST /ai/analyze`, `POST /ai/description`, `POST /ai/search`, `POST /ai/assistant`
- `POST /ai/match/{listing_id}`, `POST /ai/duplicates/check`, `POST /ai/duplicates/{listing_id}`
- `GET /matches`, `GET /matches/{id}`, `POST /matches/{id}/feedback`
- `POST /claims`, `GET /claims`, `GET /claims/{id}`, `POST /claims/{id}/evidence`
- Admin-only private evidence download: `GET /admin/claims/{id}/evidence`
- `GET /notifications`, `PATCH /notifications/{id}/read`
- Admin: `/admin/dashboard`, `/admin/listings`, `/admin/claims`, `/admin/users`, `/admin/analytics`
- Health: `/health/live`, `/health/ready`

## Evaluation

Run `make seed` followed by `make evaluation`. Outputs are written to `docs/evaluation/`:

- `evaluation_results.json`
- `retrieval_rankings.csv`
- `cross_language_results.csv`
- `mrr_comparison.png`

The included evaluation is deliberately labelled as a small synthetic demonstration. The recorded methods identify the fallback implementations currently available in this offline execution environment. The metrics must not be presented as real-world campus performance or as pretrained CLIP/E5 results.

## Current verification snapshot

- Backend Python compilation: passed.
- Backend API/workflow tests: 18 passed (`python -m pytest -q` from `backend/`).
- FastAPI live smoke test: `/health/live` and `/health/ready` returned 200. A synthetic end-to-end workflow registered two students, created LOST/FOUND reports, uploaded an image, generated matches, submitted a claim, approved it as admin, confirmed both linked reports became `RECOVERED`, and confirmed the approval notification.
- Synthetic seed: 4 lost reports, 5 found reports and 5 campus zones.
- Synthetic evaluation: completed; results and limitations are in `docs/evaluation/evaluation_results.json`.
- Meaningful first-party source lines: 2,541 across 59 source files; backend application 1,466 lines, frontend 288 lines, tests 275 lines, scripts 471 lines and migrations 39 lines. Backend + frontend application source: 1,754 lines, excluding blank lines, comments, dependencies and generated artifacts.
- Frontend TS/TSX syntax parse: passed for all 24 current TypeScript/TSX source files. The full `tsc`/Next.js build remains unverified because React/Next packages could not be installed.
- Next.js production build: not run because the execution environment could not reach the npm registry and frontend packages are not installed.
- Live Gemini: not verified; no API key was supplied.
- Real OpenCLIP/E5 inference: not verified; model packages/weights were unavailable in this offline environment.
- PostgreSQL/pgvector Docker run: not verified; Docker is not installed in this environment.
- Alembic migration: passed against a fresh SQLite database and created all 13 application tables plus `alembic_version`.
- Vercel deployment: not created. No SmartFind GitHub repository exists yet; the available `ai` and `ai-coash` repositories are empty and have different names. The project was not pushed to either without confirmation.

See `docs/` and `report/` for the detailed implementation, verification evidence, deployment instructions and academic-report status. Read `docs/deployment.md` before creating cloud resources.
