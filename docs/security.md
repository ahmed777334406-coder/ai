# Security and privacy notes

- Passwords are hashed using PBKDF2-HMAC-SHA256 with a random per-password salt and a high iteration count.
- Access tokens are HMAC-SHA256 signed, expire, and are verified server-side. Replace the development secret before production.
- The production startup guard rejects the development JWT secret and default admin password.
- Roles are enforced on admin routes and owner-only listing operations.
- Public listing serializers omit private identifying details and claim verification answers.
- Claim evidence is stored in a private directory that is not mounted as public static media.
- Uploaded images are checked by decoded format and matching filename extension, constrained by byte size and a 25-megapixel limit, assigned server-generated filenames, EXIF-transposed and re-encoded to strip metadata.
- Gemini API keys remain on the backend and are never returned to the frontend.
- Student descriptions and images are treated as untrusted data in Gemini prompts.
- Similarity scores are not probabilities and cannot auto-approve claims.
- Rate limiting is implemented in-process for authentication and general API requests. For multi-worker or public production deployments, replace it with a shared Redis-backed limiter and add operational monitoring.
- This academic project has not undergone an independent penetration test or privacy impact assessment. Do not upload real identity cards, phone numbers, addresses or sensitive personal details to the demo.

## Final audit hardening and limits

Owner-scoped unique retry keys prevent duplicate report creation after a lost response. Input strings are trimmed before required-length validation. Claim creation and review lock the listing first; reviews of separate claims for one item use the same lock order. PostgreSQL concurrent execution still requires dedicated race tests. AI requests have a separate in-process 20/minute/IP quota; Gemini uses a 15-second per-request SDK timeout with two attempts. Match explanations can cause several sequential provider calls, so aggregate request latency remains a concern.

Admin tokens moved from localStorage to sessionStorage; old persisted credentials are not reused. XSS can still read sessionStorage. Prefer a separately designed HttpOnly admin session with CSRF checks for a later release. Private evidence downloads enforce containment, are audited, and use no-store. Anonymous identity cannot safely be recovered after cookie loss without a deliberately designed recovery credential; never reconstruct identity using public information.

Backup procedure: schedule encrypted PostgreSQL logical backups and snapshot/copy the complete persistent upload volume (public and private) under restricted access. Record backup timestamps together. Restore both into an isolated environment, run migrations, compare row counts and image hashes, test authorized evidence download, and only then approve a recovery procedure. No production restore was attempted during this audit.
