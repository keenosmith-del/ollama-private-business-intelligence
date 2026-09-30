import {Router} from 'express';
import multer from 'multer';
import {config} from '../config.js';
import {db} from '../db.js';
import {allow,authenticate} from '../security.js';

export const businessDataRouter=Router();
const upload=multer({storage:multer.memoryStorage(),limits:{fileSize:config.MAX_FILE_SIZE,files:1},fileFilter:(_req,file,cb)=>file.mimetype==='text/csv'?cb(null,true):cb(new Error('CSV content type required'))});
businessDataRouter.post('/sales/import',authenticate,allow('admin','analyst'),upload.single('file'),async(req,res,next)=>{
  try{
    if(!req.file||!req.file.originalname.toLowerCase().endsWith('.csv'))return res.status(400).json({error:{code:'VALIDATION_ERROR',message:'A CSV file is required'}});
    const response=await fetch(`${config.AI_RUNTIME_URL}/v1/business-data/sales/import`,{method:'POST',headers:{'content-type':'application/json','x-internal-token':config.AI_INTERNAL_TOKEN,'x-org-id':req.principal!.orgId,'x-user-id':req.principal!.userId},body:JSON.stringify({filename:req.file.originalname,content:req.file.buffer.toString('base64')})});
    const result=await response.json();
    if(!response.ok)return res.status(response.status).json({error:{code:result.detail?.code??'IMPORT_FAILED',message:result.detail?.message??'Sales data could not be imported'}});
    await db.query("INSERT INTO audit_logs(org_id,actor_id,event_type,metadata) VALUES($1,$2,'business_data.imported',$3)",[req.principal!.orgId,req.principal!.userId,JSON.stringify({importId:result.importId,recordsImported:result.recordsImported,filename:req.file.originalname})]);
    res.status(result.alreadyImported?200:201).json({data:result});
  }catch(error){next(error)}
});
