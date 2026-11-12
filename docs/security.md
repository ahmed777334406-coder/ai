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
