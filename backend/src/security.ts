import type {Request,Response,NextFunction} from 'express';
import jwt from 'jsonwebtoken';
import {config} from './config.js';
import {db} from './db.js';
export type Principal={userId:string;orgId:string;role:'admin'|'analyst'|'viewer'};
declare global {namespace Express {interface Request {principal?:Principal}}}
export async function authenticate(req:Request,res:Response,next:NextFunction){const token=req.headers.authorization?.replace(/^Bearer /,''); if(!token)return res.status(401).json({error:{code:'UNAUTHENTICATED',message:'Authentication required'}}); let principal:Principal;try{principal=jwt.verify(token,config.JWT_SECRET,{issuer:'pbi-api',audience:'pbi-client'}) as Principal}catch{return res.status(401).json({error:{code:'UNAUTHENTICATED',message:'Invalid or expired token'}})}try{const active=await db.query('SELECT 1 FROM users WHERE id=$1 AND org_id=$2 AND active=true',[principal.userId,principal.orgId]);if(!active.rowCount)return res.status(401).json({error:{code:'UNAUTHENTICATED',message:'Account is inactive'}});req.principal=principal;next()}catch{return res.status(503).json({error:{code:'DEPENDENCY_UNAVAILABLE',message:'Authentication service is unavailable'}})}}
export function allow(...roles:Principal['role'][]){return (req:Request,res:Response,next:NextFunction)=>req.principal&&roles.includes(req.principal.role)?next():res.status(403).json({error:{code:'FORBIDDEN',message:'Insufficient permission'}})}
