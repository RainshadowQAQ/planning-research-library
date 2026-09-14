import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path),base_url='http://localhost') as c:yield c

def test_invalid_case(client):
    assert client.post('/api/projects',json={'case_no':'../x','cutoff':'2026-09-08'}).status_code==422

def test_cross_origin_rejected(client):
    assert client.post('/api/projects',headers={'origin':'https://evil.test'},json={'case_no':'A/K1/265','cutoff':'2026-09-08'}).status_code==403
    assert client.get('/api/projects',headers={'host':'evil.test'}).status_code==400

def test_zip_originals_and_file_access(client):
    store=client.app.state.store;p=store.create('A/K1/265','','2026-09-08')
    body=Path('docs/research/2026-09-05-api-feasibility/main-paper.pdf').read_bytes()
    p['documents']=[dict(id='one',kind='會議文件',title='../unsafe',language='EN',event_date='2022-10-14',status='ready',path=store.content(body),sha256=hashlib.sha256(body).hexdigest()),dict(id='two',status='error',title='failed',kind='Gist')]
    store.save(p)
    response=client.get(f"/api/projects/{p['id']}/archive");assert response.status_code==200
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        assert len(z.namelist())==1
        assert '..' not in z.namelist()[0]
        assert z.read(z.namelist()[0])==body
    assert client.get(f"/api/projects/{p['id']}/documents/one/file").content==body
    assert client.get(f"/api/projects/{p['id']}/documents/two/file").status_code==404
    assert 'path' not in client.get(f"/api/projects/{p['id']}").json()['documents'][0]

def test_recover_pending(tmp_path):
    app=create_app(tmp_path);p=app.state.store.create('A/K1/265','','2026-09-08')
    with TestClient(app,base_url='http://localhost') as c:
        assert c.get('/api/projects/'+p['id']).json()['phase']=='interrupted'
