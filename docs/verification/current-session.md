# SmartFind verification — 12 November 2026

## Deployed applications

- GitHub: https://github.com/ahmed777334406-coder/ai
- Vercel production: https://beihang-smartfind.vercel.app
- Railway API: https://smartfind-api-production.up.railway.app
- API documentation: https://smartfind-api-production.up.railway.app/docs
- Current deployed application code: `331c1d5`; subsequent commits add tests, screenshots and documentation.
- SmartFind Railway project: `f0e72604-ab53-4653-b5c9-c9a96298d78d`. Backend and PostgreSQL are independent of Football Coach. No Football Coach resources were changed.

## Executed checks

| Check | Actual result |
|---|---|
| Expanded backend suite, isolated SQLite | 27 passed |
| GitHub Actions PostgreSQL/pgvector migrations and initial suite | 24 passed; backend job succeeded in run 43164251804 |
| GitHub frontend job | Lint, typecheck and build succeeded in run 43164251804 |
| Local final frontend lint/typecheck/build | Passed on Next.js 16.4.6 / React 19.3.1 |
| Deployed Playwright tests | 4 passed in 30.2 seconds |
| Python dependency audit | No known vulnerabilities in audited environment |
| npm dependency audit | 0 vulnerabilities after scoped minimatch override |
| Public API readiness | HTTP 200, `database: postgresql` |
| Live API authorization, pgvector multilingual search and logout | Passed |
| Academic report | 5,147 counted words; regenerated Markdown, DOCX and PDF |
| Synthetic evaluation rerun | Completed on local fictional seed; only rule/hash and HSV methods observed |

The four browser tests exercised homepage rendering, language switching, desktop and 390-pixel mobile overflow checks, mobile reporting, protected-route redirects, student registration, persisted profile changes, failed login feedback, two independent students reporting LOST/FOUND items with real image uploads, fallback-labeled matching, claim submission, private administrator review, approval, both reports becoming RECOVERED, and notifications to both students. Screenshots are in `docs/screenshots/`.

The original workflow test initially used the wrong accessible labels and was interrupted twice before selector corrections. Those attempts are not counted as passes. The final complete run passed all four tests. A first public browser attempt hit the cloud proxy's certificate-trust mismatch; the successful test run explicitly trusted the environment proxy's known public-key fingerprint without a global certificate-validation bypass. No secrets, browser session state or private credential files are committed.

Backend regression tests cover rejected claims, authorization, claim finalization, workflow-state protection, upload validation, duplicate warnings, multilingual retrieval, missing-signal normalization, profile updates, rate limiting, readiness failures and token revocation.

## AI limits

Gemini SDK is installed, but `GEMINI_API_KEY` is absent. No successful Gemini call is claimed. E5 and OpenCLIP are disabled (`ENABLE_LOCAL_MODELS=false`) in the deployed image. Text uses `bilingual_rule_hash_fallback`, images use `opencv_hsv_histogram_fallback`, and generative analysis uses a named rule fallback. Results are ranking similarities, not ownership probabilities. Synthetic evaluation metrics are reproducible demonstrations, not real-world model performance.

## Administrator and privacy

The explicitly approved administrator is `admin@example.edu`; the generated password is stored privately in SmartFind Railway's `ADMIN_PASSWORD` variable. It is not a known demo password. Current report files have blank student-name and student-ID fields for public sharing. The initial source-import commit included the supplied report's author metadata; removing that historical metadata would require a separately authorized history rewrite. Existing Git history has been preserved.

## Remaining operational limitations

Some secondary/admin UI copy remains English. University identity verification, password-reset email and external notification channels are not implemented. Rate limiting is in-process and single-instance; matching reranks candidates in Python and synchronous inference can increase latency. Operator-managed backups, monitoring and larger-scale capacity testing remain necessary before institutional production use. The local Docker PostgreSQL test was interrupted by disk exhaustion; the PostgreSQL evidence above comes from successful GitHub CI and the actual Railway deployment, not that local attempt.
