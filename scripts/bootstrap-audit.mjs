// Disposable database only; the existing pbi database is never migrated or reset here.
import pg from 'pg';
import {randomBytes} from 'node:crypto';
import {spawn} from 'node:child_process';
import dotenv from 'dotenv';
dotenv.config({quiet:true});
const name='pbi_bootstrap_audit_'+randomBytes(6).toString('hex');
const base=`postgresql://pbi:pbi-local-only@localhost:${process.env.POSTGRES_PORT??5433}`;
const root=new pg.Client({connectionString:base+'/postgres'});await root.connect();
let child;
try{
 await root.query(`CREATE DATABASE ${name}`);
 child=spawn(process.execPath,['--input-type=module','-e',"const {runMigrations}=await import('./backend/dist/migrations.js');await runMigrations();const {app}=await import('./backend/dist/app.js');app.listen(3001);"],{env:{...process.env,NODE_ENV:'test',DATABASE_URL:base+'/'+name,PORT:'3001'},stdio:['ignore','ignore','pipe']});
 let ready=false;for(let i=0;i<100;i++){try{const r=await fetch('http://localhost:3001/health');if(r.ok){ready=true;break}}catch{}await new Promise(r=>setTimeout(r,100));}
 if(!ready)throw new Error('Isolated bootstrap gateway did not start');
 const password=randomBytes(24).toString('base64url');
 const send=(email,token=process.env.BOOTSTRAP_TOKEN)=>fetch('http://localhost:3001/api/auth/bootstrap',{method:'POST',headers:{'content-type':'application/json','x-bootstrap-token':token},body:JSON.stringify({organisation:'SYNTHETIC DISPOSABLE BOOTSTRAP AUDIT',email,password})});
 if((await send('invalid@example.test','wrong')).status!==403)throw new Error('Invalid bootstrap secret accepted');
 const results=await Promise.all([send('one@example.test'),send('two@example.test')]);
 const statuses=results.map(r=>r.status).sort();if(statuses.join(',')!=='201,409')throw new Error('Concurrent bootstrap was not one-time: '+statuses);
 if((await send('three@example.test')).status!==409)throw new Error('Bootstrap remained open');
 const client=new pg.Client({connectionString:base+'/'+name});await client.connect();
 const users=await client.query('SELECT count(*) FROM users');const migrations=await client.query('SELECT count(*) FROM schema_migrations');
 if(users.rows[0].count!=='1'||migrations.rows[0].count!=='8')throw new Error('Fresh database state incorrect');await client.end();
 console.log(JSON.stringify({freshMigrations:8,invalidSecret:'passed',concurrentBootstrap:'passed',oneTimeBootstrap:'passed'}));
}finally{
 if(child){child.kill('SIGTERM');await new Promise(resolve=>child.once('exit',resolve));}
 await root.query(`DROP DATABASE ${name} WITH (FORCE)`);await root.end();
}
