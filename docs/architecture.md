# Architecture — Beihang SmartFind

## System boundary

SmartFind is a standalone academic application. It uses synthetic demonstration data and configurable campus zones. It does not connect to university identity, security, facilities, student-information or official lost-property systems.

## Components

1. **Next.js client** — responsive English/Simplified Chinese interface, local browser language preference, authenticated API requests and student/admin pages.
2. **FastAPI service** — versioned REST API, request validation, JWT authentication, role checks, upload endpoints and OpenAPI documentation.
3. **PostgreSQL + pgvector** — normalized relational records, audit/claim/notification history, 384-dimensional text vectors and 512-dimensional image vectors with cosine HNSW indexes. SQLite is used for tests and quick local runs.
4. **Gemini service** — official Google Gen AI SDK, server-side API key, structured image/text extraction, description refinement and evidence-grounded match explanations.
5. **Text embedding service** — multilingual E5 small with query/passage prefixes when model packages and weights are available; otherwise a labelled bilingual dictionary/hash fallback.
6. **Image embedding service** — OpenCLIP ViT-B/32 when available; otherwise a labelled HSV histogram fallback. Histogram similarity describes color distribution, not object identity.
7. **Hybrid matching service** — only pairs LOST reports with FOUND reports, combines available signals and renormalizes weights when a signal is missing.
8. **Storage service** — generated filenames, Pillow verification/re-encoding, EXIF removal, public listing image directory and non-public claim evidence directory.

## Matching formula

The initial configurable weights are:

| Signal | Weight |
|---|---:|
| Text similarity | 0.32 |
| Image similarity | 0.28 |
| Category | 0.12 |
| Color | 0.08 |
| Time | 0.10 |
| Campus-zone proximity | 0.10 |

For a candidate pair, let `A` be the set of available signals, `w_i` the configured weight and `s_i` the normalized signal score. The final score is:

`score = 100 × Σ(w_i × s_i) / Σ(w_i), for i in A`.

Missing signals are excluded from both numerator and denominator. They are not replaced with a perfect score. The score is a ranking score, not a probability of ownership. A student claim and human administrator review are required before recovery is confirmed.

## Matching lifecycle

`LOST report → FOUND report → AI candidate retrieval → student claim → administrator review → approved handover → RECOVERED`.

The system does not automatically recover an item when a score is high. Duplicate detection only returns warnings and does not delete or merge reports.

## Data flow

1. Student submits a lost or found listing.
2. The backend stores the report and a text embedding (pretrained E5 or explicitly labelled fallback).
3. If an image is uploaded, the storage service validates and re-encodes it; the image service stores an OpenCLIP vector or labelled color-histogram vector. Gemini analysis is attempted only when configured.
4. The matching service compares the new report against opposite-status reports and stores top candidates.
5. Notifications are created with unique deduplication keys.
6. A student submits private identifying details for a found item.
7. Administrators compare claim details with private report details and approve, reject or request more evidence.
8. An approved claim changes the found report and linked lost report to RECOVERED and generates a notification.

## Operational modes

- **Quick local mode:** SQLite, no external API key, fallback AI methods, synthetic seed data.
- **Full local mode:** PostgreSQL/pgvector, Gemini API key, optional E5 and OpenCLIP model packages/weights.
- **Container mode:** Docker Compose with PostgreSQL pgvector and persistent volumes. Container startup applies Alembic migrations before launching FastAPI.

## Model lifecycle and resources

Model loading is lazy and cached at process level. Device selection supports CUDA, Apple Silicon MPS and CPU. Weight download failures do not prevent the non-AI listing and claim workflows from operating. Provider/method fields are stored with generated embeddings so the system does not silently compare incompatible vector methods.
