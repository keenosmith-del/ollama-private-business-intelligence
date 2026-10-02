"""Authenticate or bootstrap the local demo admin without exposing its credentials."""
import importlib.util
from pathlib import Path
import time

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('smoke',root/'scripts/e2e-smoke.py')
smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)
password=smoke.os.getenv('PBI_E2E_PASSWORD') or smoke.local_env('PBI_E2E_PASSWORD')
if not password or len(password)<12:raise SystemExit('Set a private PBI_E2E_PASSWORD of at least 12 characters in .env.')
for attempt in range(120):
    try:
        status,_=smoke.request('/ready')
        if status==200:break
    except Exception:pass
    if attempt%15==0:print('Waiting for PostgreSQL, AI runtime and both Ollama models...',flush=True)
    time.sleep(1)
else:raise SystemExit('Readiness timed out. Check docker compose logs and pull both configured Ollama models.')
body=smoke.json_body({'email':smoke.EMAIL,'password':password})
headers={'Content-Type':'application/json'}
status,_=smoke.request('/api/auth/login','POST',body,headers)
if status!=200:
    bootstrap=smoke.local_env('BOOTSTRAP_TOKEN')
    if not bootstrap:raise SystemExit('BOOTSTRAP_TOKEN is missing from .env.')
    status,_=smoke.request('/api/auth/bootstrap','POST',smoke.json_body({'organisation':'Northstar Components Demo','email':smoke.EMAIL,'password':password}),{**headers,'x-bootstrap-token':bootstrap})
    if status not in (201,409):raise SystemExit(f'Bootstrap failed: HTTP {status}.')
    status,_=smoke.request('/api/auth/login','POST',body,headers)
    if status!=200:raise SystemExit('Existing administrator credentials do not match. Set PBI_E2E_EMAIL/PBI_E2E_PASSWORD to the existing account; no account was overwritten.')
smoke.request('/api/auth/logout','POST')
print(f'Local administrator verified: {smoke.EMAIL}. Use the configured local password to sign in.')
