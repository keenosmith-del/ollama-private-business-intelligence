# Current API contracts

All Node application endpoints are under `/api`; protected endpoints require `Authorization: Bearer <accessToken>`. Errors use `{ "error": { "code", "message" } }`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/bootstrap` | one-time bootstrap secret | Provision first organisation admin |
| POST | `/auth/login` | public, rate-limited | Issue 30-minute access token |
| GET | `/auth/me` | authenticated | Return token principal |
| GET | `/analytics/revenue` | authenticated | Quarterly sales aggregation |
| POST | `/documents` | admin/analyst | Parse, chunk, embed and index one supported document |
| POST | `/analysis` | authenticated | Route question to fixed analytics and/or RAG |
| GET | `/models` | authenticated | Report AI runtime readiness/model availability |
| GET | `/health`, `/ready` | public | Liveness and dependency readiness |

The FastAPI runtime exposes `/health`, `/health/ready`, and versioned `/v1/documents/ingest` and `/v1/analysis`. It requires `x-internal-token` plus gateway-supplied organisation/user IDs for data operations. FastAPI publishes interactive OpenAPI at `/docs` inside the Compose network.
