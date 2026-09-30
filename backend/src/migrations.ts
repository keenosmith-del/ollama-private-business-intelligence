import { createHash } from 'node:crypto';
import { readdir, readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { db } from './db.js';

const migrationsDirectory = resolve(dirname(fileURLToPath(import.meta.url)), '../../database/migrations');
const legacySentinels: Record<string, string> = {
  '001_initial.sql': "SELECT to_regclass('public.organisations') IS NOT NULL AS present",
  '002_document_dedup.sql': "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='documents' AND column_name='content_sha256') AS present",
  '003_business_data_imports.sql': "SELECT to_regclass('public.data_imports') IS NOT NULL AS present",
  '004_refresh_sessions.sql': "SELECT to_regclass('public.auth_sessions') IS NOT NULL AS present",
};

export async function runMigrations() {
  const files = (await readdir(migrationsDirectory)).filter(file => /^\d+_.+\.sql$/.test(file)).sort();
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    await client.query("SELECT pg_advisory_xact_lock(hashtext('pbi-schema-migrations'))");
    await client.query('CREATE TABLE IF NOT EXISTS schema_migrations(version text PRIMARY KEY, checksum char(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())');
    for (const filename of files) {
      const sql = await readFile(resolve(migrationsDirectory, filename), 'utf8');
      const checksum = createHash('sha256').update(sql).digest('hex');
      const existing = await client.query('SELECT checksum FROM schema_migrations WHERE version=$1', [filename]);
      if (existing.rowCount) {
        if (existing.rows[0].checksum.trim() !== checksum) throw new Error(`Applied migration was modified: ${filename}`);
        continue;
      }

      const sentinel = legacySentinels[filename];
      if (sentinel) {
        const legacy = await client.query<{ present: boolean }>(sentinel);
        if (legacy.rows[0]?.present) {
          await client.query('INSERT INTO schema_migrations(version,checksum) VALUES($1,$2)', [filename, checksum]);
          continue;
        }
      }

      await client.query(sql);
      await client.query('INSERT INTO schema_migrations(version,checksum) VALUES($1,$2)', [filename, checksum]);
    }
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
  }
}
