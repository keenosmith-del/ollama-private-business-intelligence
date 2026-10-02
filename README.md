# Ollama Private Business Intelligence Platform

A local-first BI system for sensitive organisational data. Business calculations use parameterized PostgreSQL operations; document questions use pgvector retrieval and locally hosted Ollama models. Node/Express owns user-facing APIs and access control. FastAPI owns extraction, embeddings, retrieval and grounded generation.

## Current checkpoint

This is an integrated local BI demonstrator. See [COMPLETION_AUDIT.md](docs/COMPLETION_AUDIT.md) for the executed completion audit, exact startup/demo commands, numerical evidence and known limits, and [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for the current checkpoint.

## Start locally

1. Run `python3 scripts/setup-local.py` to create `.env` with unique secrets, or preserve and review your existing `.env`. The local demo password is stored privately in `PBI_E2E_PASSWORD`.
2. Start dependencies and services with `docker compose up -d --build` (Docker Desktop must be running). Services bind to localhost; the Docker database defaults to host port 5433, configurable with `POSTGRES_PORT`.
3. Pull models into the local Ollama volume: `docker compose exec ollama ollama pull qwen2.5:1.5b` and `docker compose exec ollama ollama pull nomic-embed-text`.
4. Run `python3 scripts/bootstrap-local.py` to wait for readiness and authenticate/bootstrap the local demo admin. Alternatively create the first admin using `POST /api/auth/bootstrap` with header `x-bootstrap-token` and JSON `{ "organisation": "Northstar Components", "email": "admin@example.test", "password": "use-a-long-unique-password" }`. Bootstrap closes once the first user exists.
5. Open `http://localhost:5173` and sign in with the admin account. FastAPI publishes OpenAPI and Swagger docs at `/docs` on the private Compose network; the AI runtime has no host-published port.

The sample SQL can be loaded with `docker compose exec -T postgres psql -U pbi -d pbi < database/seeds/001_demo.sql` after the organisation exists. It uses fictional customers, quarterly sales, costs and incidents. Import `data/sample/sales-import.csv` through `POST /api/sales/import` for the validated, idempotent structured CSV path. Upload the sample TXT files through `POST /api/documents` to exercise RAG and hybrid analysis.

The frontend provides live business overview, AI Analyst with saved history, document upload/library/search and retry status, CSV sales/customer and expense imports, structured analytics, and admin/audit screens. Viewers can use analysis and analytics; document-library routes are restricted to admins and analysts. Admins can scope restricted documents to selected users or roles.

The demonstration includes customer-attributed delivery costs, so the analyst can answer deterministic questions such as “Which customers are least profitable?” and “Which customers are becoming less profitable?” from revenue less recorded direct costs.

Run `python3 scripts/e2e-smoke.py` with Compose running to execute auth, idempotent CSV import, upload, deterministic revenue, semantic search, hybrid analysis, policy retrieval, audit and user-role checks. It reads `PBI_E2E_PASSWORD` and `BOOTSTRAP_TOKEN` from the local `.env` (or accepts `PBI_E2E_PASSWORD` from the process environment). On first run it uses the bootstrap token to create the local admin.

## API surface (current)

- `GET /health`, `GET /ready`
- `POST /api/auth/bootstrap`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/analytics/revenue`
- `POST /api/documents` (multipart field `file`)
- `POST /api/analysis` (`{ "question": "..." }`)
- `GET /api/models`

Normal API calls use `Authorization: Bearer <accessToken>`. Access tokens are held in frontend memory; an HttpOnly cookie supports refresh-token rotation and logout. The runtime is intended to be private to the Compose network; it verifies a shared internal service token and trusts the authenticated Node gateway's organisation/user/role headers and must not be exposed publicly.

Analyses present deterministic SQL facts and exact source excerpts. Real Ollama inference selects relevant evidence IDs; unrestricted model prose is not accepted as a financial figure or cause. A management explanation does not establish causation or a causal loss amount. New uploads retain their bytes locally for manual retry. Profit covers recorded entries; customer profit excludes shared overhead.

Run `npm run test:browser` after `npx playwright install chromium` for the real frontend journeys. The completion report lists the fresh-bootstrap, business-scenario, model-failure and isolation audit commands. Run live suites sequentially to respect the API rate limit.

## Privacy boundary

In the default Compose setup, documents, extracted text, embeddings, database queries and inference stay in the local Docker services and volumes. No external LLM API is used. Docker image/model downloads do require network access during setup. Do not claim an air-gapped installation until images and model artifacts have been provisioned and outbound network access is disabled. Production deployment still needs secrets management, TLS, network policy and a dedicated least-privilege database role.

## Development

Node requires the workspace packages; Python dependencies are pinned in `ai-runtime/requirements.txt`. PostgreSQL schema is explicit in `database/migrations`. Avoid putting real customer data in seeds, logs, prompts or issues.
