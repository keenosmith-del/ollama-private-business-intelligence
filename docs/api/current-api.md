# Current API contracts

All Node application endpoints are under `/api`; protected endpoints require `Authorization: Bearer <accessToken>`. Errors use `{ "error": { "code", "message" } }`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/bootstrap` | one-time bootstrap secret | Provision first organisation admin |
| POST | `/auth/login` | public, rate-limited | Issue 30-minute access token |
| GET | `/auth/me` | authenticated | Return token principal |
| GET, POST | `/users` | admin | List and create organisation users |
| DELETE | `/users/:id` | admin | Disable an organisation user |
| GET, DELETE | `/documents`, `/documents/:id` | admin/analyst read; admin delete | List, inspect metadata and delete documents |
| GET | `/analytics/revenue` | authenticated | Quarterly sales aggregation |
| GET | `/analytics/operations` | authenticated | Operational incident aggregation |
| GET | `/customers`, `/financials` | authenticated | Organisation-scoped business records |
| POST | `/search` | authenticated | Semantic evidence search |
| POST | `/documents` | admin/analyst | Parse, chunk, embed and index one supported document |
| POST | `/analysis` | authenticated | Route question to fixed analytics and/or RAG |
| GET | `/models` | authenticated | Report AI runtime readiness/model availability |
| GET | `/audit` | admin | Read paginated organisation audit events |
| GET | `/health`, `/ready` | public | Liveness and dependency readiness |

The FastAPI runtime exposes `/health`, `/health/ready`, and versioned `/v1/documents/ingest` and `/v1/analysis`. It requires `x-internal-token` plus gateway-supplied organisation/user IDs for data operations. FastAPI publishes interactive OpenAPI at `/docs` inside the Compose network.
