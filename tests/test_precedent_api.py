from tests.test_site_fact_api import client,seed,FIXTURES

def test_precedents_from_saved_main_paper(client):
    fid,run=seed(client)
    other=client.app.state.library.folder('A/K1/250')
    r=client.get(f'/api/folders/{fid}/precedents');assert r.status_code==200
    data=r.json()
    assert data['status']=='ready' and data['source']['source_run']==run['id']
    previous,similar=data['groups']
    assert previous['items']==[] and previous['statements'][0]['page']==4
    [item]=similar['items']
    assert (item['case_no'],item['decision'],item['decision_date'],item['folder_id'])==('A/K1/250','approved_with_conditions','2015-08-21',other)
    c=item['citation']
    assert c['page']==4 and c['source_sha256']==data['source']['sha256'] and 'approved with conditions' in c['excerpt']
    assert client.get(f"/api/folders/{fid}/files/{c['source_run']}/{c['doc_id']}").content==(FIXTURES/'main-paper.pdf').read_bytes()
    assert data['summary']=={'approved':1,'rejected':0,'other':0}
    assert '"path"' not in r.text

def test_precedents_respect_scope_and_missing_paper(client):
    fid,_=seed(client)
    assert client.get(f'/api/folders/{fid}/precedents?cutoff=2022-01-01').json()['status']=='no_paper'
    fid,_=seed(client,case='A/H7/183',body=b'%PDF-1.4 not readable')
    assert client.get(f'/api/folders/{fid}/precedents').json()['status']=='unreadable'
    assert client.get('/api/folders/nope/precedents').status_code==404
