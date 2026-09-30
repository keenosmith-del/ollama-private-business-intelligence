ALTER TABLE financial_records
    ADD COLUMN IF NOT EXISTS customer_id uuid REFERENCES customers(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS financial_records_org_customer_idx
    ON financial_records(org_id, customer_id) WHERE customer_id IS NOT NULL;
