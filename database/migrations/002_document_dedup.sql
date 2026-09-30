ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_sha256 text;
CREATE UNIQUE INDEX IF NOT EXISTS documents_org_hash_uq ON documents(org_id,content_sha256) WHERE content_sha256 IS NOT NULL;
