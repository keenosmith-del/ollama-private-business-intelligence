import { Router } from 'express';
import { z } from 'zod';
import { db } from '../db.js';
import { authenticate, allow } from '../security.js';

export const documentAccessRouter = Router();
const documentId = (req: Parameters<typeof authenticate>[0]) => z.string().uuid().parse(req.params.id);

documentAccessRouter.get('/documents/:id/access', authenticate, allow('admin'), async (req, res, next) => {
  try {
    const id = documentId(req);
    const document = await db.query('SELECT id FROM documents WHERE id=$1 AND org_id=$2', [id, req.principal!.orgId]);
    if (!document.rowCount) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Document not found' } });
    const { rows } = await db.query('SELECT da.id,da.user_id,u.email,da.role,da.created_at FROM document_access da LEFT JOIN users u ON u.id=da.user_id WHERE da.document_id=$1 AND da.org_id=$2 ORDER BY da.created_at', [id, req.principal!.orgId]);
    return res.json({ data: rows });
  } catch (error) { next(error); }
});

documentAccessRouter.post('/documents/:id/access', authenticate, allow('admin'), async (req, res, next) => {
  try {
    const id = documentId(req);
    const body = z.object({ userId: z.string().uuid().optional(), role: z.enum(['analyst','viewer']).optional() }).refine(value => Boolean(value.userId) !== Boolean(value.role)).parse(req.body);
    const document = await db.query('SELECT id FROM documents WHERE id=$1 AND org_id=$2', [id, req.principal!.orgId]);
    if (!document.rowCount) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Document not found' } });
    if (body.userId) {
      const user = await db.query('SELECT 1 FROM users WHERE id=$1 AND org_id=$2 AND active=true', [body.userId, req.principal!.orgId]);
      if (!user.rowCount) return res.status(404).json({ error: { code: 'USER_NOT_FOUND', message: 'Active organisation user not found' } });
    }
    const result = await db.query('INSERT INTO document_access(org_id,document_id,user_id,role,granted_by) VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING RETURNING id,user_id,role,created_at', [req.principal!.orgId, id, body.userId ?? null, body.role ?? null, req.principal!.userId]);
    if (result.rowCount) await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'document.access_granted',$3)", [req.principal!.orgId, req.principal!.userId, JSON.stringify({ documentId: id, userId: body.userId, role: body.role })]);
    return res.status(result.rowCount ? 201 : 200).json({ data: result.rows[0] ?? { alreadyGranted: true } });
  } catch (error) { next(error); }
});

documentAccessRouter.delete('/documents/:id/access/:grantId', authenticate, allow('admin'), async (req, res, next) => {
  try {
    const id = documentId(req);
    const grantId = z.string().uuid().parse(req.params.grantId);
    const result = await db.query('DELETE FROM document_access WHERE id=$1 AND document_id=$2 AND org_id=$3 RETURNING id', [grantId, id, req.principal!.orgId]);
    if (!result.rowCount) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Document access grant not found' } });
    await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'document.access_revoked',$3)", [req.principal!.orgId, req.principal!.userId, JSON.stringify({ documentId: id, grantId })]);
    return res.status(204).end();
  } catch (error) { next(error); }
});

documentAccessRouter.patch('/documents/:id', authenticate, allow('admin'), async (req, res, next) => {
  try {
    const id = documentId(req);
    const body = z.object({ visibility: z.enum(['organisation','restricted']) }).parse(req.body);
    const result = await db.query('UPDATE documents SET visibility=$1 WHERE id=$2 AND org_id=$3 RETURNING id,filename,visibility', [body.visibility, id, req.principal!.orgId]);
    if (!result.rowCount) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Document not found' } });
    await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'document.visibility_updated',$3)", [req.principal!.orgId, req.principal!.userId, JSON.stringify({ documentId: id, visibility: body.visibility })]);
    return res.json({ data: result.rows[0] });
  } catch (error) { next(error); }
});
