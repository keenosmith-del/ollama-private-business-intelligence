"""Run a second runtime with intentionally missing models against real Ollama.
Does not stop or reconfigure the shared Compose services.
"""
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

import httpx
import psycopg

ROOT=Path(__file__).resolve().parents[1]
local=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
DB=f"postgresql://pbi:pbi-local-only@localhost:{local.get('POSTGRES_PORT','5433')}/pbi"
with psycopg.connect(DB) as conn:
    org,user=conn.execute("SELECT u.org_id,u.id FROM users u JOIN organisations o ON o.id=u.org_id WHERE o.name LIKE 'SYNTHETIC COMPLETION AUDIT %' ORDER BY o.created_at DESC LIMIT 1").fetchone()
internal=local['AI_INTERNAL_TOKEN'].strip('"\'')
headers={'x-internal-token':internal,'x-org-id':str(org),'x-user-id':str(user),'x-role':'admin'}
checks=[]


def run(generation, embedding, action):
    env={**os.environ,'DATABASE_URL':DB,'AI_INTERNAL_TOKEN':internal,'OLLAMA_BASE_URL':'http://localhost:11434','OLLAMA_MODEL':generation,'OLLAMA_EMBEDDING_MODEL':embedding}
    proc=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'],cwd=ROOT/'ai-runtime',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(timeout=240) as client:
            for _ in range(100):
                try:
                    if client.get('http://localhost:8001/health').status_code==200:break
                except httpx.ConnectError:pass
                time.sleep(.1)
            else:raise AssertionError('Runtime did not start')
            action(client)
    finally:
        proc.terminate();proc.wait(timeout=10)


def missing_generation(client):
    r=client.get('http://localhost:8001/health/ready');assert r.status_code==503 and r.json()['models']['generationAvailable'] is False;checks.append('missing generation readiness')
    r=client.post('http://localhost:8001/v1/analysis',headers=headers,json={'question':'Why did revenue decline in Q2?'})
    p=r.json();assert r.status_code==200 and not p['inferenceUsed'] and p['metrics'] and any('inference is unavailable' in w for w in p['warnings']);checks.append('missing generation returns actual evidence without claiming inference')
    r=client.post('http://localhost:8001/v1/search',json={'question':'expense policy'},headers={'x-org-id':str(org)});assert r.status_code==401;checks.append('direct runtime missing internal credential denied')


def missing_embedding(client):
    r=client.get('http://localhost:8001/health/ready');assert r.status_code==503 and r.json()['models']['embeddingAvailable'] is False;checks.append('missing embedding readiness')
    raw=('SYNTHETIC MODEL FAILURE '+secrets.token_hex(6)+' expense receipts.').encode()
    r=client.post('http://localhost:8001/v1/documents/ingest',headers=headers,json={'filename':'synthetic-model-failure.txt','mimeType':'text/plain','content':base64.b64encode(raw).decode()})
    assert r.status_code==503 and r.json()['detail']['code']=='EMBEDDING_UNAVAILABLE';document=r.json()['detail']['documentId']
    with psycopg.connect(DB) as conn:
        assert conn.execute('SELECT status,error_code FROM documents WHERE id=%s',(document,)).fetchone()==('failed','EMBEDDING_UNAVAILABLE')
    checks.append('missing embedding failure persists inspectable status')
    # Retry through the normal model configuration, retaining the original bytes.
    return document


if __name__=='__main__':
    run('synthetic-missing-generation:never','nomic-embed-text',missing_generation)
    documents=[]
    run('qwen2.5:1.5b','synthetic-missing-embedding:never',lambda c:documents.append(missing_embedding(c)))
    def recover(client):
        r=client.post('http://localhost:8001/v1/documents/'+documents[0]+'/retry',headers=headers);assert r.status_code==200 and r.json()['status']=='ready';checks.append('real model recovery retry indexes retained bytes')
    run('qwen2.5:1.5b','nomic-embed-text',recover)
    print(json.dumps({'checksPassed':len(checks),'checks':checks}))
