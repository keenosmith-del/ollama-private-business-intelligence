import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { Router, type Request, type Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { config } from '../config.js';
import { db } from '../db.js';
import { authenticate } from '../security.js';

export const authRouter = Router();
const refreshCookie = 'pbi_refresh';
const refreshLifetimeMs = 14 * 24 * 60 * 60 * 1000;
const cookieOptions = { httpOnly: true, secure: config.NODE_ENV === 'production', sameSite: 'strict' as const, path: '/api/auth' };

function readCookie(req: Request, name: string) {
  const value = req.headers.cookie?.split(';').map(part => part.trim()).find(part => part.startsWith(`${name}=`))?.slice(name.length + 1);
  if (!value) return undefined;
  try { return decodeURIComponent(value); } catch { return undefined; }
}

function tokenHash(token: string) { return createHash('sha256').update(token).digest('hex'); }
function makeAccessToken(user: { id: string; org_id: string; role: 'admin' | 'analyst' | 'viewer' }) {
  return jwt.sign({ userId: user.id, orgId: user.org_id, role: user.role }, config.JWT_SECRET, { expiresIn: '30m', issuer: 'pbi-api', audience: 'pbi-client' });
}
function setRefreshCookie(res: Response, token: string) { res.cookie(refreshCookie, token, { ...cookieOptions, maxAge: refreshLifetimeMs }); }
function clearRefreshCookie(res: Response) { res.clearCookie(refreshCookie, cookieOptions); }

authRouter.post('/bootstrap', async (req, res, next) => {
  try {
    const token = process.env.BOOTSTRAP_TOKEN;
    if (!token || req.headers['x-bootstrap-token'] !== token) return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Bootstrap is not enabled' } });
    const body = z.object({ organisation: z.string().trim().min(2).max(120), email: z.string().email().max(254), password: z.string().min(12).max(200) }).parse(req.body);
    const existing = await db.query('SELECT 1 FROM users LIMIT 1');
    if (existing.rowCount) return res.status(409).json({ error: { code: 'BOOTSTRAP_COMPLETE', message: 'An initial user already exists' } });
    const hash = await bcrypt.hash(body.password, 12);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const org = await client.query('INSERT INTO organisations(name) VALUES($1) RETURNING id', [body.organisation]);
      const user = await client.query("INSERT INTO users(org_id,email,password_hash,role) VALUES($1,lower($2),$3,'admin') RETURNING id,org_id,email,role", [org.rows[0].id, body.email, hash]);
      await client.query("INSERT INTO audit_logs(org_id,actor_id,event_type) VALUES($1,$2,'auth.bootstrap')", [org.rows[0].id, user.rows[0].id]);
      await client.query('COMMIT');
      return res.status(201).json({ data: user.rows[0] });
    } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
  } catch (e) { next(e); }
});

authRouter.post('/login', async (req, res, next) => {
  try {
    const body = z.object({ email: z.string().email().max(254), password: z.string().min(1).max(200) }).parse(req.body);
    const { rows } = await db.query("SELECT id,org_id,email,password_hash,role FROM users WHERE lower(email)=lower($1) AND active=true", [body.email]);
    const user = rows[0];
    if (!user || !(await bcrypt.compare(body.password, user.password_hash))) {
      await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES ($1,$2,'auth.login_failed','{}')", [user?.org_id ?? null, user?.id ?? null]).catch(() => {});
      return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Email or password is incorrect' } });
    }
    const refreshToken = randomBytes(48).toString('base64url');
    await db.query('INSERT INTO auth_sessions(family_id,user_id,org_id,token_hash,expires_at) VALUES($1,$2,$3,$4,now()+interval \'14 days\')', [randomUUID(), user.id, user.org_id, tokenHash(refreshToken)]);
    await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES ($1,$2,'auth.login','{}')", [user.org_id, user.id]);
    setRefreshCookie(res, refreshToken);
    return res.json({ data: { accessToken: makeAccessToken(user), tokenType: 'Bearer', expiresIn: 1800, user: { id: user.id, email: user.email, role: user.role, orgId: user.org_id } } });
  } catch (e) { next(e); }
});

authRouter.post('/refresh', async (req, res) => {
  const refreshToken = readCookie(req, refreshCookie);
  if (!refreshToken) return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Refresh session is unavailable' } });
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    const result = await client.query('SELECT s.id,s.family_id,s.user_id,s.org_id,s.expires_at,s.revoked_at,u.email,u.role,u.active FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=$1 FOR UPDATE OF s', [tokenHash(refreshToken)]);
    const session = result.rows[0];
    if (!session) { await client.query('ROLLBACK'); clearRefreshCookie(res); return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Refresh session is invalid' } }); }
    if (session.revoked_at) {
      await client.query('UPDATE auth_sessions SET revoked_at=coalesce(revoked_at,now()) WHERE family_id=$1', [session.family_id]);
      await client.query('COMMIT'); clearRefreshCookie(res);
      return res.status(401).json({ error: { code: 'SESSION_REPLAYED', message: 'Refresh session is no longer valid' } });
    }
    if (!session.active || new Date(session.expires_at).getTime() <= Date.now()) {
      await client.query('UPDATE auth_sessions SET revoked_at=coalesce(revoked_at,now()) WHERE family_id=$1', [session.family_id]);
      await client.query('COMMIT'); clearRefreshCookie(res);
      return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Refresh session has expired' } });
    }
    const nextToken = randomBytes(48).toString('base64url');
    const nextId = randomUUID();
    await client.query('INSERT INTO auth_sessions(id,family_id,user_id,org_id,token_hash,expires_at) VALUES($1,$2,$3,$4,$5,now()+interval \'14 days\')', [nextId, session.family_id, session.user_id, session.org_id, tokenHash(nextToken)]);
    await client.query('UPDATE auth_sessions SET revoked_at=now(),replaced_by=$2 WHERE id=$1', [session.id, nextId]);
    await client.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'auth.refreshed','{}')", [session.org_id, session.user_id]);
    await client.query('COMMIT');
    setRefreshCookie(res, nextToken);
    return res.json({ data: { accessToken: makeAccessToken({ id: session.user_id, org_id: session.org_id, role: session.role }), tokenType: 'Bearer', expiresIn: 1800, user: { id: session.user_id, email: session.email, role: session.role, orgId: session.org_id } } });
  } catch { await client.query('ROLLBACK').catch(() => {}); clearRefreshCookie(res); return res.status(503).json({ error: { code: 'DEPENDENCY_UNAVAILABLE', message: 'Authentication service is unavailable' } }); } finally { client.release(); }
});

authRouter.post('/logout', async (req, res) => {
  const refreshToken = readCookie(req, refreshCookie);
  if (refreshToken) {
    try {
      const result = await db.query('UPDATE auth_sessions SET revoked_at=coalesce(revoked_at,now()) WHERE token_hash=$1 RETURNING user_id,org_id', [tokenHash(refreshToken)]);
      if (result.rowCount) await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'auth.logout','{}')", [result.rows[0].org_id, result.rows[0].user_id]);
    } catch { clearRefreshCookie(res); return res.status(503).json({ error: { code: 'DEPENDENCY_UNAVAILABLE', message: 'Authentication service is unavailable' } }); }
  }
  clearRefreshCookie(res);
  return res.status(204).end();
});

authRouter.get('/me', authenticate, (req, res) => res.json({ data: req.principal }));
