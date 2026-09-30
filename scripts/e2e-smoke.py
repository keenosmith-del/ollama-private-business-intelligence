"""Run the local auth, upload, SQL, RAG, and hybrid workflow against Compose."""
import json
import os
import http.cookiejar
from pathlib import Path
import secrets
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
BASE_URL=os.getenv('PBI_API_URL','http://localhost:3000').rstrip('/')
EMAIL=os.getenv('PBI_E2E_EMAIL','admin@example.test')
COOKIE_JAR=http.cookiejar.CookieJar()
OPENER=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))

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
        with OPENER.open(req,timeout=240) as response:
            payload=response.read()
            return response.status,json.loads(payload) if payload else {}
    except urllib.error.HTTPError as error:return error.code,json.loads(error.read())

def json_body(value):return json.dumps(value).encode()

def upload(token:str,name:str,content:bytes,visibility='organisation'):
    boundary='----pbi-'+secrets.token_hex(12)
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: text/plain\r\n\r\n'.encode()+content+f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="visibility"\r\n\r\n{visibility}\r\n--{boundary}--\r\n'.encode())
    return request('/api/documents','POST',body,{'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary})

def import_sales(token:str,content:bytes):
    boundary='----pbi-'+secrets.token_hex(12)
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sales-import.csv"\r\nContent-Type: text/csv\r\n\r\n'.encode()+content+f'\r\n--{boundary}--\r\n'.encode())
    return request('/api/sales/import','POST',body,{'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary})

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
    refresh_before=next((cookie.value for cookie in COOKIE_JAR if cookie.name=='pbi_refresh'),None)
    status,refreshed=request('/api/auth/refresh','POST')
    refresh_after=next((cookie.value for cookie in COOKIE_JAR if cookie.name=='pbi_refresh'),None)
    if status!=200 or not refreshed.get('data',{}).get('accessToken') or refresh_after==refresh_before:raise SystemExit(f'Refresh-token rotation failed with HTTP {status}: {refreshed.get("error",{}).get("code","invalid response")}')
    token=refreshed['data']['accessToken']
    status,organisation=request('/api/organisations/me',headers={'Authorization':'Bearer '+token})
    if status!=200 or not organisation.get('data',{}).get('name'):raise SystemExit('Organisation profile read failed.')
    status,updated_org=request('/api/organisations/me','PATCH',json_body({'name':organisation['data']['name']}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    if status!=200:raise SystemExit('Admin organisation profile update failed.')
    for filename in ('management-report-q2.txt','refund-policy.txt'):
        status,result=upload(token,filename,(ROOT/'data/sample'/filename).read_bytes())
        if status!=201:raise SystemExit(f'Upload {filename} failed with HTTP {status}: {result.get("error",{}).get("code")}')
    restricted_content=(ROOT/'data/sample/restricted-forecast.txt').read_bytes()
    status,restricted=upload(token,'restricted-forecast.txt',restricted_content,'restricted')
    if status!=201 or not restricted.get('data',{}).get('documentId'):raise SystemExit('Restricted document ingestion failed.')
    status,imported=import_sales(token,(ROOT/'data/sample/sales-import.csv').read_bytes())
    if status not in (200,201) or imported.get('data',{}).get('recordsImported')!=3:raise SystemExit('Synthetic sales CSV import failed.')
    status,repeated_import=import_sales(token,(ROOT/'data/sample/sales-import.csv').read_bytes())
    if status!=200 or not repeated_import.get('data',{}).get('alreadyImported'):raise SystemExit('Repeated sales import was not deduplicated.')
    for path in ('/api/users','/api/documents','/api/customers','/api/financials','/api/analytics/operations'):
        status,_=request(path,headers={'Authorization':'Bearer '+token})
        if status!=200:raise SystemExit(f'Admin data endpoint {path} failed with HTTP {status}.')
    status,revenue=request('/api/analytics/revenue',headers={'Authorization':'Bearer '+token})
    if status!=200 or len(revenue.get('data',[]))<2:raise SystemExit('Quarterly revenue API did not return at least two periods.')
    status,search=request('/api/search','POST',json_body({'question':'refunds within 30 days'}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    if status!=200 or not search.get('data',{}).get('results'):raise SystemExit('Semantic search failed its evidence assertion.')
    status,hybrid=analyse(token,'Why did revenue fall in Q2?')
    if status!=200 or hybrid.get('data',{}).get('analysisType')!='hybrid' or not hybrid.get('data',{}).get('sources'):raise SystemExit('Hybrid analysis failed its evidence assertions.')
    q2_change=next((m.get('value') for m in hybrid['data'].get('metrics',[]) if m.get('metric')=='q2_change_percent'),None)
    if q2_change!=-40.09:raise SystemExit(f'Q2 comparison selected the wrong quarters: {q2_change}')
    status,knowledge=analyse(token,'What does our refund policy say?')
    if status!=200 or knowledge.get('data',{}).get('analysisType')!='knowledge' or not knowledge.get('data',{}).get('sources'):raise SystemExit('Knowledge retrieval failed its source assertion.')
    status,profitability=analyse(token,'Which customers are least profitable?')
    profits=profitability.get('data',{}).get('metrics',[])
    if status!=200 or profitability.get('data',{}).get('analysisType')!='analytics' or not any('profit' in metric for metric in profits):raise SystemExit('Customer profitability analysis failed its metric assertion.')
    status,profit_trend=analyse(token,'Which customers are becoming less profitable?')
    trend_metrics=profit_trend.get('data',{}).get('metrics',[])
    if status!=200 or not any('q1Profit' in metric and 'q2Profit' in metric for metric in trend_metrics):raise SystemExit('Customer profitability trend analysis failed its metric assertion.')
    status,audit=request('/api/audit',headers={'Authorization':'Bearer '+token})
    if status!=200 or not audit.get('data'):raise SystemExit('Audit event read failed its evidence assertion.')
    status,_=request('/api/auth/logout','POST')
    if status!=204:raise SystemExit('Logout did not revoke the refresh session.')
    status,_=request('/api/auth/refresh','POST')
    if status!=401:raise SystemExit('A logged-out refresh session remained active.')
    viewer_email='e2e-'+secrets.token_hex(5)+'@example.test'
    status,viewer=request('/api/users','POST',json_body({'email':viewer_email,'password':password,'role':'viewer'}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    if status!=201:raise SystemExit('Admin user creation failed.')
    status,viewer_login=request('/api/auth/login','POST',json_body({'email':viewer_email,'password':password}),{'Content-Type':'application/json'})
    if status!=200:raise SystemExit('Viewer login failed.')
    viewer_token=viewer_login['data']['accessToken']
    status,_=request('/api/organisations/me','PATCH',json_body({'name':organisation['data']['name']}),{'Authorization':'Bearer '+viewer_token,'Content-Type':'application/json'})
    if status!=403:raise SystemExit('Viewer role was not denied organisation administration.')
    status,denied_search=request('/api/search','POST',json_body({'question':'violet quartz cipher forecast'}),{'Authorization':'Bearer '+viewer_token,'Content-Type':'application/json'})
    if status!=200 or any(result.get('filename')=='restricted-forecast.txt' for result in denied_search.get('data',{}).get('results',[])):raise SystemExit('Restricted document appeared in viewer search before access was granted.')
    status,grant=request(f"/api/documents/{restricted['data']['documentId']}/access",'POST',json_body({'role':'viewer'}),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    if status!=201:raise SystemExit('Admin could not grant document access to a role.')
    status,allowed_search=request('/api/search','POST',json_body({'question':'violet quartz cipher forecast'}),{'Authorization':'Bearer '+viewer_token,'Content-Type':'application/json'})
    if status!=200 or not any(result.get('filename')=='restricted-forecast.txt' for result in allowed_search.get('data',{}).get('results',[])):raise SystemExit('Role-based document access grant did not enable retrieval.')
    status,allowed_analysis=analyse(viewer_token,'Summarise the violet quartz cipher forecast.')
    if status!=200 or not any(source.get('name')=='restricted-forecast.txt' for source in allowed_analysis.get('data',{}).get('sources',[])):raise SystemExit('Granted restricted document was not available to RAG analysis.')
    status,_=request(f"/api/documents/{restricted['data']['documentId']}/access/{grant['data']['id']}",'DELETE',headers={'Authorization':'Bearer '+token})
    if status!=204:raise SystemExit('Admin could not revoke document access.')
    status,revoked_search=request('/api/search','POST',json_body({'question':'violet quartz cipher forecast'}),{'Authorization':'Bearer '+viewer_token,'Content-Type':'application/json'})
    if status!=200 or any(result.get('filename')=='restricted-forecast.txt' for result in revoked_search.get('data',{}).get('results',[])):raise SystemExit('Revoked document access remained available in semantic search.')
    status,revoked_analysis=analyse(viewer_token,'Summarise the violet quartz cipher forecast.')
    if status!=200 or any(source.get('name')=='restricted-forecast.txt' for source in revoked_analysis.get('data',{}).get('sources',[])):raise SystemExit('Revoked restricted document remained available to RAG analysis.')
    status,_=request('/api/users',headers={'Authorization':'Bearer '+viewer_token})
    if status!=403:raise SystemExit('Viewer role was not denied access to user administration.')
    status,_=request('/api/users/'+viewer['data']['id'],'DELETE',headers={'Authorization':'Bearer '+token})
    if status!=204:raise SystemExit('Admin user disable failed.')
    status,_=request('/api/analytics/revenue',headers={'Authorization':'Bearer '+viewer_token})
    if status!=401:raise SystemExit('Disabled user access token was not revoked.')
    print(json.dumps({'login':'passed','refreshRotation':'passed','organisationAdministration':'passed','documentAcl':'passed','revenue':'passed','customerProfitability':'passed','profitabilityTrend':'passed','search':'passed','hybrid':'passed','hybridSources':len(hybrid['data']['sources']),'knowledge':'passed','knowledgeSources':len(knowledge['data']['sources']),'audit':'passed','userRbacAndDisable':'passed','logout':'passed'}))

if __name__=='__main__':main()
