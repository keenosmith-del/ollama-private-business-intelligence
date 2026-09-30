import { Router } from 'express';
import { z } from 'zod';
import { db } from '../db.js';
import { authenticate, allow } from '../security.js';

export const organisationsRouter = Router();

organisationsRouter.get('/me', authenticate, async (req, res, next) => {
  try {
    const result = await db.query('SELECT id,name,created_at FROM organisations WHERE id=$1', [req.principal!.orgId]);
    if (!result.rowCount) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Organisation not found' } });
    return res.json({ data: result.rows[0] });
  } catch (error) { next(error); }
});

organisationsRouter.patch('/me', authenticate, allow('admin'), async (req, res, next) => {
  try {
    const body = z.object({ name: z.string().trim().min(2).max(120) }).parse(req.body);
    const result = await db.query('UPDATE organisations SET name=$1 WHERE id=$2 RETURNING id,name,created_at', [body.name, req.principal!.orgId]);
    if (!result.rowCount) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Organisation not found' } });
    await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'organisation.updated',$3)", [req.principal!.orgId, req.principal!.userId, JSON.stringify({ name: body.name })]);
    return res.json({ data: result.rows[0] });
  } catch (error) { next(error); }
});
