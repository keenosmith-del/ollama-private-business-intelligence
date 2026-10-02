# Completion audit — 2 October 2026

## Objective and scope

Audit and complete the existing local private BI application: React → Node/Express → Python/FastAPI → PostgreSQL/pgvector and Ollama. The implementation was inspected directly, including README/status/architecture/security/API docs, every migration, services/routes, frontend routes/API client, tests, seed data, CI and Dockerfiles/Compose. No replacement architecture, external AI provider, frontend redesign or database reset was introduced. Existing volumes and business records were retained. The existing host PostgreSQL service was left untouched.

## Findings and resolutions

| Area | Observed implementation before audit | Resolution |
| --- | --- | --- |
| Authentication | Bootstrap, login, rotating refresh and disabled-account checks worked; bearer tokens survived logout; bootstrap had a concurrent creation race | Serialize bootstrap; tie access tokens to a live refresh family; logout/replay revoke bearer access; load current role from the database |
| Organisation/users | Scoped organisation profile, rename, team creation/disable and role gates present | Retained; verify administrator and viewer workflows through APIs and browser |
| Document permissions | Organisation/restricted ACL predicates and user/role grants present | Retained; verify isolation and revocation; connect existing visibility API to UI; block duplicate-upload metadata disclosure to another uploader |
| Ingestion | Supported five formats, but processing/failed rows disappeared with a rolled-back transaction | Persist status, raw bytes, error code, attempt count and timestamps; atomic chunk writes; retry endpoint/UI; nonblocking duplicate-processing lock; failed/interrupted upload recovery |
| Extraction | DOCX paragraphs omitted tables; ragged CSV could crash | Include DOCX tables; handle CSV extra columns; verify PDF/DOCX/CSV/XLSX/TXT using real indexing |
| Business imports | Validated/idempotent sales/customer CSV API lacked UI; no expense import | Connect sales import; add transactional expense CSV import with optional existing-customer attribution and validation; idempotency locks |
| Financial calculations | Fixed SQL existed; Q1/Q2 comparison could select the wrong target; trends fixed to 2026; company profit missing | Explicit quarter/year selection and adjacent comparison; separate customer aggregates; recorded company profit; zero/missing period handling; three-category cost exposure |
| Grounding | Real Ollama prose invented an additional cause and incident-linked expense figures during this audit | Constrain real inference to evidence-ID selection. Render deterministic facts and exact stored document excerpts. No unrestricted generated cause or financial figure is accepted |
| Saved analyses | Results/audit persisted but no authenticated inspection API/UI | List/detail history; retain question privately; recheck every source ACL on every read, including deleted sources; connect history to analyst UI |
| Frontend | Live main routes existed; readiness indicator was hard-coded | Actual readiness polling; session-expiry transition; profit/trend metric rendering; source excerpts; search, import, retry, visibility and history integration using existing styling |
| Startup/privacy | Docker stopped; localhost:5432 already owned by host PostgreSQL; service ports published on all interfaces | Start existing Docker installation; localhost-only bindings; configurable Docker PostgreSQL host port defaults to 5433; exact-origin browser CORS; secure setup/bootstrap helpers |
| Test coverage | 3 Node and 7 Python tests; API smoke present; no automated authenticated browser journey | Expand Python coverage; add disposable fresh-bootstrap audit, synthetic business/security/format audit, real missing-model audit, two Playwright journeys |

New migrations are additive: `007_ingestion_recovery.sql`, `008_analysis_questions.sql`. Applied earlier migration files were not changed. Old access tokens without a session-family claim are rejected; refresh or sign-in issues a replacement. Legacy documents already indexed remain usable; legacy documents without retained bytes require re-upload for retry. Legacy saved analyses may have no original question.

## Executed verification

Final results are recorded below after the final sequential run. Earlier checkpoints are historical claims, not substitutes for these executions.

