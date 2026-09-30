import type {Request,Response,NextFunction} from 'express';
import jwt from 'jsonwebtoken';
import {config} from './config.js';
export type Principal={userId:string;orgId:string;role:'admin'|'analyst'|'viewer'};
declare global {namespace Express {interface Request {principal?:Principal}}}
export function authenticate(req:Request,res:Response,next:NextFunction){const token=req.headers.authorization?.replace(/^Bearer /,''); if(!token)return res.status(401).json({error:{code:'UNAUTHENTICATED',message:'Authentication required'}}); try{req.principal=jwt.verify(token,config.JWT_SECRET) as Principal; next()}catch{return res.status(401).json({error:{code:'UNAUTHENTICATED',message:'Invalid or expired token'}})}}
export function allow(...roles:Principal['role'][]){return (req:Request,res:Response,next:NextFunction)=>req.principal&&roles.includes(req.principal.role)?next():res.status(403).json({error:{code:'FORBIDDEN',message:'Insufficient permission'}})}
