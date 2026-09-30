# Project status — 2026-09-30

## Checkpoint 1: foundation and first backend slice

Implemented: TypeScript Express API; password-hashed one-time admin bootstrap and JWT login; role middleware and active-account token checks; admin user list/create/disable; org-scoped document inventory/detail/delete; paginated audit reads; semantic search; sales/customer/expense/incident aggregation; validated and idempotent CSV sales import; multipart validation; FastAPI extraction for PDF/DOCX/TXT/CSV/XLSX; chunking and content-hash deduplication; Ollama embeddings and grounded chat; vector retrieval; fixed parameterized query templates; structured evidence response; pgvector schema; Compose services; frontend Vite/React routing and typed API shell; API and privacy docs.

Verified integration paths: admin bootstrap and login to the protected API; organisation-scoped Q1/Q2 SQL revenue aggregation; three-row CSV sales import and repeat-import deduplication; Q2 comparison remains Q1-to-Q2 after Q3 records exist; TXT report upload, Ollama embedding, pgvector indexing, hybrid analysis with SQL and document evidence; knowledge-only policy retrieval; fixed analytics for customer movement, expense categories and operational incidents; duplicate document upload returns the prior indexed document; admin user creation, viewer permission denial and immediate disabled-account rejection; semantic search; admin audit read; persisted analysis result and audit event. Both configured Ollama models were pulled into local volumes.

## Checkpoint 4: API-backed frontend and continuous integration

Implemented: signed-in application shell with in-memory bearer-token handling; role-aware navigation for document access; responsive overview using live revenue, customer, and operations endpoints; evidence-first AI Analyst with analysis type, findings, metrics, sources and warnings; document upload/index and library views; structured revenue/customer/cost analytics; loading, error, and empty states; local-only typography and assets; CI workflow for Node tests/type checks/build, Python Ruff/pytest/compile checks, and Compose validation.

Verified: Node/Python checks and production builds passed; Ruff focused checks passed; Compose rebuilt all services and started the frontend; local browser rendered the sign-in view. Authenticated frontend clicks were not automated because entering account credentials through the browser requires user handoff. The existing API E2E smoke remains the verified authenticated integration path.

Still not complete: organisation administration; document-level ACLs; full audit coverage; retryable ingestion status; persistent observability metrics; broader negative-path and cross-tenant tests; admin/audit frontend surfaces; frontend automated browser tests; Tailwind utility styling; production TLS/secrets/network hardening and deployment guidance.

## Checkpoint 5: rotating refresh sessions

Implemented: HttpOnly SameSite=Strict refresh cookie; random refresh secrets stored only as SHA-256 hashes; 14-day session lifetime; rotation on use; replay detection that revokes the token family; logout revocation; disabled-account rejection on refresh; refresh/logout audit events; credentialed API client with single-flight refresh and memory-only access token; startup session restore after page reload; additive migration `004_refresh_sessions.sql`.

Verification: TypeScript and frontend type checks passed; Python suite (7 tests), focused Ruff checks, compilation and Compose config passed; migration applied to the local database. The rebuilt Compose stack passed `scripts/e2e-smoke.py`, including a rotated refresh cookie, grounded search and analysis, role restrictions, and logout revocation.

## Checkpoint 6: versioned database migrations

Implemented: backend startup now runs sorted SQL migrations transactionally under a PostgreSQL advisory lock, records SHA-256 checksums in `schema_migrations`, and rejects edits to already-applied migrations. Existing databases are adopted through per-migration schema sentinels. Compose no longer relies on PostgreSQL's one-time initialization directory; the backend image includes the migration files.

Verification: backend image rebuilt; startup adopted the existing database and recorded migrations 001–004; `/ready` returned `ready`; the full local smoke workflow passed again. The project database and sample business records remained intact.

## Checkpoint 7: customer profitability analytics

Implemented: migration `005_customer_cost_attribution.sql`; fictional per-customer direct costs in the sample seed; deterministic customer gross-profit ranking and Q1-to-Q2 profitability trend queries using separate aggregate CTEs; evidence sources and structured metrics; updated end-to-end assertions.

Verification: Node and Python checks passed; the migration and seed were applied to the local database; `/ready` returned `ready`; the full Ollama-backed workflow passed, including least-profitable customer ranking and customer profit trend.

## Verification

Environment observed: Node 24.14.1, npm 11.11.0, Python 3.14.7, Docker 29.4.2, Git 2.50.1. npm dependencies and a local Python venv were installed. Verified: Node security unit tests; Python chunking, intent, vector, TXT and CSV parser tests; Ruff E4/E9/F checks; Node TypeScript build; Vite production build; Python compile; Compose config validation; Git whitespace check.

Verified against the local Docker stack: migrations, sample seed records, both Ollama models, pgvector inserts and nearest-neighbour retrieval, idempotent CSV import, protected analysis request/result persistence, audit reads, RBAC and disabled-user rejection, and `scripts/e2e-smoke.py` across login, structured import, document upload, revenue, search, hybrid analysis, knowledge retrieval and user lifecycle. The running containers are left up for review. Broader isolation/security/performance testing remains.

## Decisions made

- PostgreSQL + pgvector keeps structured facts and document vectors in one access-controlled storage boundary.
- Node is the API/auth gateway; Python isolates document/AI dependencies and remains independently testable.
- The first analytics path is fixed SQL, never model-generated SQL.
- The UI remains a route shell until backend workflows are integrated, per requested build order.
