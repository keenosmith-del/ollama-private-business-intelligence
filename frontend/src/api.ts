const baseUrl=import.meta.env.VITE_API_URL??'http://localhost:3000/api';
let accessToken:string|undefined;
export function setAccessToken(token:string|undefined){accessToken=token}
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
  const headers=new Headers(init.headers);if(accessToken)headers.set('Authorization',`Bearer ${accessToken}`);if(init.body&&!headers.has('Content-Type')&&!(init.body instanceof FormData))headers.set('Content-Type','application/json');
  const response=await fetch(`${baseUrl}${path}`,{...init,headers});const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.error?.message??'The request could not be completed');return payload as T;
}
export const signIn=(email:string,password:string)=>api<{data:{accessToken:string;user:{id:string;email:string;role:string}}}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
export const analyse=(question:string)=>api<{data:{answer:string;confidence:string;analysisType:string;sources:unknown[];metrics:unknown[];warnings:string[]}}>('/analysis',{method:'POST',body:JSON.stringify({question})});
