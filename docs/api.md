# API and workflow notes

Interactive OpenAPI documentation is exposed at `/docs` when FastAPI is running.

## Authentication

`POST /api/v1/auth/register` and `/login` return a bearer access token. The frontend stores the token in browser local storage and sends it as `Authorization: Bearer <token>`. The logout endpoint is stateless and instructs the client to discard its token. The token expiry is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.

## Listing privacy

Public listing responses intentionally omit `private_identifiers`. The owner and administrator can edit a listing; the public API only returns public image URLs. Claim evidence is written under the private upload directory and has no public URL.

## AI analysis

`GET /api/v1/ai/status` reports whether the Gemini SDK and API key are configured. `POST /ai/analyze` accepts a text query for attribute extraction. `POST /ai/description` returns a suggested title/description and explicitly requires student approval before applying it. Image uploads trigger image embeddings and Gemini analysis when available.

## Matching

`POST /api/v1/ai/match/{listing_id}` runs matching for a student's own listing (or an administrator). The engine enforces opposite statuses, excludes closed reports, stores candidate evidence and returns at most five candidates. `GET /api/v1/matches` returns only matches involving the authenticated student's reports, unless the caller is an administrator.

## Claims

`POST /api/v1/claims` accepts a found listing ID, optional match ID and private verification details. A student can view claim status but cannot read the verification details back from the API. Administrators can read the claim details and the found listing's private identifying details. The evidence upload endpoint stores files privately.

## Administration

Admin routes are role-protected. Claim review accepts `NEEDS_EVIDENCE`, `APPROVED` or `REJECTED`. Approval marks the found item and, when the claim includes a valid match belonging to the claimant, the linked lost item as recovered. The matching-results UI carries the match identifier into the claim flow. Rejections and evidence requests notify the claimant. Admin changes are written to the audit log.

## Search

`POST /api/v1/ai/search` retrieves actual stored reports. PostgreSQL deployments use pgvector cosine distance with the configured vector index; SQLite uses a bounded Python retrieval fallback. Search responses identify the embedding method and retrieval backend.


## Pre-submission duplicate warning

`POST /api/v1/ai/duplicates/check` compares a proposed report with existing same-status records before the new report is saved. The frontend displays a confirmation warning when candidates are returned. The operation is advisory only and does not create, delete or merge records. The post-submission `/ai/duplicates/{listing_id}` endpoint can be used to inspect possible duplicates for an existing report.


## Campus-zone administration

Administrators can list, create and update campus zones under `/api/v1/admin/zones`. Adjacency codes are validated against existing zones. Only administrators can change listing workflow state; a student cannot mark their own report as recovered through the listing update endpoint.
