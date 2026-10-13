import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

FIXTURES=Path(__file__).resolve().parent.parent/'docs/research/2026-09-05-api-feasibility'
PAPER_URL='https://www.tpb.gov.hk/uploads/page/meetings/MPC/A_K1_265_A/A_K1_265_A_MainPaper.pdf'

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path),base_url='http://localhost') as c:yield c

def seed(client,case='A/K1/265',cutoff='2026-09-05',body=None,url=PAPER_URL,event_date='2022-10-14'):
    lib=client.app.state.library;store=lib.store
    body=body if body is not None else (FIXTURES/'main-paper.pdf').read_bytes()
    p=store.create(case,'',cutoff);p['phase']='complete'
    p['documents']=[dict(id=hashlib.sha256(url.encode()).hexdigest()[:20],url=url,kind='會議文件',title='主文件',status='ready',
                         path=store.content(body),sha256=hashlib.sha256(body).hexdigest(),event_date=event_date)]
    store.save(p);return lib.import_run(p),p

def citation(payload,claim,index=0):
    return next(c for c in payload['claims'] if c['id']==claim)['citations'][index]

def test_citation_resolves_to_saved_version(client):
    fid,run=seed(client)
    r=client.get(f'/api/folders/{fid}/site-facts');assert r.status_code==200
    lot=citation(r.json(),'lot')
    assert lot['availability']=='ready' and lot['source_run']==run['id'] and lot['warnings']==[]
    assert client.get(f"/api/folders/{fid}/files/{lot['source_run']}/{lot['doc_id']}").content==(FIXTURES/'main-paper.pdf').read_bytes()
    # The Gist was not saved in this folder: visible gap, never a fake target.
    assert citation(r.json(),'site-area')['availability']=='missing_original'
    assert '"path"' not in r.text and 'files/' not in r.text

def test_changed_url_still_navigates_with_warning(client):
    fid,_=seed(client,url=PAPER_URL+'?v=2')
    lot=citation(client.get(f'/api/folders/{fid}/site-facts').json(),'lot')
    assert lot['availability']=='ready' and lot['warnings']==['source_url_changed']

def test_changed_bytes_never_ready(client):
    fid,_=seed(client,body=b'%PDF-1.4 different')
    lot=citation(client.get(f'/api/folders/{fid}/site-facts').json(),'lot')
    assert lot['availability']=='version_mismatch' and lot['doc_id'] is None

def test_scope_hides_versions(client):
    fid,run=seed(client)
    early=client.get(f'/api/folders/{fid}/site-facts?cutoff=2022-01-01').json()
    assert citation(early,'lot')['availability']=='outside_scope'
    scoped=client.get(f"/api/folders/{fid}/site-facts?run={run['id']}").json()
    assert citation(scoped,'lot')['availability']=='ready'
    assert client.get(f"/api/folders/{fid}/site-facts?run={run['id']}&cutoff=2022-01-01").status_code==422

def test_site_facts_are_bound_to_requested_folder(client):
    fid,_=seed(client,case='A/H7/183')
    assert client.get(f'/api/folders/{fid}/site-facts').status_code==404
    fid,_=seed(client,case='A/K1/265-1')
    assert client.get(f'/api/folders/{fid}/site-facts').status_code==404
    assert client.get('/api/folders/nope/site-facts').status_code==404

def test_get_does_not_create_runs_or_copy_files(client,tmp_path):
    fid,_=seed(client)
    before=sorted((tmp_path/'files').iterdir());runs=len(client.app.state.library.view(fid)['runs'])
    client.get(f'/api/folders/{fid}/site-facts')
    assert sorted((tmp_path/'files').iterdir())==before
    assert len(client.app.state.library.view(fid)['runs'])==runs
