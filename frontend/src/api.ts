const baseUrl=import.meta.env.VITE_API_URL??'http://localhost:3000/api';
let accessToken:string|undefined;
let refreshInFlight:Promise<{accessToken:string;user:{id:string;email:string;role:string}}|null>|undefined;
export function setAccessToken(token:string|undefined){accessToken=token}
function makeRequest(path:string,init:RequestInit,token=accessToken){
  const headers=new Headers(init.headers);if(token)headers.set('Authorization',`Bearer ${token}`);if(init.body&&!headers.has('Content-Type')&&!(init.body instanceof FormData))headers.set('Content-Type','application/json');
  return fetch(`${baseUrl}${path}`,{...init,headers,credentials:'include'});
}
export async function refreshAccessToken(){
  if(!refreshInFlight)refreshInFlight=(async()=>{try{const response=await makeRequest('/auth/refresh',{method:'POST'},undefined);const payload=await response.json().catch(()=>null);if(!response.ok){accessToken=undefined;return null}accessToken=payload.data.accessToken;return payload.data}catch{accessToken=undefined;return null}})().finally(()=>{refreshInFlight=undefined});
  return refreshInFlight;
}
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
  let response=await makeRequest(path,init);if(response.status===401&&!path.startsWith('/auth/')){const session=await refreshAccessToken();if(session)response=await makeRequest(path,init,session.accessToken)}
  const payload=await response.json().catch(()=>null);
  if(response.status===401&&!path.startsWith('/auth/'))window.dispatchEvent(new Event('pbi-session-expired'));
  if(!response.ok)throw new Error(payload?.error?.message??'The request could not be completed');return payload as T;
}
export const signIn=(email:string,password:string)=>api<{data:{accessToken:string;user:{id:string;email:string;role:string}}}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
export const signOut=()=>api<void>('/auth/logout',{method:'POST'});
export type AnalysisSource = { type?: string; id?: string; name?: string; page?: number | null; description?: string; excerpt?: string };
export type AnalysisMetric = { profit?:number; costs?:number; q1Profit?:number; q2Profit?:number; previousQuarter?:string; targetQuarter?:string; metric?: string; value?: number; quarter?: string; revenue?: number; customer?: string; category?: string; amount?: number; count?: number; severity?: string; change?: number };
export type AnalysisResponse = { answer: string; confidence: string; analysisType: string; sources: AnalysisSource[]; metrics: AnalysisMetric[]; warnings: string[]; latencyMs?: number; inferenceUsed?:boolean };
export const analyse=(question:string)=>api<{data:AnalysisResponse}>('/analysis',{method:'POST',body:JSON.stringify({question})});
