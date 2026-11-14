> Final audit (14 November 2026): see [gap analysis](docs/FINAL_GAP_ANALYSIS.md), [executed verification](docs/verification/final-results.md), and [delivery checklist](docs/FINAL_DELIVERY_CHECKLIST.md). This branch adds real API-backed Smart Search/assistant, reliable report retries, private evidence downloads and local E2E coverage. It is **not a claim that every submission requirement or production release is complete**. Current pretrained E5/OpenCLIP inference is unverified; production uses explicit fallbacks. Existing production and this branch must be distinguished.

# Beihang SmartFind

Bilingual campus lost-and-found application. Students can browse, report items,
upload photographs, inspect matches, submit claims and receive in-app notifications
without registering or entering an email, username or password.

## Live services

- Website: https://beihang-smartfind.vercel.app
- API: https://smartfind-api-production.up.railway.app
- API documentation: https://smartfind-api-production.up.railway.app/docs
- Source: https://github.com/ahmed777334406-coder/ai

## Visitor privacy and sessions

The frontend automatically calls `POST /api/v1/auth/session`. The server generates
32 cryptographically random bytes, creates a database principal with no usable
password, and issues a signed, HttpOnly, SameSite=Lax cookie. Production cookies
are Secure. The session lasts 30 days (`VISITOR_SESSION_DAYS`); clearing cookies,
changing browsers or expiration loses access to that visitor's history. Reports
remain public, but private identifying details, claims, evidence, matches and
notifications are protected by server-side ownership checks.

Student registration is removed. `/login` and `/register` redirect to the visitor
dashboard. `/auth/login` accepts individually provisioned administrators only;
the administrator UI is at `/admin/login`. No public demo administrator is created.
Existing report ownership and database history are preserved. Anonymous principals
reuse the existing users table, so no destructive ownership migration is needed.

Mutating cookie requests require `X-SmartFind-Request: 1` and reject untrusted
Origin headers. CORS allows only configured origins. The API rate limiter is per
process; run one API worker/replica or replace it with shared limiting before
scaling. Uploads validate type, size, decoded image content and extension, then
re-encode images. Claim evidence is stored outside public media.

## Matching and AI: actual behavior

Matching ranks opposite-status reports using text, images, category, color,
campus-zone adjacency and time decay. Scores are 0–100 similarity measures,
**not ownership probabilities**. Missing signals are excluded and remaining
weights normalized. Results contain component evidence, method names and an
explanation. Administrators verify claims before marking recovery.

Optional local inference uses multilingual E5-small and OpenCLIP ViT-B-32.
Install `backend/requirements-ai.txt`, set `ENABLE_LOCAL_MODELS=true` and provision
sufficient memory/model cache. Without these resources the documented alternatives
are bilingual synonym/token hashing for text and OpenCV HSV histograms for images.
These are real computed heuristics, labeled fallback matching; they do not identify
objects or provide unrestricted multilingual understanding.

Google AI Studio is the confirmed provider. Production uses the official Google
Gen AI SDK with `gemini-3-flash-preview`, configured in backend Railway variables.
The previous `gemini-2.5-flash` model returned NOT_FOUND for this account;
`gemini-3.8-flash` returned temporary UNAVAILABLE during verification.
The working model supports description improvement, image analysis and structured
matching explanations. Text/image ranking still reports its actual embedding or
heuristic methods independently from the explanation provider.

Keys are kept only in backend environment variables, never in this repository or
frontend variables. Rotate keys shared in chat. Provider outages and errors use
explicitly labeled fallback results; configuration alone does not prove a live
request succeeded. `provider=google_gemini` in an operation response identifies a
successful live call. Description requests can select English or Simplified Chinese
with `target_language`.

## Local development

Requires Python 3.11+ and Node.js 22+.

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend .venv/bin/python scripts/bootstrap.py
.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
BACKEND_ORIGIN=http://localhost:8000 NEXT_PUBLIC_API_URL=/api/v1 npm run dev
```

SQLite is supported for development and isolated tests. Production requires
PostgreSQL with pgvector and migrations. Existing Alembic migrations preserve
schema and token revocation history. Do not run demo seeding in production.

## Production configuration

Railway uses `backend/Dockerfile` and `railway.json`, runs Alembic before startup,
and keeps `UPLOAD_DIR=/data/uploads` on the existing persistent `/data` volume.
Set `ENVIRONMENT=production`, `DATABASE_URL`, a strong unique `JWT_SECRET_KEY`,
explicit HTTPS `CORS_ORIGINS`, and private `ADMIN_EMAIL` / `ADMIN_PASSWORD` for
initial administrator provisioning. Do not reuse credentials across people.
The bootstrap only creates a missing administrator; it does not rotate passwords.

Vercel must use the existing `beihang-smartfind` project, root `frontend`:

```text
NEXT_PUBLIC_API_URL=/api/v1
NEXT_PUBLIC_API_ORIGIN=
BACKEND_ORIGIN=https://smartfind-api-production.up.railway.app
```

API and public media rewrites keep browser traffic on the website's origin,
which avoids third-party cookie restrictions. `BACKEND_ORIGIN` is server-side.
Never put AI keys in `NEXT_PUBLIC_*`, source control or browser storage.

## Verification

```sh
.venv/bin/pytest -q backend/tests
cd frontend
npm run lint
npm run build
npm run test:e2e -- e2e/smoke.spec.ts
```

The full browser recovery test uses isolated visitor contexts and optionally a
private administrator credentials JSON file specified by
`SMARTFIND_TEST_CREDENTIALS`. Run against a test database, not public production
records. `API_ORIGIN` and `BASE_URL` select its target. Backend tests cover reporting,
image validation, matching, filters, claims, recovery review, notifications, session
cookies, CSRF, visitor isolation and admin authorization. Live AI connectivity is checked separately against the configured Google model.
