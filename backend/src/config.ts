import 'dotenv/config';
import { z } from 'zod';
const schema = z.object({ NODE_ENV:z.enum(['development','test','production']).default('development'), PORT:z.coerce.number().default(3000), DATABASE_URL:z.string().min(1), JWT_SECRET:z.string().min(32), AI_INTERNAL_TOKEN:z.string().min(32), AI_RUNTIME_URL:z.string().url().default('http://localhost:8000'), MAX_FILE_SIZE:z.coerce.number().default(20*1024*1024) });
export const config=schema.parse(process.env);
