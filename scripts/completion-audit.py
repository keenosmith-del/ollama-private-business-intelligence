"""Real local integration audit. Adds labelled synthetic records in isolated organisations.
Run with the project venv; never resets existing volumes or business records.
"""
import importlib.util
import io
import json
from pathlib import Path
import secrets
import time
import uuid

import httpx
import psycopg
from docx import Document
from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('smoke', ROOT/'scripts/e2e-smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
DB = f"postgresql://pbi:pbi-local-only@localhost:{smoke.local_env('POSTGRES_PORT') or '5433'}/pbi"
BASE = smoke.BASE_URL
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS '+name, flush=True)


def call(token, path, method='GET', body=None):
    return smoke.request(path, method, smoke.json_body(body) if body is not None else None, {'Authorization':'Bearer '+token,'Content-Type':'application/json'})


def upload(token, name, content, mime='text/plain', visibility='organisation'):
    with httpx.Client(timeout=240) as client:
        r=client.post(BASE+'/api/documents',headers={'Authorization':'Bearer '+token},files={'file':(name,content,mime)},data={'visibility':visibility})
        return r.status_code,r.json()


def import_csv(token, kind, content):
    with httpx.Client(timeout=240) as client:
        r=client.post(BASE+f'/api/{kind}/import',headers={'Authorization':'Bearer '+token},files={'file':('synthetic-audit.csv',content,'text/csv')})
        return r.status_code,r.json()


def login(email, password):
    code,p=smoke.request('/api/auth/login','POST',smoke.json_body({'email':email,'password':password}),{'Content-Type':'application/json'})
    check('login '+email.split('@')[0],code==200)
    return p['data']['accessToken']


def create_org(conn, name, email, password):
    org=conn.execute('INSERT INTO organisations(name) VALUES(%s) RETURNING id',(name,)).fetchone()[0]
    user=conn.execute("INSERT INTO users(org_id,email,password_hash,role) VALUES(%s,%s,crypt(%s,gen_salt('bf',12)),'admin') RETURNING id",(org,email,password)).fetchone()[0]
    conn.commit()
    return str(org),str(user)


def fixtures():
    text='SYNTHETIC COMPLETION AUDIT: Internal expense policy requires receipts for every reimbursement. Travel above ZAR 500 requires manager approval. Management report Q2 2027: revenue declined; supplier delays deferred shipments and a system outage disrupted order processing. These are management explanations; no causal loss amount has been established.'
    doc=Document();doc.add_paragraph(text);doc.add_table(rows=1,cols=1).cell(0,0).text='Synthetic policy control: approval required.'
    docx=io.BytesIO();doc.save(docx)
    book=Workbook();book.active.append(['description','amount']);book.active.append([text,500]);xlsx=io.BytesIO();book.save(xlsx)
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 10 Tf 20 700 Td (SYNTHETIC AUDIT: Expense receipts and manager approval are required.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream);pdf=io.BytesIO();writer.write(pdf)
    return [('synthetic-audit.txt',text.encode(),'text/plain'),('synthetic-audit.docx',docx.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),('synthetic-audit.xlsx',xlsx.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),('synthetic-audit.pdf',pdf.getvalue(),'application/pdf'),('synthetic-audit.csv',b'policy,requirement\nExpense,Receipts and manager approval required\n','text/csv')]


def main():
    run=secrets.token_hex(4);password=secrets.token_urlsafe(24)
    with psycopg.connect(DB) as conn:
        org,admin_id=create_org(conn,'SYNTHETIC COMPLETION AUDIT '+run,'audit-'+run+'@example.test',password)
        other,_=create_org(conn,'SYNTHETIC ISOLATION AUDIT '+run,'other-'+run+'@example.test',password)
        token=login('audit-'+run+'@example.test',password)
        code,_=smoke.request('/api/auth/bootstrap','POST',smoke.json_body({'organisation':'Synthetic','email':'closed@example.test','password':password}),{'Content-Type':'application/json','x-bootstrap-token':smoke.local_env('BOOTSTRAP_TOKEN')})
        check('bootstrap closed after existing users',code==409)
        sales=b'customer,date,amount,industry\nSynthetic Alpha,2027-01-15,120000,Retail\nSynthetic Beta,2027-02-15,80000,Services\nSynthetic Alpha,2027-04-15,70000,Retail\nSynthetic Beta,2027-05-15,50000,Services\n'
        expenses=b'category,date,amount,customer,description\nDelivery,2027-02-01,40000,Synthetic Alpha,Q1 direct costs\nDelivery,2027-02-01,30000,Synthetic Beta,Q1 direct costs\nDelivery,2027-05-01,40000,Synthetic Alpha,Q2 direct costs\nDelivery,2027-05-01,55000,Synthetic Beta,Q2 direct costs\nLogistics,2027-05-01,30000,,Expedited shipments\nReturns,2027-05-01,12000,,Returns exposure\n'
        code,p=import_csv(token,'sales',sales);check('sales/customer import',code==201 and p['data']['recordsImported']==4)
        code,p=import_csv(token,'sales',sales);check('sales idempotency',code==200 and p['data']['alreadyImported'])
        code,p=import_csv(token,'expenses',expenses);check('attributed and shared expense import',code==201 and p['data']['recordsImported']==6)
        code,p=import_csv(token,'expenses',expenses);check('expense idempotency',code==200 and p['data']['alreadyImported'])
        before=conn.execute('SELECT count(*) FROM financial_records WHERE org_id=%s',(org,)).fetchone()[0]
        code,_=import_csv(token,'expenses',b'category,date,amount,customer\nSynthetic,2027-05-01,20,Unknown customer\n');check('invalid customer rolls back expense import',code==422 and conn.execute('SELECT count(*) FROM financial_records WHERE org_id=%s',(org,)).fetchone()[0]==before)
        for raw in (b'customer,date,amount\nSynthetic,invalid,1\n',b'customer,date,amount\nSynthetic,2027-05-01,-1\n'):
            code,_=import_csv(token,'sales',raw);check('invalid sales rejected',code==422)
        conn.execute('INSERT INTO operational_records(org_id,occurred_at,category,severity,description) VALUES(%s,%s,%s,%s,%s)',(org,'2027-05-01','Supplier delay','high','SYNTHETIC: deferred shipments'));conn.commit()
        documents=[]
        for name,content,mime in fixtures():
            code,p=upload(token,name,content,mime);check('real embedding and indexing '+name,code==201 and p['data']['chunks']>0);documents.append(p['data']['documentId'])
        import hashlib
        concurrent_raw=b'SYNTHETIC concurrent lock audit'
        lock_key=org+hashlib.sha256(concurrent_raw).hexdigest()
        conn.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',(lock_key,))
        try:
            code,p=upload(token,'synthetic-concurrent.txt',concurrent_raw)
            check('concurrent processing returns retryable conflict without blocking runtime',code==409 and p['error']['code']=='DOCUMENT_PROCESSING')
        finally:
            conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(lock_key,));conn.commit()
        code,p=upload(token,'synthetic-audit.txt',fixtures()[0][1]);check('ready document deduplication',code==201 and p['data']['alreadyIndexed'])
        code,p=upload(token,'synthetic-broken.pdf',b'not a pdf','application/pdf');check('parse failure returned',code==422);failed=p['error']['documentId']
        code,p=call(token,'/api/documents/'+failed);check('persistent failed ingestion status',code==200 and p['data']['status']=='failed' and p['data']['error_code']=='DOCUMENT_PARSE_ERROR')
        code,_=call(token,'/api/documents/'+failed+'/retry','POST');check('invalid bytes retry remains failed',code==422)
        code,p=call(token,'/api/documents/'+failed);check('retry attempt persisted',p['data']['processing_attempts']==2)
        code,_=upload(token,'unsupported.exe',b'exe','application/octet-stream');check('unsupported MIME rejected',code==415)
        code,p=upload(token,'empty.txt',b'');check('empty text rejected',code==422 and 'documentId' in p['error'])
        # Seed one retryable valid document as an interrupted upload, then use the actual API.
        retry_id=str(uuid.uuid4());raw=b'SYNTHETIC RECOVERY: Receipts required for expenses.'
        conn.execute("INSERT INTO documents(id,org_id,uploaded_by,filename,mime_type,status,content_sha256,source_content,error_code) VALUES(%s,%s,%s,'synthetic-recovery.txt','text/plain','failed',%s,%s,'INTERRUPTED')",(retry_id,org,admin_id,hashlib.sha256(raw).hexdigest(),raw));conn.commit()
        code,p=call(token,'/api/documents/'+retry_id+'/retry','POST');check('failed valid document recovers with real embeddings',code==200 and p['data']['status']=='ready')
        questions=['What was our revenue in Q2?','Compare Q1 and Q2 revenue.','Which customers generated the most revenue?','Which customers are least profitable?','What are our largest expense categories?','What are the three biggest areas of financial loss or cost exposure?','Why did revenue decline in Q2?','What does our internal expense policy say?','What operational issues may have contributed to financial performance?','Which customers are becoming less profitable? Compare Q1 and Q2.','What was our profitability in Q2?']
        results=[]
        for q in questions:
            code,p=call(token,'/api/analysis','POST',{'question':q});check('real inference: '+q,code==200 and p['data'].get('inferenceUsed') is True and p['data']['sources']);results.append(p)
        rows=conn.execute("SELECT date_trunc('quarter',sale_date)::date,sum(amount) FROM sales WHERE org_id=%s GROUP BY 1 ORDER BY 1",(org,)).fetchall()
        check('Q2 matches independent database sum',results[0]['data']['metrics'][0]['revenue']==float(rows[1][1])==120000)
        metrics=results[1]['data']['metrics'];check('Q1/Q2 sums and percentage match database',metrics[0]['revenue']==float(rows[0][1])==200000 and metrics[1]['revenue']==120000 and metrics[2]['value']==-40)
        top=conn.execute('SELECT c.name,sum(s.amount) FROM sales s JOIN customers c ON s.customer_id=c.id WHERE s.org_id=%s GROUP BY c.name ORDER BY 2 DESC',(org,)).fetchall()
        ranked=[m for m in results[2]['data']['metrics'] if 'customer' in m];check('customer revenue matches independent SQL',[(m['customer'],m['revenue']) for m in ranked]==[(r[0],float(r[1])) for r in top])
        profits=conn.execute('SELECT c.name,(SELECT sum(amount) FROM sales WHERE customer_id=c.id)-(SELECT sum(amount) FROM financial_records WHERE customer_id=c.id) profit FROM customers c WHERE org_id=%s ORDER BY 2',(org,)).fetchall()
        ranked=[m for m in results[3]['data']['metrics'] if 'profit' in m];check('customer profit matches independent SQL',[(m['customer'],m['profit']) for m in ranked]==[(r[0],float(r[1])) for r in profits])
        costs=conn.execute('SELECT category,sum(amount) FROM financial_records WHERE org_id=%s GROUP BY 1 ORDER BY 2 DESC',(org,)).fetchall()
        for i in (4,5):check('expense sums match independent SQL '+str(i),[(m['category'],m['amount']) for m in results[i]['data']['metrics']]==[(r[0],float(r[1])) for r in costs])
        check('cost exposure is not asserted as a loss',any('not proven' in w for w in results[5]['data']['warnings']))
        check('causal explanation labelled with source excerpts',results[6]['data']['answer'].startswith('Established financial facts:') and any(s.get('excerpt') for s in results[6]['data']['sources']) and any('not causes' in w for w in results[6]['data']['warnings']))
        narrative=results[6]['data']['answer'].split('Management document evidence (exact excerpts; not proven causation):\n',1)[1]
        cited=[block for block in narrative.split('[Source: ') if block]
        check('causal response contains only original source excerpts',bool(cited) and all(block.split(']\n',1)[1].strip() in [s.get('excerpt') for s in results[6]['data']['sources']] for block in cited))
        narrative=results[8]['data']['answer'].split('Management document evidence (exact excerpts; not proven causation):\n',1)[1]
        check('operational explanation cannot invent financial impact',all(block.split(']\n',1)[1].strip() in [s.get('excerpt') for s in results[8]['data']['sources']] for block in narrative.split('[Source: ') if block))
        check('expense policy is knowledge only',results[7]['data']['analysisType']=='knowledge' and not results[7]['data']['metrics'])
        check('operational incidents present',any(m.get('category')=='Supplier delay' and m.get('count')==1 for m in results[8]['data']['metrics']))
        trends=results[9]['data']['metrics'];check('profit trend actual amounts',any(m.get('customer')=='Synthetic Beta' and m.get('q1Profit')==50000 and m.get('q2Profit')==-5000 and m.get('change')==-55000 for m in trends))
        profit=next(m['value'] for m in results[10]['data']['metrics'] if m.get('metric')=='recorded_profit')
        actual=conn.execute("SELECT (SELECT sum(amount) FROM sales WHERE org_id=%s AND sale_date >= '2027-04-01' AND sale_date < '2027-07-01')-(SELECT sum(amount) FROM financial_records WHERE org_id=%s AND record_date >= '2027-04-01' AND record_date < '2027-07-01')",(org,org)).fetchone()[0]
        check('overall Q2 recorded profit matches independent SQL',profit==float(actual)==-17000)
        conn.execute("INSERT INTO sales(org_id,customer_id,sale_date,amount) SELECT %s,id,'2027-09-01',999999 FROM customers WHERE org_id=%s LIMIT 1",(org,org));conn.commit()
        code,p=call(token,'/api/analysis','POST',{'question':'Compare Q1 and Q2 revenue.'});check('Q3 cannot change Q1/Q2 selection',p['data']['metrics'][2]['value']==-40)
        code,p=call(token,'/api/analysis','POST',{'question':'What was our revenue in Q4 2028?'});check('missing period does not select unrelated revenue',p['data']['metrics'][0]['revenue']==0 and p['data']['warnings'])
        code,p=call(token,'/api/analyses/'+results[6]['meta']['requestId']);check('saved analysis inspection',code==200 and p['data']['question']==questions[6] and p['data']['result']['metrics']==results[6]['data']['metrics'])
        check('analysis and audit persisted',conn.execute("SELECT count(*) FROM audit_logs WHERE org_id=%s AND event_type='analysis.completed'",(org,)).fetchone()[0]>=12)
        # Restricted source and both role and individual grants, including saved-answer revocation.
        code,p=upload(token,'synthetic-secret.txt',b'SYNTHETIC restricted sapphire ledger policy: approval code is amber orbit.','text/plain','restricted');secret_id=p['data']['documentId']
        code,p=call(token,'/api/users','POST',{'email':'viewer-'+run+'@example.test','password':password,'role':'viewer'});viewer_id=p['data']['id'];viewer=login('viewer-'+run+'@example.test',password)
        code,_=call(viewer,'/api/users');check('viewer cannot administer users',code==403)
        code,_=import_csv(viewer,'sales',sales);check('viewer cannot import',code==403)
        code,p=call(viewer,'/api/search','POST',{'question':'sapphire ledger approval code'});check('restricted search denied',not any(r['documentId']==secret_id for r in p['data']['results']))
        code,p=call(token,'/api/documents/'+secret_id+'/access','POST',{'userId':viewer_id});grant=p['data']['id'];check('individual grant created',code==201)
        code,p=call(viewer,'/api/analysis','POST',{'question':'What does the sapphire ledger policy say?'});saved=p['meta']['requestId'];check('granted restricted RAG retrieval',any(s.get('id')==secret_id for s in p['data']['sources']))
        code,_=call(viewer,'/api/analyses/'+saved);check('granted saved result readable',code==200)
        code,_=call(token,'/api/documents/'+secret_id+'/access/'+grant,'DELETE');check('grant revoked',code==204)
        code,_=call(viewer,'/api/analyses/'+saved);check('revocation blocks saved excerpts',code==404)
        code,p=call(viewer,'/api/analysis','POST',{'question':'What does the sapphire ledger policy say?'});check('revocation blocks new RAG',not any(s.get('id')==secret_id for s in p['data']['sources']))
        other_token=login('other-'+run+'@example.test',password)
        for path in ['/api/documents/'+documents[0],'/api/documents/'+secret_id+'/access','/api/analyses/'+results[0]['meta']['requestId']]:
            code,_=call(other_token,path);check('cross-org denial '+path.split('/')[2],code==404)
        code,p=call(other_token,'/api/analytics/revenue');check('cross-org structured isolation',code==200 and p['data']==[])
        code,p=call(other_token,'/api/search','POST',{'question':'internal expense receipts'});check('cross-org vector isolation',code==200 and p['data']['results']==[])
        code,_=call(token,'/api/documents/'+secret_id+'/access','POST',{'userId':str(conn.execute('SELECT id FROM users WHERE org_id=%s',(other,)).fetchone()[0])});check('cross-org grant rejected',code==404)
        # Dependency failures tested without stopping the shared production Ollama service.
        internal=smoke.local_env('AI_INTERNAL_TOKEN')
        with httpx.Client(timeout=30) as c:
            r=c.post(BASE+'/api/auth/refresh');check('missing refresh rejected',r.status_code==401)
        code,_=call(token,'/api/users/'+viewer_id,'DELETE');check('user disabled',code==204)
        code,_=call(viewer,'/api/analytics/revenue');check('disabled bearer rejected',code==401)
        # Login sets a cookie in smoke.OPENER; logout must invalidate both credentials.
        other_token=login('other-'+run+'@example.test',password)
        old_cookie=next(c.value for c in smoke.COOKIE_JAR if c.name=='pbi_refresh')
        code,p=smoke.request('/api/auth/refresh','POST');check('refresh rotates',code==200)
        rotated=p['data']['accessToken']
        with httpx.Client(timeout=30) as client:
            replay=client.post(BASE+'/api/auth/refresh',headers={'Cookie':'pbi_refresh='+old_cookie})
            check('refresh replay rejected',replay.status_code==401 and replay.json()['error']['code']=='SESSION_REPLAYED')
        code,_=call(rotated,'/api/analytics/revenue');check('refresh replay revokes bearer family',code==401)
        code,_=smoke.request('/api/auth/refresh','POST');check('refresh replay revokes rotated cookie',code==401)
        other_token=login('other-'+run+'@example.test',password)
        code,_=smoke.request('/api/auth/logout','POST');check('logout succeeds',code==204)
        code,_=call(other_token,'/api/analytics/revenue');check('logout revokes bearer family',code==401)
        code,_=smoke.request('/api/auth/refresh','POST');check('logout revokes refresh',code==401)
        check('internal token configured',bool(internal))
        output={'syntheticOrganisationId':org,'isolationOrganisationId':other,'checksPassed':len(checks),'questions':[{'question':q,'result':r['data']} for q,r in zip(questions,results)]}
        (ROOT/'docs/audit-results.json').write_text(json.dumps(output,indent=2)+'\n')
        print(json.dumps({'checksPassed':len(checks),'syntheticOrganisationId':org}),flush=True)


if __name__=='__main__':
    started=time.perf_counter()
    main()
    print(f'Elapsed {time.perf_counter()-started:.1f}s')
