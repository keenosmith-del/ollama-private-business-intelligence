# Initial security model

- Passwords use bcrypt hashing. Access tokens expire after 30 minutes and carry a user, organisation and role claim.
- Admin bootstrap requires a separate environment secret and is disabled after the first user exists.
- Express protects user-facing routes with authentication, role checks, request validation, upload size/type limits, Helmet headers and API rate limiting.
- Express forwards organisation scope to the private AI runtime using a shared internal token. The runtime service has no published host port in Compose.
- Every current analytics and retrieval query includes an organisation filter. Model-generated SQL is not accepted or run.
- Retrieved document text is treated as untrusted evidence in the generation system prompt. User-facing errors do not return stack traces.
- Audit rows record login, failed login, bootstrap, upload and analysis events without recording prompts or document text.

Before production use, add refresh/revocation, persistent document-level ACLs, a dedicated read-only analytics database role, TLS, secret-manager integration, immutable audit retention, stronger MIME/content sniffing, antivirus scanning, storage encryption, request correlation and an explicit migration runner. Keep PostgreSQL and Ollama on private networks; never publish the AI runtime.
