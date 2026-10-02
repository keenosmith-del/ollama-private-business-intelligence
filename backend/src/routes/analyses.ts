import {Router} from 'express';
import {z} from 'zod';
import {db} from '../db.js';
import {authenticate} from '../security.js';
export const analysesRouter=Router();
// Saved answers contain excerpts. Re-evaluate every source ACL at read time,
// including deleted documents, so revocation also removes history access.
const permitted=`r.org_id=$1 AND (r.user_id=$2 OR $3='admin') AND NOT EXISTS (
 SELECT 1 FROM jsonb_array_elements(coalesce(result->'sources','[]'::jsonb)) source
 WHERE source->>'type'='document' AND NOT EXISTS (
 SELECT 1 FROM documents d WHERE d.id::text=source->>'id' AND d.org_id=$1 AND
 (d.visibility='organisation' OR d.uploaded_by=$2 OR $3='admin' OR EXISTS
 (SELECT 1 FROM document_access da WHERE da.document_id=d.id AND da.org_id=d.org_id AND (da.user_id=$2 OR da.role=$3)))))`;
analysesRouter.get('/analyses',authenticate,async(req,res,next)=>{try{
 const query=z.object({limit:z.coerce.number().int().min(1).max(100).default(30),offset:z.coerce.number().int().min(0).default(0)}).parse(req.query);
 const {rows}=await db.query(`SELECT r.id,r.question,r.analysis_type,r.status,r.created_at FROM ai_analysis_requests r JOIN ai_analysis_results a ON a.request_id=r.id WHERE ${permitted} ORDER BY r.created_at DESC LIMIT $4 OFFSET $5`,[req.principal!.orgId,req.principal!.userId,req.principal!.role,query.limit,query.offset]);
 res.json({data:rows});
}catch(e){next(e)}});
analysesRouter.get('/analyses/:id',authenticate,async(req,res,next)=>{try{
 const id=z.string().uuid().parse(req.params.id);
 const {rows}=await db.query(`SELECT r.id,r.question,r.analysis_type,r.status,r.created_at,a.result FROM ai_analysis_requests r JOIN ai_analysis_results a ON a.request_id=r.id WHERE ${permitted} AND r.id=$4`,[req.principal!.orgId,req.principal!.userId,req.principal!.role,id]);
 if(!rows.length)return res.status(404).json({error:{code:'NOT_FOUND',message:'Analysis not found or source access revoked'}});
 res.json({data:rows[0]});
}catch(e){next(e)}});
