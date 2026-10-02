# Initial security model

- Passwords use bcrypt hashing. Access tokens expire after 30 minutes and carry user, organisation and session-family claims. Authentication reads current user role/active state and requires an unrevoked, unexpired session family. Logout, refresh replay and account disable reject retained bearer access.
- Admin bootstrap requires a separate environment secret and is disabled after the first user exists.
- Express protects user-facing routes with authentication, role checks, request validation, upload size/type limits, Helmet headers and API rate limiting.
- Express forwards organisation scope to the private AI runtime using a shared internal token. The runtime service has no published host port in Compose.
- Every current analytics and retrieval query includes an organisation filter. Model-generated SQL is not accepted or run.
- Retrieved document text is treated as untrusted evidence in the generation system prompt. User-facing errors do not return stack traces.
- Audit rows record login, failed login, bootstrap, upload and analysis events without recording prompts or document text.

Rotating HttpOnly refresh cookies, persistent document ACLs and versioned migration checks are implemented. Saved results containing inaccessible/deleted sources are denied at read time. Retrieved evidence cannot become unrestricted generated answer text: local inference returns validated evidence IDs and the application quotes stored excerpts. Browser CORS defaults to the exact frontend origin; published service ports bind to localhost.

Before production use, add a dedicated read-only analytics database role, TLS, secret-manager integration, immutable audit retention, stronger MIME/content sniffing, antivirus scanning, storage encryption and request correlation. Keep PostgreSQL and Ollama on private networks; never publish the AI runtime.