| Check | Final result |
| --- | --- |
| `npm test` | PASS: 3 Node tests and frontend type check |
| `npm run build` | PASS: backend TypeScript and React/Vite production build |
| `.venv/bin/python -m pytest -q ai-runtime/tests` | PASS: 13 tests; dependency deprecation warnings only |
| Ruff E4/E9/F and Python compileall | PASS |
| `docker compose config --quiet`, rebuilt Compose images | PASS |
| `npm audit --omit=dev` | PASS: zero reported production dependency vulnerabilities at audit time |
| Fresh migrations / concurrent bootstrap | PASS: all 8 migrations; invalid secret rejected; simultaneous attempts produce exactly one 201 and one 409; only one user created; disposable database removed |
| Comprehensive synthetic API/SQL/vector/Ollama audit | PASS: 82 assertions, 11 real-inference business questions; SQL/value checks, formats, ACL/isolation, retries, concurrency, history, disable/logout/replay; 84.8 seconds |
| Existing API smoke, final model configuration | PASS: auth/refresh, organisation, document user/role ACLs, revenue/profit/trends, search, hybrid/policy evidence, audit, disable and logout; real Ollama |
| Real missing-model and recovery audit | PASS: 6 assertions against real Ollama with intentionally absent generation/embedding models, internal-auth denial and recovered real embeddings |
| Playwright against actual frontend/backend | PASS: 2 Chromium tests in 26.9 seconds; login/restore, sales and expense import, upload/index, semantic search, visibility PATCH, real inference/excerpts, saved history, administration/audit, viewer creation/restrictions, disable/session restoration denial, logout |
| `git diff --check` | PASS |
| Local setup/bootstrap helpers | PASS: existing `.env` preserved; existing administrator verified; no credentials overwritten |
| PostgreSQL extension, model inventory, final API readiness | PASS: all 5 services running; `/ready` HTTP 200; PostgreSQL healthy; pgvector 0.8.6, pgcrypto 1.3; migrations 001–008; qwen2.5:1.5b (65ec06548149), nomic-embed-text:latest (0a109f422b47) |

