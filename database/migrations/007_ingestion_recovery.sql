-- Keep uploaded bytes locally so a failed or interrupted ingestion can be retried.
ALTER TABLE documents ADD COLUMN source_content bytea;
ALTER TABLE documents ADD COLUMN error_code text;
ALTER TABLE documents ADD COLUMN processing_attempts integer NOT NULL DEFAULT 0;
ALTER TABLE documents ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
