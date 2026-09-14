import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path),base_url='http://localhost') as c:yield c

def test_duplicate_does_not_schedule(client):
    lib=client.app.state.library;p=lib.store.create('A/K1/265','','2026-09-08');p['phase']='complete';lib.store.save(p);fid=lib.import_run(p)
    class NoNetwork:
        def run(self,*a,**kw):raise AssertionError('unexpected search')
    client.app.state.service=NoNetwork()
    assert client.post('/api/folders',json={'case_no':'a/k1/265'}).json()=={'id':fid,'created':False}
    assert len(lib.view(fid)['runs'])==1

def test_state(client):
    assert client.post('/api/state/library',json={'value':{'folder':'x'}}).status_code==200
    assert client.get('/api/state/library').json()=={'folder':'x'}
    assert client.post('/api/state/library',json={'value':{'large':'x'*40000}}).status_code==422

def test_run_ownership_and_scope(client):
    lib=client.app.state.library
    a=lib.store.create('A/K1/265','','2026-09-08');a['phase']='complete';fid=lib.import_run(a)
    b=lib.store.create('A/H7/183','','2026-09-08');b['phase']='complete';lib.import_run(b)
    assert client.get(f'/api/folders/{fid}?run={b["id"]}').status_code==404
    assert client.get(f'/api/folders/{fid}?cutoff=no').status_code==422
    assert client.get(f'/api/folders/{fid}?cutoff=20220801').status_code==422
    assert client.get(f'/api/folders/{fid}?run={a["id"]}&cutoff=2022-08-01').status_code==422

def test_nested_paths_not_exposed(client):
    lib=client.app.state.library;p=lib.store.create('A/K1/265','','2026-09-08');p['phase']='complete'
    p['documents']=[dict(id='x',title='x',status='ready',sha256='a',path='files/x',url='https://www.tpb.gov.hk/x.pdf')];fid=lib.import_run(p)
    text=client.get('/api/folders/'+fid).text
    assert 'files/x' not in text

def test_legacy_creates_child_run(client):
    lib=client.app.state.library;p=lib.store.create('A/K1/265','old','2026-09-08');p['phase']='complete';lib.store.save(p);fid=lib.import_run(p)
    class Finish:
        def run(self,id,**kw):
            item=lib.store.get(id);item['question']='new';item['phase']='complete';lib.store.save(item)
    client.app.state.service=Finish()
    r=client.post('/api/projects/'+p['id']+'/resume',json={})
    assert r.status_code==202
    assert r.json()['id']!=p['id']
    assert lib.view(fid,run_id=p['id'])['question']=='old'
    assert len(lib.view(fid)['runs'])==2


def test_rejected_legacy_run_does_not_block_folder(client):
    import threading, time
    entered=threading.Event();release=threading.Event()
    lib=client.app.state.library
    class Slow:
        def run(self,id,**kw):
            entered.set();release.wait(3)
            item=lib.store.get(id);item['phase']='complete';lib.store.save(item)
    client.app.state.service=Slow()
    try:
        first=client.post('/api/projects',json={'case_no':'A/K1/265'})
        assert first.status_code==202 and entered.wait(1)
        assert client.post('/api/projects',json={'case_no':'A/K1/265'}).status_code==409
        fid=lib.find('A/K1/265')
        assert lib.view(fid)['runs'][0]['phase']=='failed'
    finally:release.set()
    for _ in range(100):
        if all(p['phase'] not in ('queued','searching','collecting') for p,_ in lib.snapshots(fid)):break
        time.sleep(.01)
    assert client.post(f'/api/folders/{fid}/collect',json={}).status_code==202
