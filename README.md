# Beihang SmartFind
## 北航校园智能失物招领系统

An independent AI-powered university lost-and-found platform developed for Beihang University's Artificial Intelligence Practice course.

> This is an independent demonstration project. It is not an official Beihang University system and does not access real student records.

### Project capabilities
- Student registration, login, and role-based access.
- Lost and found item listings with image uploads.
- Search, candidate matching, ownership claims, and recovery workflows.
- Administrator review, listing management, campus-zone configuration, and analytics.
- English and Simplified Chinese interface support.
- Hybrid matching architecture combining text, image, category, color, time, and campus-zone signals.
- Gemini-assisted image/description analysis when a valid server-side API key is configured.
- OpenCLIP and multilingual E5 integrations with clearly identified fallback behavior.

### Repository structure
- `backend/` — FastAPI API, SQLAlchemy models, services, and tests.
- `frontend/` — Next.js, React, and TypeScript application.
- `docs/` — architecture, API, deployment, security, and evaluation notes.
- `data/` — small fictional demonstration assets and evaluation pairs.
- `report/` — academic report sources and rendered submission files.
- `scripts/` — development, seeding, evaluation, and report utilities.

### Local setup
1. Copy `.env.example` to `.env` and configure values locally. Never commit secrets.
2. Start the database and supporting services with Docker Compose.
3. Install backend dependencies from `backend/requirements.txt`.
4. Install frontend dependencies in `frontend/` with npm.
5. Run the backend and frontend using the commands in the project README and `docs/deployment.md`.

### AI configuration
Gemini calls are made only by the backend. Configure `GEMINI_API_KEY` and `GEMINI_MODEL` in the local environment. The platform should remain usable when external AI services or model weights are unavailable; fallback results must not be represented as real model inference.

### Verification
Run backend tests with:

```bash
cd backend
pytest -q
```

Follow `docs/evaluation.md` for the evaluation workflow. Distinguish deterministic demo/test results from live model evaluations.

### Privacy and security
- Use fictional demo data only.
- Do not upload real student identity documents or sensitive personal information.
- Keep API keys and database credentials out of source control.
- Review `docs/security.md` before any public deployment.

### License
Academic demonstration project. Add a license only if/when the project owner chooses one.
