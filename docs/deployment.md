# Existing SmartFind deployment and release guide

Last inspected: 14 November 2026. Reuse `ahmed777334406-coder/ai`, Vercel `beihang-smartfind` and Railway project `Beihang SmartFind`. Do not create duplicate services or touch Football Coach.

## Verified current production

Frontend: https://beihang-smartfind.vercel.app — existing production deployment `dpl_3NUfEmk4Lfe66mNn3nMAKQSeK4tD`, READY. Backend: https://smartfind-api-production.up.railway.app — deployment `7bb84f90-f447-43db-beaa-eee0ce902f36`, SUCCESS; reported source commit `685112e4b4527691abf507a673450213de1119a3`. `/health/ready` returned ready/PostgreSQL. These statuses describe the existing deployment, not this feature branch.

Railway project: `f0e72604-ab53-4653-b5c9-c9a96298d78d`; production environment `b59afb6a-2623-4972-9b97-f7bc82977613`; API service `533de1e3-a175-4674-a873-037cd16f9904`; Postgres service `3e078b6d-d8ae-40bc-9c62-5d7cf6732313`. Vercel project ID: `prj_YSbxPj70ncdvC4YTgGYFWwcMooys`.

Gemini currently reports `gemini-3-flash-preview`; real text inference was verified. Do not replace a working production model solely because a documentation example names another model. E5 and OpenCLIP are disabled in current production.

## Configuration

Backend requires production PostgreSQL/pgvector, a strong JWT_SECRET_KEY, administrator credentials, explicit HTTPS CORS_ORIGINS, persistent UPLOAD_DIR, and optionally server-only GEMINI_API_KEY. Never copy provider/database secrets to frontend bundles or reports. Preserve the existing upload volume and database.

Frontend root remains `frontend`, Node 22, install `npm ci`, build `npm run build`. In this branch, production browser calls use the same-origin proxy; `BACKEND_ORIGIN=https://smartfind-api-production.up.railway.app` selects the existing API and is also the default. NEXT_PUBLIC_API_URL/NEXT_PUBLIC_API_ORIGIN only override development routing. A backend/frontend release must be tested together.

## Release sequence

1. Review the feature PR, pass pytest, lint, typecheck, build, isolated Playwright and PostgreSQL/pgvector CI.
2. Take coordinated database/upload backups and verify rollback ownership and storage configuration.
3. Test migration `0003_report_idempotency` on a staging copy. It adds a nullable column and owner/request uniqueness; existing records retain null keys. It requires a normal PostgreSQL table lock during DDL. It does not delete records or regenerate vectors.
4. Stage the existing API service at the reviewed commit, observe terminal SUCCESS and health/readiness. Do not redeploy an old source snapshot by mistake.
5. Stage the existing frontend with the same reviewed source and test same-origin cookies, CSRF/CORS, image URLs and private evidence.
6. Plan transition for visitors holding only an API-domain cookie. Cookies cannot be transferred between unrelated domains automatically; do not infer identity from public reports. Keep the original sessions/records intact.
7. Promote only verified deployments and record both exact deployed SHAs. Re-check health, anonymous reload, claims and existing images without creating public synthetic reports.

No production deployment or migration was performed in this audit because release gates remain open. Do not describe a feature-branch commit as deployed. A generic old-snapshot Railway redeploy is insufficient to ship new code.

## Local reproduction

Create `.venv`, install `backend/requirements.txt`, then `cd frontend && npm ci`. From repository root, `bash scripts/test-e2e-local.sh` creates disposable data/uploads, runs migrations and seed, builds the frontend, starts both servers, runs Playwright, and cleans up. It never targets production. For isolated PostgreSQL tests, use a disposable database and `TEST_DATABASE_URL`; the pytest fixture creates/drops its tables. Never point TEST_DATABASE_URL at production.

Remote verification update: run 43540537239 passed frontend checks, PostgreSQL 17/pgvector migrations plus 41 tests, and six isolated E2E workflows on code commit 7ea7a41. Remaining release gates concern production storage, cookie transition, staging AI/image validation and coordinated rollout.
