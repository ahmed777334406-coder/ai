> Historical archive verification. For current deployed results, see [current-session.md](current-session.md).

# Beihang SmartFind — Verification Results

Date: 2026-11-11 (execution environment)

## Automated backend tests

Command: `python -m pytest -q` from `backend/`

Result: **18 passed**.

Coverage includes registration/login, role authorization, listing privacy, LOST-to-FOUND matching, claim approval, recovery state, notifications, image upload, fallback honesty, duplicate warnings, private claim data, cross-language fallback search, missing-signal normalization, cosine similarity clamping, and image extension/content validation.

## Live API and synthetic end-to-end workflow

The FastAPI server was started with Uvicorn using SQLite. `/health/live` and `/health/ready` returned HTTP 200; readiness reported `sqlite`. OpenAPI exposed 37 versioned/application paths.

A separate synthetic workflow was executed over HTTP:

1. Register two student accounts.
2. Create a LOST report and a matching FOUND report.
3. Upload a valid PNG image.
4. Run matching and retrieve five candidates.
5. Submit a claim tied to the candidate match.
6. Log in as the seeded administrator and approve the claim.
7. Verify that both linked listings became `RECOVERED`.
8. Verify that the claimant received a `CLAIM_APPROVED` notification.

Observed methods: `opencv_hsv_histogram_fallback` for image representation and `rule_fallback` for Gemini analysis. These are not pretrained OpenCLIP or live Gemini results. The selected candidate score was 63.34 and is a ranking score, not a probability.

## Database migration

Alembic upgrade was executed against a fresh SQLite database. It created the 13 application tables plus `alembic_version` successfully.

## Synthetic retrieval evaluation

Dataset: 4 synthetic LOST records, 5 synthetic FOUND records and 3 known positive pairs.

| Method | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|
| Text-only fallback | 0.20 | 1.00 | 1.00 |
| Image-only HSV histogram | 0.20 | 1.00 | 1.00 |
| Hybrid | 0.20 | 1.00 | 1.00 |

All three known cross-language demonstration pairs ranked at position 1 using the bilingual rule/hash fallback. The sample is small and synthetic; these values are not generalizable and do not measure pretrained E5 or CLIP.

## Source counts

- Total meaningful first-party source: 2,541 lines across 59 source files.
- Backend application: 1,466 lines.
- Frontend: 288 lines.
- Tests: 277 lines.
- Scripts: 471 lines.
- Migrations: 39 lines.
- Backend + frontend application source: 1,754 lines.

The count excludes blank lines, comment-only lines, dependencies, caches, generated output and release archives.

## Not verified / blocked

- Next.js package installation and production build: blocked because the environment could not resolve `registry.npmjs.org`. `make build` completed Python compilation, then stopped at the frontend step with `next: not found` because the npm packages were not installed.
- Full browser screenshot capture: Chromium navigation to localhost returned `ERR_BLOCKED_BY_ADMINISTRATOR`.
- Live Gemini: no API key supplied; SDK not installed in the execution environment.
- Pretrained multilingual E5 and OpenCLIP: optional packages and model weights unavailable.
- PostgreSQL/pgvector Docker deployment: Docker runtime unavailable; only SQLite migration was exercised.
- GitHub push and Vercel deployment: not performed. The GitHub account has two empty repositories named `ai` and `ai-coash`, but no repository named `Beihang-SmartFind`; no files were pushed to an unrelated repository without confirmation.

No synthetic output is described as real university data, and no fallback method is described as a pretrained model.
