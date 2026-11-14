# Final gap analysis — 14 November 2026

Baseline: `9281839`. Source inspection precedes changes. Historical documentation and screenshots are not fresh verification. This document records initial findings; final executed results are in `docs/verification/final-results.md`.

| Feature | Initial status | Source evidence / finding |
|---|---|---|
| Anonymous sessions | Partially implemented | auth.py: HttpOnly 30-day SameSite=Lax cookie, revocation; direct cross-site Railway API cookies incompatible with Lax; no expiry recovery UI |
| Private history | Implemented, verification pending | dependencies.py; owner filters in listings.py, claims.py, notifications.py, matches.py |
| Admin authentication | Partially implemented | ADMIN role checks; browser localStorage token exposed to XSS; move to sessionStorage as bounded compatible improvement |
| Reports and uploads | Partially implemented | listings.py, storage.py: format/size checks, re-encoding; report page incorrectly treats saved report as failed if image fails |
| Gemini | Configured status is not inference proof | gemini.py official SDK + validated JSON, silent fallback; lacks explicit provider timeout/retry bounds |
| E5 | Optional / blocked on resources | embeddings.py: optional multilingual-e5-small, explicit bilingual hash fallback; pretrained inference not yet verified |
| OpenCLIP | Optional / blocked on resources | vision.py: optional ViT-B-32, HSV fallback; pretrained inference not yet verified |
| Model migration | Partial | 384/512 fixed dimensions and method guards; configurable models can mislabel incompatible representations |
| Hybrid ranking | Broken cases | matching.py: normalizes available signals but includes same-owner pairs and returns unrelated low-score matches |
| Semantic retrieval | Broken cases | ai.py: returns zero-similarity rows and recovered/moderated reports; PostgreSQL omits records with older methods entirely |
| Smart search + assistant UI | Missing | API routes exist; no frontend page invokes search/assistant |
| Claims / recovery | Partial | admin.py: review, evidence route, audit log; claim creation not locked against approval; review lock order can deadlock |
| Evidence privacy | Implemented, verification pending | private directory, admin-only evidence endpoint; frontend lacks download control |
| Personal editing/closing | Partial | backend owner APIs exist; dashboard only shows first three reports, lacks controls |
| EN / zh | Partial | i18n.tsx; many hardcoded strings, statuses, notifications and admin UI |
| UI / mobile | Partial | existing responsive CSS and browser tests; current run pending |
| Rate limiting | Partial | main.py: in-process; AI shares broad 300/min quota |
| PostgreSQL / pgvector | Implemented, verification pending | vector columns + HNSW, migrations; isolated database required |
| Storage / backups | External verification needed | disk-based uploads require persistent volume; no verified restore exercise |
| Automated tests | Partial | pytest + Playwright; workflow defaults to production API and legacy registration helper; must block production mutations |
| Documentation / report | Partial | existing outputs preserved; deployment guide contains contradictory outdated setup claims |
| Production / CI | External verification needed | existing services only; no production writes or destructive migrations authorized |

## Source inventory

- `frontend/app/admin/analytics/page.tsx` (6 lines)
- `frontend/app/admin/claims/page.tsx` (6 lines)
- `frontend/app/admin/listings/page.tsx` (6 lines)
- `frontend/app/admin/login/page.tsx` (8 lines)
- `frontend/app/admin/page.tsx` (7 lines)
- `frontend/app/admin/zones/page.tsx` (5 lines)
- `frontend/app/claims/page.tsx` (6 lines)
- `frontend/app/dashboard/page.tsx` (14 lines)
- `frontend/app/item/[id]/page.tsx` (14 lines)
- `frontend/app/layout.tsx` (5 lines)
- `frontend/app/listings/[status]/page.tsx` (13 lines)
- `frontend/app/login/page.tsx` (2 lines)
- `frontend/app/matches/page.tsx` (8 lines)
- `frontend/app/notifications/page.tsx` (6 lines)
- `frontend/app/page.tsx` (8 lines)
- `frontend/app/profile/page.tsx` (34 lines)
- `frontend/app/register/page.tsx` (2 lines)
- `frontend/app/report/[status]/page.tsx` (13 lines)
- `frontend/app/settings/page.tsx` (6 lines)
- `frontend/components/AppShell.tsx` (63 lines)
- `frontend/components/ItemCard.tsx` (7 lines)
- `frontend/components/Ui.tsx` (5 lines)
- `frontend/lib/api.ts` (26 lines)
- `frontend/lib/i18n.tsx` (39 lines)
- `backend/app/__init__.py` (0 lines)
- `backend/app/api/__init__.py` (0 lines)
- `backend/app/api/router.py` (11 lines)
- `backend/app/api/routes/__init__.py` (0 lines)
- `backend/app/api/routes/admin.py` (161 lines)
- `backend/app/api/routes/ai.py` (151 lines)
- `backend/app/api/routes/auth.py` (71 lines)
- `backend/app/api/routes/claims.py` (67 lines)
- `backend/app/api/routes/listings.py` (133 lines)
- `backend/app/api/routes/matches.py` (54 lines)
- `backend/app/api/routes/notifications.py` (19 lines)
- `backend/app/config.py` (53 lines)
- `backend/app/database.py` (29 lines)
- `backend/app/dependencies.py` (28 lines)
- `backend/app/main.py` (86 lines)
- `backend/app/models.py` (193 lines)
- `backend/app/schemas.py` (132 lines)
- `backend/app/security.py` (44 lines)
- `backend/app/services/__init__.py` (0 lines)
- `backend/app/services/embeddings.py` (69 lines)
- `backend/app/services/gemini.py` (170 lines)
- `backend/app/services/matching.py` (155 lines)
- `backend/app/services/notifications.py` (7 lines)
- `backend/app/services/storage.py` (72 lines)
- `backend/app/services/vision.py` (43 lines)
- `backend/migrations/env.py` (23 lines)
- `backend/migrations/versions/0001_initial_schema.py` (22 lines)
- `backend/migrations/versions/0002_revoked_tokens.py` (14 lines)
- `.github/workflows/verify.yml` (36 lines)
- `report/README.md` (5 lines)
- `report/SmartFind_Report.md` (213 lines)


## Final disposition

See `docs/verification/final-results.md` for executed evidence. 41 backend/migration tests and six isolated browser workflows pass. Confirmed defects fixed: own-report matching; low-relevance search; recovered/moderated semantic candidates; mixed-method PostgreSQL retrieval omission (lexical fallback); whole-report failure after saved report/photo failure; duplicate creates on lost responses; claim-review lock ordering; whitespace-only fields; cached reused visitor session; incorrect login errors; missing smart-search/assistant interface and evidence download control. Added nullable owner-scoped retry migration without rewriting existing data or embeddings.

Remaining incomplete work is explicitly tracked in `docs/FINAL_DELIVERY_CHECKLIST.md`. Important limitations: complete legacy/admin/notification translation, admin HttpOnly authentication, comprehensive mobile-camera/upload-progress/interruption recovery, live Gemini image inference, E5/OpenCLIP resource profiling/inference, all PostgreSQL races, shared rate limiting, operational-error dashboard, measured load tests, verified backup restore, and coordinated production rollout with legacy visitor-cookie transition. No claim of full submission readiness is made.
