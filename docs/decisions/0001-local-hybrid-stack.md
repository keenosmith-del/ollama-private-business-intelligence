# ADR 0001: Local hybrid intelligence stack

Status: accepted for initial implementation.

Use Ollama with configurable open-weight models so inference can run inside the organisation's environment. Keep structured facts in PostgreSQL and semantic document chunks in pgvector. Use deterministic query templates for metrics and retrieval plus local generation for concise explanations. This avoids routing sensitive content through a hosted LLM and avoids giving the model unrestricted SQL execution.

PostgreSQL with pgvector is adequate for the expected single-organisation demonstration and simplifies backup/access boundaries compared with a separate vector database. Node/Express remains the public API and auth boundary; Python/FastAPI isolates data/AI processing libraries. Model changes are environment configuration, subject to embedding dimension compatibility.
