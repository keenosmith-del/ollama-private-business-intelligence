# Project status — 2026-09-30

## Checkpoint 1: foundation and first backend slice

Implemented: TypeScript Express API; password-hashed one-time admin bootstrap and JWT login; role middleware and active-account token checks; admin user list/create/disable; org-scoped document inventory/detail/delete; paginated audit reads; semantic search; sales/customer/expense/incident aggregation; multipart validation; FastAPI extraction for PDF/DOCX/TXT/CSV/XLSX; chunking and content-hash deduplication; Ollama embeddings and grounded chat; vector retrieval; fixed parameterized query templates; structured evidence response; pgvector schema; Compose services; frontend Vite/React routing and typed API shell; API and privacy docs.

Verified integration paths: admin bootstrap and login to the protected API; organisation-scoped Q1/Q2 SQL revenue aggregation; TXT report upload, Ollama embedding, pgvector indexing, hybrid Q2 analysis with SQL and document evidence; knowledge-only policy retrieval; fixed analytics for Q1/Q2 customer movement, expense categories and operational incidents; duplicate document upload returns the prior indexed document; admin user creation, viewer permission denial and immediate disabled-account rejection; semantic search; admin audit read; persisted analysis result and audit event. Both configured Ollama models were pulled into local volumes.

Not yet complete: refresh-token lifecycle and logout; organisation administration; document-level ACLs; migration runner/version tracking; wider analytical question support (including profitability); complete audit event coverage; retryable ingestion state; observability metrics; more negative-path and cross-tenant integration coverage; CI; frontend API client integration and product UI; TLS/secrets/network hardening.

## Verification

Environment observed: Node 24.14.1, npm 11.11.0, Python 3.14.7, Docker 29.4.2, Git 2.50.1. npm dependencies and a local Python venv were installed. Verified: Node security unit tests; Python chunking, routing, vector-shape and TXT parsing tests; Node TypeScript build; Vite production build; Python compile; Compose config validation; Git whitespace check.

Verified against the local Docker stack: migrations, sample seed records, both Ollama models, pgvector inserts and nearest-neighbour retrieval, protected analysis request/result persistence, audit reads, RBAC and disabled-user rejection, and `scripts/e2e-smoke.py` across login, upload, revenue, search, hybrid analysis, knowledge retrieval and user lifecycle. The running containers are left up for review. Broader isolation/security/performance testing remains.

## Decisions made

- PostgreSQL + pgvector keeps structured facts and document vectors in one access-controlled storage boundary.
- Node is the API/auth gateway; Python isolates document/AI dependencies and remains independently testable.
- The first analytics path is fixed SQL, never model-generated SQL.
- The UI remains a route shell until backend workflows are integrated, per requested build order.
