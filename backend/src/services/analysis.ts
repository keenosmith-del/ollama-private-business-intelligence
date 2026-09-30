import {createHash} from 'node:crypto';
import {db} from '../db.js';

export async function persistAnalysis(orgId:string,userId:string,question:string,result:Record<string,unknown>){
  const client=await db.connect();
  try{
    await client.query('BEGIN');
    const request=await client.query("INSERT INTO ai_analysis_requests(org_id,user_id,question_hash,analysis_type,status) VALUES($1,$2,$3,$4,'completed') RETURNING id",[orgId,userId,createHash('sha256').update(question).digest('hex'),result.analysisType]);
    await client.query('INSERT INTO ai_analysis_results(request_id,result) VALUES($1,$2)',[request.rows[0].id,JSON.stringify(result)]);
    await client.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'analysis.completed',$3)",[orgId,userId,JSON.stringify({requestId:request.rows[0].id,analysisType:result.analysisType})]);
    await client.query('COMMIT');
    return request.rows[0].id as string;
  }catch(error){await client.query('ROLLBACK');throw error}finally{client.release()}
}
