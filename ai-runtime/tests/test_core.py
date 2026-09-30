import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import main
from app.main import chunk_text, classify, extract_text, parse_sales_csv, vector_literal
def test_chunk_text_overlaps_and_preserves_content():
    chunks=chunk_text('word '*600,size=300,overlap=40)
    assert len(chunks)>1 and all(chunks)
def test_classifier_routes_hybrid_question():
    assert classify('Why did revenue fall in Q2?')=='hybrid'
    assert classify('Which customers contributed most to the revenue decline and what does management say?')=='hybrid'
def test_classifier_separates_structured_financial_queries():
    assert classify('What are our biggest areas of financial loss?')=='analytics'
    assert classify('Which customers declined the most in Q2?')=='analytics'
def test_vector_literal_enforces_database_dimension():
    assert vector_literal([0.0]*768).startswith('[0.0,')
    with pytest.raises(ValueError): vector_literal([0.0]*3)
def test_plain_text_extraction_and_unsupported_file_rejection():
    assert extract_text('policy.txt',b'Refunds are accepted within 30 days.')==[(None,'Refunds are accepted within 30 days.')]
    with pytest.raises(HTTPException) as error: extract_text('file.exe',b'no')
    assert error.value.status_code==415
def test_sales_csv_parser_validates_and_normalizes_rows():
    rows=parse_sales_csv(b'customer,date,amount,industry\nAcme Retail,2026-09-01,1250.50,Retail\n')
    assert rows[0]['customer']=='Acme Retail' and str(rows[0]['amount'])=='1250.50'
    with pytest.raises(HTTPException) as error: parse_sales_csv(b'customer,date,amount\nAcme,not-a-date,1\n')
    assert error.value.status_code==422
    with pytest.raises(HTTPException): parse_sales_csv(b'customer,date,amount\nAcme,2026-09-01,0.001\n')
def test_ai_routes_require_gateway_token(monkeypatch):
    monkeypatch.setattr(main,'INTERNAL_TOKEN','a-test-internal-token-with-more-than-32-chars')
    response=TestClient(main.app).post('/v1/analysis',headers={'x-org-id':'org-test'},json={'question':'Why did revenue fall?'})
    assert response.status_code==401