Failures encountered and addressed: Docker initially unavailable; system Python lacked pytest (used existing project venv); sandbox initially blocked localhost/npm access (reran with authorized access); Compose localhost:5432 conflicted with a host database (moved only the project's published port); unrestricted small-model prose failed grounding inspection (replaced with constrained inference and exact excerpts); overlapping localhost suites hit rate limiting (structured rate-limit errors, sequential final execution). These initial failures are not described as passes. No live final test uses a mocked AI response. The Python negative-path unit test intentionally supplies invalid model prose to verify rejection; real integration tests use actual Ollama.

## Actual user journey and numerical evidence

1. Provision an administrator once; repeat or concurrent bootstrap cannot create another initial user. Authenticate, rotate refresh and restore the session after browser reload.
2. Read/rename the organisation; create a viewer through the frontend; viewer navigation and API gates restrict administration/uploads; disabling the account rejects active access and subsequent session restoration.
3. Import labelled synthetic sales/customers and expenses. Repeat imports do not double-count. Invalid rows and unknown expense customers leave no partial records.
4. Upload five real file formats. Extracted chunks receive actual `nomic-embed-text` embeddings stored as vector(768). Parse/empty/model failures remain inspectable; retry can index retained valid bytes. Concurrent processing returns a retryable conflict instead of blocking the runtime.
5. Search evidence with organisation and document ACLs. Grant/revoke both role and user access. Another organisation cannot see structured records, document metadata, vector hits or saved answers. Revocation also blocks stored source excerpts.
6. Ask the nine requested business questions plus customer-trend and overall-profit questions. Use actual `qwen2.5:1.5b` inference. Financial facts come from fixed SQL and Decimal calculations. Document answers quote stored evidence, with filenames/pages; management statements are not treated as proven causes.
7. Inspect the saved question, metrics, warnings and evidence through analyst history. Confirm corresponding completed-analysis audit rows. Log out; neither retained bearer credentials nor refresh cookies restore access. Refresh replay also revokes the whole family.

The separate audit organisation is explicitly named `SYNTHETIC COMPLETION AUDIT ...`; fixtures are generated by `scripts/completion-audit.py`. Its business-question values, before the deliberate Q3 selection test, are:

| Question | Verified financial facts / evidence boundary |
| --- | --- |
| Revenue in Q2 | 120,000 in Q2 2027 |
| Compare Q1 and Q2 | 200,000 → 120,000; -80,000; -40.00% |
| Highest revenue customers | Synthetic Alpha 190,000; Synthetic Beta 130,000 across recorded Q1/Q2 |
| Least profitable customers | Synthetic Beta 45,000 recorded gross profit; Synthetic Alpha 110,000; shared overhead excluded |
| Largest expenses | Delivery 165,000; Logistics 30,000; Returns 12,000 across recorded Q1/Q2 |
| Three largest areas of loss/cost exposure | Those three expense totals are cost exposure, not independently established losses |
| Why Q2 revenue declined | Financial decline above; exact management excerpts mention deferred shipments/supplier delays and disrupted order processing; no additional cause or attributed loss amount |
| Internal expense policy | Exact synthetic policy evidence: receipts required; manager approval for travel above 500 |
| Operational contributions | One structured supplier-delay incident; document statements describe outage/deferred shipments; no incident-linked financial amount inferred |
| Customer profit trend | Synthetic Beta 50,000 → -5,000 (-55,000); Alpha 80,000 → 30,000 (-50,000), Q1 to Q2 2027 |
| Company Q2 recorded profit | Revenue 120,000 - recorded expenses 137,000 = -17,000 |

Independent PostgreSQL queries check the revenue, percentage, customer ranking, customer profit, expense and overall-profit results. Adding Q3 sales does not change Q1/Q2 selection. A requested empty Q4 2028 returns zero **recorded** sales with a missing-record warning, not another quarter's sales. [audit-results.json](audit-results.json) stores the final synthetic questions/results, model/inference flags and organisation identifiers; it contains no credentials or real customer data.

The existing Northstar seed/smoke uses different fictional 2026 values: Q1 212,000 and Q2 127,000, a -40.09% movement. Do not confuse those values with the isolated audit fixture.

## Exact local startup

Run from the existing project directory. Docker Desktop must be running. Preserve an existing `.env`; the helper creates unique local secrets only when the file is absent.

```sh
cd "/Users/keenosmith/Ollama/Project 1/ollama-private-business-intelligence"
python3 scripts/setup-local.py
docker compose up -d --build
docker compose exec ollama ollama pull qwen2.5:1.5b
docker compose exec ollama ollama pull nomic-embed-text
python3 scripts/bootstrap-local.py
curl --fail http://localhost:3000/ready
```

Open `http://localhost:5173`. Default demo email: `admin@example.test`; password: the private value of `PBI_E2E_PASSWORD` in `.env`. For an existing administrator with a different email/password, use `PBI_E2E_EMAIL`/`PBI_E2E_PASSWORD` process variables; existing credentials are never overwritten. Configure model names in `.env` if using different supported local artifacts (embedding output must remain 768-dimensional). PostgreSQL is available on localhost `${POSTGRES_PORT:-5433}`; services still use `postgres:5432` internally. API: localhost:3000, frontend: localhost:5173, Ollama: localhost:11434. The runtime is internal-only.

Fresh demo database only, after bootstrap, load the existing fictional seed:

```sh
docker compose exec -T postgres psql -U pbi -d pbi < database/seeds/001_demo.sql
python3 scripts/e2e-smoke.py
```

The seed targets the first organisation and uses fixed synthetic IDs. It is not a production-data import procedure. For the comprehensive audit, use isolated synthetic organisations instead of adding the seed to real business accounts.

Developer/test environment and exact commands:

```sh
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r ai-runtime/requirements.txt ruff==0.16.9
npx playwright install chromium
npm test
npm run build
.venv/bin/python -m pytest -q ai-runtime/tests
.venv/bin/ruff check --select E4,E9,F ai-runtime/app ai-runtime/tests scripts
.venv/bin/python -m compileall -q ai-runtime/app ai-runtime/tests scripts
docker compose config --quiet
node scripts/bootstrap-audit.mjs
.venv/bin/python scripts/completion-audit.py
.venv/bin/python scripts/model-failure-audit.py
python3 scripts/e2e-smoke.py
npm run test:browser
git diff --check
```

Run live suites sequentially. A rapid repetition may need a minute between suites due to the API's 120 requests/minute localhost limit. The comprehensive audit adds labelled synthetic organisations/users/records, leaves them inspectable, and rewrites only its synthetic results report. Its passwords are random and not logged. The bootstrap audit creates/removes only its own disposable database. The model-failure audit uses a second local runtime on port 8001 and does not stop the shared Ollama service. The bootstrap audit briefly uses port 3001.

## Exact demonstration steps

1. Sign in; reload the page to demonstrate restoration; inspect live overview and readiness.
2. Administration: inspect organisation/team/audit. Create a synthetic viewer (12+ character password). Verify its restricted navigation in another browser context.
3. Analytics: import `data/sample/sales-import.csv` into the synthetic demo organisation; repeat to show deduplication. To import expenses, choose Expenses and use CSV `category,date,amount` with optional `customer,description` (customers must already exist).
4. Documents: upload `data/sample/management-report-q2.txt` and `data/sample/refund-policy.txt`; confirm ready/chunks. Search `refunds within 30 days`. Use Manage access → Document visibility to restrict a document, then grant/revoke a user or role.
5. For the internal-expense-policy scenario, upload a clearly labelled synthetic TXT policy stating that receipts are required and travel above 500 requires manager approval. Use PDF/DOCX/XLSX/CSV variants via `scripts/completion-audit.py` for repeatable format verification.
6. AI Analyst: ask the nine listed business questions. Check metrics, exact evidence, source labels and warnings. For the original seed, add `2026` to quarter questions to make the intended year explicit. Ask `Which customers are becoming less profitable? Compare Q1 and Q2 2026.` and `What was our profitability in Q2 2026?`.
7. Click Saved analyses to inspect a persisted original question and result. Revoke source access and verify a saved answer containing that source becomes unavailable to the revoked user.
8. Upload a malformed synthetic PDF to show failed status/error. Retry shows a new attempt; replacing malformed bytes requires a new upload. For missing-model recovery, run the model-failure audit.
9. Disable the synthetic viewer and reload its browser. Sign out the administrator and reload; the application stays at sign-in.

## Limits, blockers and redesign readiness

No remaining blocker to the verified local demonstration journey. The backend is ready for a separate frontend redesign: API integrations, access controls, ingestion recovery, deterministic calculations, evidence, persistence and real local inference have been exercised through the running application. Redesign should preserve these contracts and browser tests. No production-readiness claim is made.

Deliberate limits: fixed analytics intents/templates rather than arbitrary generated SQL; login requires an unambiguous active email across the local installation (ambiguous matches fail closed); one nominal currency in financial data (UI displays ZAR; multi-currency/FX conversion is not implemented); profit covers recorded revenue/costs rather than complete accounting/tax profit; customer profit excludes unattributed shared overhead. DOCX/PDF extraction does not perform OCR on scanned images. XLSX extraction reads cached formula values; it does not calculate formulas. Office documents are evidence uploads; structured financial imports are CSV. Empty/unsupported/unparseable files fail visibly.

Ingestion is synchronous with persisted status and manual retry, not a background queue. After an interrupted process, status can remain processing until manually retried. New upload bytes and questions are private local database data; retention policy/backups/encryption must be managed by the operator. Saved answers cannot erase evidence a user already read before revocation. Historical analyses created before grounding hardening are preserved, not retrospectively reverified; regenerate them to obtain the current exact-evidence contract. Exact excerpts may include neighbouring contextual text; retrieval ranking and small-model evidence selection remain imperfect. Invalid inference selection is reported and cannot inject generated facts. Locally hosted inference is intentionally constrained to prevent the hallucinations observed during this audit.

This is a verified local demonstrator, not a production hardening or performance certification. Dedicated least-privilege database roles, TLS, encrypted backups, malware scanning, durable background job recovery, immutable audit retention, load/performance tests, and offline provisioning remain deployment considerations. Public deployment was not tested. No frontend visual redesign was performed; `frontend/src/style.css` is unchanged. The frontend is still served by Vite in Compose. Container base images/Ollama tag are not digest-pinned, so downloads can change upstream even though application migrations and Node dependencies are versioned.
