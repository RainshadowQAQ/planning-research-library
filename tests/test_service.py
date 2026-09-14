from pathlib import Path
import json
import pytest
from app.store import Store
from app.research import ResearchService, verify_pdf

SAMPLE=Path('docs/research/2026-09-05-api-feasibility')
class FakeClient:
    def __init__(self,root):self.calls=[]
    def close(self):pass
    def request(self,url,data=None):
        self.calls.append((url,data))
        if url.endswith('/api/Perm'):return (SAMPLE/'perm-search.json').read_bytes()
        if url.endswith('/Detail/'):return (SAMPLE/'perm-detail.json').read_bytes()
        if '/Agenda/' in url:return b'<html><table><tr><td>A/K1/265</td><td><a href="https://www.tpb.gov.hk/main.pdf">Paper</a></td></tr></table></html>'
        if url.endswith('main.pdf'):return (SAMPLE/'main-paper.pdf').read_bytes()
        if 'Minutes/' in url:return (SAMPLE/'minutes-705-en.pdf').read_bytes()
        raise RuntimeError('unavailable')

def test_store_survives_reopen(tmp_path):
    first=Store(tmp_path).create('A/K1/265','','2026-09-08')
    assert Store(tmp_path).get(first['id'])['case_no']=='A/K1/265'

def test_bad_pdf_rejected():
    with pytest.raises(ValueError):verify_pdf(b'<html>error</html>','A/K1/265')

def test_download_resume_no_duplicates(tmp_path):
    store=Store(tmp_path);p=store.create('A/K1/265','','2026-09-08')
    service=ResearchService(store,FakeClient);service.run(p['id'])
    p=store.get(p['id']);assert p['application']['caseNo']=='A/K1/265'
    assert 'A/K1/265-1' in p['related']
    assert p['phase']=='partial'
    ready=[d for d in p['documents'] if d['status']=='ready'];assert ready
    service.run(p['id'])
    second=store.get(p['id']);assert len(second['documents'])==len(p['documents'])
    assert [d['sha256'] for d in second['documents'] if d['status']=='ready']==[d['sha256'] for d in ready]

def test_ambiguous_pauses(tmp_path):
    class Ambiguous(FakeClient):
        def request(self,url,data=None):
            assert url.endswith('/api/Perm')
            return json.dumps({'IsSuccess':True,'Data':[{'caseNo':'A/K1/265','planNo':'one'},{'caseNo':'A/K1/265','planNo':'two'}]}).encode()
    store=Store(tmp_path);p=store.create('A/K1/265','','2026-09-08')
    ResearchService(store,Ambiguous).run(p['id'])
    assert store.get(p['id'])['phase']=='awaiting_selection'
    assert store.get(p['id'])['documents']==[]

def test_unrelated_readable_pdf_rejected():
    with pytest.raises(ValueError,match='不符'):
        verify_pdf((SAMPLE/'main-paper.pdf').read_bytes(),'A/H7/183')

def test_resume_preserves_saved_files_during_agenda_outage(tmp_path):
    store=Store(tmp_path);p=store.create('A/K1/265','','2026-09-08')
    ResearchService(store,FakeClient).run(p['id'])
    before=store.get(p['id']);ids={d['id'] for d in before['documents'] if d['status']=='ready'}
    class Outage(FakeClient):
        def request(self,url,data=None):
            if '/Agenda/' in url:raise RuntimeError('outage')
            return super().request(url,data)
    ResearchService(store,Outage).run(p['id'])
    assert ids <= {d['id'] for d in store.get(p['id'])['documents'] if d['status']=='ready'}

def test_historical_presentation_excludes_current_status(tmp_path):
    store=Store(tmp_path);p=store.create('A/K1/265','','2022-08-01')
    ResearchService(store,FakeClient).run(p['id'])
    p=store.get(p['id'])
    assert 'appDeciCode' not in p['application']
    assert 'meetDetail' not in p['application']
    assert len(p['events'])==1


def test_missing_minutes_reported_even_when_papers_exist(tmp_path):
    class NoMinutes(FakeClient):
        def request(self,url,data=None):
            body=super().request(url,data)
            if url.endswith('/Detail/'):
                payload=json.loads(body)
                for item in payload['Data']:
                    for event in item.get('meetDetail',[]):
                        event.pop('MinsLinkEN',None);event.pop('MinsLinkTC',None)
                return json.dumps(payload).encode()
            return body
    store=Store(tmp_path);p=store.create('A/K1/265','','2022-08-01')
    ResearchService(store,NoMinutes).run(p['id']);p=store.get(p['id'])
    assert any(d['status']=='ready' for d in p['documents'])
    assert p['phase']=='partial'
    assert any('會議記錄（EN）' in i for i in p['issues'])
    assert any('會議記錄（TC）' in i for i in p['issues'])


def test_minutes_fallback_uses_official_anchor_and_archive(tmp_path):
    class Pages:
        def request(self,url):
            if 'archive' in url:return b'<a href="/en/meetings/MPC/Minutes/m699mpc_e.pdf">Minutes</a><a href="/en/meetings/MPC/Minutes/m6990mpc_e.pdf">Other</a>'
            return b'<a href="mpc_meeting_archive.html">Archive</a>'
    docs=ResearchService(Store(tmp_path))._minutes_fallback(Pages(),'MPC',699,'EN','2022-07-15')
    assert len(docs)==1
    assert docs[0]['url'].endswith('/m699mpc_e.pdf')
    assert docs[0]['discovered_from'].endswith('_archive.html')


def test_pdf_spaced_characters_and_suffix_boundary(monkeypatch):
    from types import SimpleNamespace
    def reader(text):return SimpleNamespace(is_encrypted=False,pages=[SimpleNamespace(extract_text=lambda:text)])
    monkeypatch.setattr('app.research.PdfReader',lambda _:reader('A / K 1 / 2 6 5 Proposed use'))
    assert verify_pdf(b'%PDF-test','A/K1/265')['matched_pages']==[1]
    monkeypatch.setattr('app.research.PdfReader',lambda _:reader('A/K1/265-1 Proposed use'))
    with pytest.raises(ValueError):verify_pdf(b'%PDF-test','A/K1/265')


@pytest.mark.parametrize('text',['A / K 1 / 2 6 5 - 1 Proposed use','A / H 7 / 1 8 3 Proposed use'])
def test_spaced_conflicting_pdf_rejected(monkeypatch,text):
    from types import SimpleNamespace
    monkeypatch.setattr('app.research.PdfReader',lambda _:SimpleNamespace(is_encrypted=False,pages=[SimpleNamespace(extract_text=lambda:text)]))
    with pytest.raises(ValueError,match='不符'):verify_pdf(b'%PDF-test','A/K1/265')
