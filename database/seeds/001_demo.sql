-- Synthetic quarterly sales for the first provisioned organisation.
INSERT INTO customers(id,org_id,name,industry)
SELECT 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',id,'Acme Retail','Retail' FROM organisations ORDER BY created_at LIMIT 1
ON CONFLICT(id) DO NOTHING;
INSERT INTO customers(id,org_id,name,industry)
SELECT 'cccccccc-cccc-cccc-cccc-cccccccccccc',id,'Blue Peak Systems','Technology' FROM organisations ORDER BY created_at LIMIT 1
ON CONFLICT(id) DO NOTHING;
INSERT INTO sales(id,org_id,customer_id,sale_date,amount)
SELECT v.id,o.id,v.customer_id,v.sale_date,v.amount FROM organisations o CROSS JOIN (VALUES
('dddddddd-dddd-dddd-dddd-dddddddddddd'::uuid,'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid,'2026-01-15'::date,120000::numeric),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'::uuid,'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,'2026-02-20'::date,92000::numeric),
('ffffffff-ffff-ffff-ffff-ffffffffffff'::uuid,'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid,'2026-04-15'::date,76000::numeric),
('11111111-2222-3333-4444-555555555555'::uuid,'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,'2026-05-20'::date,51000::numeric)
) v(id,customer_id,sale_date,amount)
WHERE o.id=(SELECT id FROM organisations ORDER BY created_at LIMIT 1)
ON CONFLICT(id) DO NOTHING;
INSERT INTO financial_records(id,org_id,record_date,category,amount,description,customer_id)
SELECT v.id,o.id,v.record_date,v.category,v.amount,v.description,v.customer_id FROM organisations o CROSS JOIN (VALUES
('22222222-2222-3333-4444-555555555555'::uuid,'2026-02-28'::date,'Logistics',18500::numeric,'Expedited Q1 shipments',NULL::uuid),
('33333333-2222-3333-4444-555555555555'::uuid,'2026-05-31'::date,'Logistics',34750::numeric,'Expedited Q2 shipments',NULL::uuid),
('44444444-2222-3333-4444-555555555555'::uuid,'2026-05-31'::date,'Returns',12900::numeric,'Q2 customer returns and replacements',NULL::uuid),
('88888888-2222-3333-4444-555555555555'::uuid,'2026-02-15'::date,'Customer delivery costs',40000::numeric,'Acme Retail Q1 service and delivery costs','bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid),
('99999999-2222-3333-4444-555555555555'::uuid,'2026-05-15'::date,'Customer delivery costs',35000::numeric,'Acme Retail Q2 service and delivery costs','bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid),
('aaaaaaaa-2222-3333-4444-555555555555'::uuid,'2026-02-15'::date,'Customer delivery costs',45000::numeric,'Blue Peak Systems Q1 service and delivery costs','cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid),
('bbbbbbbb-2222-3333-4444-555555555555'::uuid,'2026-05-15'::date,'Customer delivery costs',48000::numeric,'Blue Peak Systems Q2 service and delivery costs','cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid)
) v(id,record_date,category,amount,description,customer_id)
WHERE o.id=(SELECT id FROM organisations ORDER BY created_at LIMIT 1) ON CONFLICT(id) DO NOTHING;
INSERT INTO operational_records(id,org_id,occurred_at,category,severity,description)
SELECT v.id,o.id,v.occurred_at,v.category,v.severity,v.description FROM organisations o CROSS JOIN (VALUES
('55555555-2222-3333-4444-555555555555'::uuid,'2026-05-08 09:30+00'::timestamptz,'Supplier delay','high','Critical component delivery arrived nine days late.'),
('66666666-2222-3333-4444-555555555555'::uuid,'2026-05-21 14:00+00'::timestamptz,'System outage','medium','Order processing was unavailable for 74 minutes.'),
('77777777-2222-3333-4444-555555555555'::uuid,'2026-06-02 11:15+00'::timestamptz,'Supplier delay','high','Second late shipment from the same component supplier.')
) v(id,occurred_at,category,severity,description)
WHERE o.id=(SELECT id FROM organisations ORDER BY created_at LIMIT 1) ON CONFLICT(id) DO NOTHING;
