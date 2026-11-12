# Deployment Guide — Beihang SmartFind

The application is prepared for a separate frontend and backend deployment. A production deployment has **not** been created yet. Do not deploy the current frontend with its default `localhost` API URL.

## 1. Backend

Deploy `backend/` as a persistent Python service using `backend/Dockerfile` (the Dockerfile is designed to run Alembic migrations before Uvicorn). Provision PostgreSQL 16 with the pgvector extension and persistent storage for uploads.

Required backend environment variables:

```dotenv
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
JWT_SECRET_KEY=<at-least-32-random-characters>
ADMIN_EMAIL=<administrator-email>
ADMIN_PASSWORD=<unique-strong-password>
UPLOAD_DIR=/app/uploads
FRONTEND_URL=https://<your-vercel-domain>
CORS_ORIGINS=https://<your-vercel-domain>
GEMINI_API_KEY=<optional-server-side-key>
GEMINI_MODEL=gemini-3.1-flash-lite
```

Keep `GEMINI_API_KEY`, database credentials and JWT secrets only in the backend host's secret manager. Do not put them in Vercel `NEXT_PUBLIC_*` variables or commit them.

The backend stores uploaded listing photos and private claim evidence on disk. The hosting service must provide a persistent volume mounted at `UPLOAD_DIR`, or the storage service must be replaced with a durable object-storage adapter before using ephemeral serverless storage.

## 2. Frontend on Vercel

After the source is pushed to a dedicated GitHub repository, create a Vercel project linked to that repository and set the root directory to `frontend/`.

Build command: `npm run build`

Install command: `npm install`

Framework: Next.js

Required build-time public environment variables:

```dotenv
NEXT_PUBLIC_API_URL=https://<backend-domain>/api/v1
NEXT_PUBLIC_API_ORIGIN=https://<backend-domain>
```

Set the exact Vercel production and preview origins in the backend `CORS_ORIGINS` value. Rebuild the frontend after changing `NEXT_PUBLIC_*` values because Next.js embeds them into the client bundle at build time.

## 3. Seed and administrator setup

Run the synthetic seed script only against a development or demonstration database:

```bash
python scripts/seed_demo.py
```

The seed script creates synthetic users, listings, campus-zone labels and generated demonstration images. Change the administrator password and JWT secret before exposing the service publicly. Never seed synthetic records into a production database containing real student records.

## 4. Pre-release checks

- Run `python -m pytest -q` from `backend/`.
- Run the synthetic evaluation with `PYTHONPATH=backend python scripts/evaluate.py`.
- Confirm `/health/live` and `/health/ready` return HTTP 200.
- Confirm the frontend production build succeeds.
- Complete a browser workflow at desktop and mobile widths.
- Confirm PostgreSQL/pgvector migrations and vector queries on the target database.
- Verify Gemini using a real API key if that feature is enabled.
- Confirm persistent upload storage, HTTPS, CORS, rate limiting and backup/restore procedures.

## 5. Current blocker

The connected GitHub account currently exposes two empty repositories named `ai` and `ai-coash`, but no repository named `Beihang-SmartFind`. The available GitHub actions can push files/commits to an existing repository but do not expose repository creation. No source has been pushed to either unrelated empty repository. Create a dedicated repository named `Beihang-SmartFind` (or explicitly authorize use of one of the empty repositories) before linking it to Vercel.

## Actual deployment (12 November 2026)

The existing Vercel project `beihang-smartfind` uses root directory `frontend`, Node 22, `npm ci`, and `npm run build`. Its production domain remains https://beihang-smartfind.vercel.app.

SmartFind's independent Railway project contains `Postgres` (PostgreSQL 17/pgvector, persistent database volume) and `smartfind-api` (Dockerfile `backend/Dockerfile`, persistent `/data` upload volume). API: https://smartfind-api-production.up.railway.app. Startup runs Alembic migrations, idempotent campus setup and Uvicorn on `$PORT`. Database URLs are normalized to `postgresql+psycopg`.

Configured backend variables: `ENVIRONMENT`, `DATABASE_URL` (Railway service reference), `JWT_SECRET_KEY` (private generated value), `UPLOAD_DIR=/data/uploads`, `FRONTEND_URL`, `CORS_ORIGINS`, `PORT=8000`, `GEMINI_MODEL=gemini-2.5-flash`, `ENABLE_LOCAL_MODELS=false`, `ADMIN_EMAIL` and private `ADMIN_PASSWORD`.

Configured Vercel variables: `NEXT_PUBLIC_API_URL=https://smartfind-api-production.up.railway.app/api/v1` and `NEXT_PUBLIC_API_ORIGIN=https://smartfind-api-production.up.railway.app`.

Only `GEMINI_API_KEY` is still required for live Gemini calls. Set it in SmartFind Railway Variables, never in a `NEXT_PUBLIC_*` variable. Choose another `GEMINI_MODEL` only if needed for your key's available models. Enabling local pretrained inference additionally requires optional packages/weights, `INSTALL_AI_DEPS=true` at build, `ENABLE_LOCAL_MODELS=true` and adequate memory/cache storage. Rebuild and re-embed existing listings when representation methods change; do not compare embeddings from different methods.

The deployed backend is pinned to the verified commit. To deploy later source changes, reconnect the same SmartFind service to the intended reviewed commit. Do not create or modify any Football Coach service.

The service also sets `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile` and explicit Dockerfile/healthcheck/restart settings through Railway service configuration. A generic redeploy initially selected Railpack and failed to detect the monorepo application; explicit settings correct the build selection. Railway now deprecates `railwayConfigFile` updates, so dashboard/API service settings are authoritative rather than that deprecated update field.
