"""Run the local auth, upload, SQL, RAG, and hybrid workflow against Compose."""
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
BASE_URL=os.getenv('PBI_API_URL','http://localhost:3000').rstrip('/')
EMAIL=os.getenv('PBI_E2E_EMAIL','admin@example.test')

def local_env(key:str)->str|None:
    env_path=ROOT/'.env'
    if not env_path.exists(): return None
    for line in env_path.read_text().splitlines():
        name,sep,value=line.partition('=')
        if sep and name==key:return value.strip().strip('"\'')
    return None

def request(path:str,method='GET',body:bytes|None=None,headers:dict|None=None):
    req=urllib.request.Request(BASE_URL+path,data=body,headers=headers or {},method=method)
    try:
        with urllib.request.urlopen(req,timeout=240) as response:
            payload=response.read()
            return response.status,json.loads(payload) if payload else {}
    except urllib.error.HTTPError as error:return error.code,json.loads(error.read())

def json_body(value):return json.dumps(value).encode()

def upload(token:str,name:str,content:bytes):
    boundary='----pbi-'+secrets.token_hex(12)
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: text/plain\r\n\r\n'.encode()+content+f'\r\n--{boundary}--\r\n'.encode())
    return request('/api/documents','POST',body,{'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary})

def analyse(token:str,question:str):
    return request('/api/analysis','POST',json_body({'question':question}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})

def main():
    password=os.getenv('PBI_E2E_PASSWORD') or local_env('PBI_E2E_PASSWORD')
    if not password:raise SystemExit('Set PBI_E2E_PASSWORD to a local demo password (12+ characters).')
    status,login=request('/api/auth/login','POST',json_body({'email':EMAIL,'password':password}),{'Content-Type':'application/json'})
    if status!=200:
        bootstrap=local_env('BOOTSTRAP_TOKEN')
        if not bootstrap:raise SystemExit('Login failed and BOOTSTRAP_TOKEN is not available in the local .env.')
        status,_=request('/api/auth/bootstrap','POST',json_body({'organisation':'Northstar Components Demo','email':EMAIL,'password':password}),{'Content-Type':'application/json','x-bootstrap-token':bootstrap})
        if status not in (201,409):raise SystemExit(f'Admin bootstrap failed with HTTP {status}.')
        status,login=request('/api/auth/login','POST',json_body({'email':EMAIL,'password':password}),{'Content-Type':'application/json'})
    if status!=200:raise SystemExit(f'Login failed with HTTP {status}.')
    token=login['data']['accessToken']
    for filename in ('management-report-q2.txt','refund-policy.txt'):
        status,result=upload(token,filename,(ROOT/'data/sample'/filename).read_bytes())
        if status!=201:raise SystemExit(f'Upload {filename} failed with HTTP {status}: {result.get("error",{}).get("code")}')
    for path in ('/api/users','/api/documents','/api/customers','/api/financials','/api/analytics/operations'):
        status,_=request(path,headers={'Authorization':'Bearer '+token})
        if status!=200:raise SystemExit(f'Admin data endpoint {path} failed with HTTP {status}.')
    status,revenue=request('/api/analytics/revenue',headers={'Authorization':'Bearer '+token})
    if status!=200 or len(revenue.get('data',[]))<2:raise SystemExit('Quarterly revenue API did not return at least two periods.')
    status,search=request('/api/search','POST',json_body({'question':'refunds within 30 days'}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    if status!=200 or not search.get('data',{}).get('results'):raise SystemExit('Semantic search failed its evidence assertion.')
    status,hybrid=analyse(token,'Why did revenue fall in Q2?')
    if status!=200 or hybrid.get('data',{}).get('analysisType')!='hybrid' or not hybrid.get('data',{}).get('sources'):raise SystemExit('Hybrid analysis failed its evidence assertions.')
    status,knowledge=analyse(token,'What does our refund policy say?')
    if status!=200 or knowledge.get('data',{}).get('analysisType')!='knowledge' or not knowledge.get('data',{}).get('sources'):raise SystemExit('Knowledge retrieval failed its source assertion.')
    status,audit=request('/api/audit',headers={'Authorization':'Bearer '+token})
    if status!=200 or not audit.get('data'):raise SystemExit('Audit event read failed its evidence assertion.')
    viewer_email='e2e-'+secrets.token_hex(5)+'@example.test'
    status,viewer=request('/api/users','POST',json_body({'email':viewer_email,'password':password,'role':'viewer'}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    if status!=201:raise SystemExit('Admin user creation failed.')
    status,viewer_login=request('/api/auth/login','POST',json_body({'email':viewer_email,'password':password}),{'Content-Type':'application/json'})
    if status!=200:raise SystemExit('Viewer login failed.')
    viewer_token=viewer_login['data']['accessToken']
    status,_=request('/api/users',headers={'Authorization':'Bearer '+viewer_token})
    if status!=403:raise SystemExit('Viewer role was not denied access to user administration.')
    status,_=request('/api/users/'+viewer['data']['id'],'DELETE',headers={'Authorization':'Bearer '+token})
    if status!=204:raise SystemExit('Admin user disable failed.')
    status,_=request('/api/analytics/revenue',headers={'Authorization':'Bearer '+viewer_token})
    if status!=401:raise SystemExit('Disabled user access token was not revoked.')
    print(json.dumps({'login':'passed','revenue':'passed','search':'passed','hybrid':'passed','hybridSources':len(hybrid['data']['sources']),'knowledge':'passed','knowledgeSources':len(knowledge['data']['sources']),'audit':'passed','userRbacAndDisable':'passed'}))

if __name__=='__main__':main()
