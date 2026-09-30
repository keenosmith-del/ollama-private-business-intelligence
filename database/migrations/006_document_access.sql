ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'organisation'
    CHECK (visibility IN ('organisation','restricted'));

CREATE TABLE IF NOT EXISTS document_access (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id uuid REFERENCES users(id) ON DELETE CASCADE,
    role text CHECK (role IN ('admin','analyst','viewer')),
    granted_by uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((user_id IS NOT NULL AND role IS NULL) OR (user_id IS NULL AND role IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS document_access_user_uq
    ON document_access(document_id,user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS document_access_role_uq
    ON document_access(document_id,role) WHERE role IS NOT NULL;
CREATE INDEX IF NOT EXISTS document_access_org_idx
    ON document_access(org_id,document_id);
