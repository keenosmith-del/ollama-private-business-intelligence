# Current API contracts

All Node application endpoints are under `/api`; protected endpoints require `Authorization: Bearer <accessToken>`. Errors use `{ "error": { "code", "message" } }`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/bootstrap` | one-time bootstrap secret | Provision first organisation admin |
| POST | `/auth/login` | public, rate-limited | Issue a 30-minute access token and an HttpOnly refresh cookie |
| POST | `/auth/refresh` | refresh cookie | Rotate the 14-day refresh session and issue a new access token |
| POST | `/auth/logout` | refresh cookie | Revoke the current refresh session and clear its cookie |
| GET | `/auth/me` | authenticated | Return token principal |
| GET, POST | `/users` | admin | List and create organisation users |
| DELETE | `/users/:id` | admin | Disable an organisation user |
| GET | `/organisations/me` | authenticated | Read the signed-in user's organisation profile |
| PATCH | `/organisations/me` | admin | Update the organisation name |
| GET, DELETE | `/documents`, `/documents/:id` | admin/analyst read; admin delete | List, inspect metadata and delete documents |
| GET | `/analytics/revenue` | authenticated | Quarterly sales aggregation |
| GET | `/analytics/operations` | authenticated | Operational incident aggregation |
| GET | `/customers`, `/financials` | authenticated | Organisation-scoped business records |
| POST | `/search` | authenticated | Semantic evidence search |
| POST | `/sales/import` | admin/analyst | Validated, idempotent CSV sales import (`customer,date,amount`; optional `industry`) |
| POST | `/documents` | admin/analyst | Parse, chunk, embed and index one supported document |
| POST | `/analysis` | authenticated | Route question to fixed analytics and/or RAG |
| GET | `/models` | authenticated | Report AI runtime readiness/model availability |
| GET | `/audit` | admin | Read paginated organisation audit events |
| GET | `/health`, `/ready` | public | Liveness and dependency readiness |

The FastAPI runtime exposes `/health`, `/health/ready`, `/v1/documents/ingest`, `/v1/business-data/sales/import`, `/v1/search` and `/v1/analysis`. It requires `x-internal-token` plus gateway-supplied organisation/user IDs for data operations. FastAPI publishes interactive OpenAPI at `/docs` inside the Compose network.

The browser holds access tokens in memory and sends the refresh cookie with credentialed requests. Refresh tokens are random, stored as SHA-256 hashes, rotated on use, and scoped to an HttpOnly, SameSite=Strict cookie. Reuse of a revoked token invalidates its session family. Production cookies use the Secure attribute; production deployment still requires TLS.

The Node API runs checked-in SQL migrations at startup. Applied filenames and checksums are tracked in `schema_migrations`; modifying an already-applied migration stops startup, so schema changes should be added as a new numbered file.
