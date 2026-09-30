import pg from 'pg';
import {config} from './config.js';
export const db=new pg.Pool({connectionString:config.DATABASE_URL, max:10, connectionTimeoutMillis:3000, statement_timeout:10000});
