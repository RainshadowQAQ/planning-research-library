import hashlib
import re
from pathlib import Path
import pytest
from pypdf import PdfReader
from app.site_facts import load_sample,resolve_sample

FIXTURES=Path(__file__).resolve().parent.parent/'docs/research/2026-09-05-api-feasibility'
FILES={'P':'main-paper.pdf','M':'minutes-705-en.pdf','D':'perm-detail.json'}

def claims():return {c['id']:c for c in load_sample()['claims']}
def norm(text):return re.sub(r'\s+','',text.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')).lower()

def test_sample_has_21_claims_seven_questions_and_nine_issues():
    data=load_sample()
    assert len(data['claims'])==21 and len(claims())==21
    assert [q['id'] for q in data['questions']]==['identity','use','scale','meaning','planning','history','unknowns']
    assert len(data['issues'])==9
    for c in data['claims']:
        assert c['citations'],c['id']
        for key in ['time','nature','scope','review_status']:assert c[key],(c['id'],key)

def test_only_user_confirmed_fields_are_marked_confirmed():
    confirmed={i for i,c in claims().items() if c['review_status']!='pending'}
    assert confirmed=={'site-area','original-expiry'}
    assert claims()['site-area']['review_status']=='user_confirmed_source_value'

def test_application_pr_is_not_a_planning_limit():
    pr=claims()['pr-application']
    assert pr['value'].startswith('約 1.41') and pr['nature']=='application_proposal'
    assert 'ozp-notes-pr-limit' in pr['issue_ids']
    assert any(i['id']=='ozp-notes-pr-limit' for i in load_sample()['issues'])

def test_sources_keep_approximations_and_open_eot_state():
    c=claims()
    assert c['site-area']['value']=='約 5,410' and c['site-area']['approximation']=='approximate'
    assert c['gfa-nondomestic']['value'].startswith('約 7,638')
    assert '未核實' in c['original-expiry']['value'] and '2026-10-14' in c['original-expiry']['value']
    roof=c['government-land-roof']['value']
    assert all(word in roof for word in ['FSI','LCSD','不屬本申請','未確定'])

def test_committed_snapshots_match_frozen_hashes():
    data=load_sample()
    for code,name in FILES.items():
        assert hashlib.sha256((FIXTURES/name).read_bytes()).hexdigest()==data['sources'][code]['sha256']

@pytest.fixture(scope='module')
def pages():
    return {code:[norm(p.extract_text() or '') for p in PdfReader(FIXTURES/name).pages] for code,name in FILES.items() if name.endswith('.pdf')}

def test_every_committed_pdf_excerpt_is_unique_on_its_cited_page(pages):
    data=load_sample()
    for row in [*data['claims'],*data['interpretations']]:
        for c in row['citations']:
            if c['source'] not in pages or not c['excerpt']:continue
            text=pages[c['source']][c['page']-1]
            assert text.count(norm(c['excerpt']))==1,(row['id'],c['source'],c['page'],c['excerpt'])

def test_json_citations_have_paths_but_no_page():
    for row in load_sample()['claims']:
        for c in row['citations']:
            if c['source']=='D':assert c['json_path'] and c['page'] is None

def first(view,claim='site-area',index=0):
    return next(x for x in resolve_sample(view)['claims'] if x['id']==claim)['citations'][index]

def saved(citation,**extra):
    return {'id':'doc','source_run':'run-1','status':'ready','sha256':citation['source_sha256'],'url':citation['source_url'],**extra}

def test_missing_saved_pdf_cannot_become_navigation_target():
    c=first({'case_no':'A/K1/265','documents':[]})
    assert c['availability']=='missing_original' and c['doc_id'] is None

def g():
    s=load_sample()['sources']['G'];return {'source_sha256':s['sha256'],'source_url':s['url']}

def test_exact_hash_match_is_navigable():
    c=first({'case_no':'A/K1/265','documents':[saved(g())]})
    assert c['availability']=='ready' and c['doc_id']=='doc' and c['source_run']=='run-1' and c['warnings']==[]

def test_same_bytes_with_changed_url_remain_navigable():
    doc=saved(g());doc['url']+='&new-query=1'
    c=first({'case_no':'A/K1/265','documents':[doc]})
    assert c['availability']=='ready' and c['warnings']==['source_url_changed']

def test_same_bytes_without_saved_url_remain_navigable():
    doc=saved(g());del doc['url']
    c=first({'case_no':'A/K1/265','documents':[doc]})
    assert c['availability']=='ready' and c['warnings']==['source_url_missing']

def test_older_version_in_versions_list_is_found():
    display={'id':'doc','source_run':'run-2','status':'ready','sha256':'new','url':g()['source_url'],'versions':[saved(g())]}
    c=first({'case_no':'A/K1/265','documents':[display]})
    assert c['availability']=='ready' and c['source_run']=='run-1'

def test_changed_bytes_from_same_url_are_a_version_mismatch():
    doc=saved(g());doc['sha256']='0'*64
    c=first({'case_no':'A/K1/265','documents':[doc]})
    assert c['availability']=='version_mismatch' and c['doc_id'] is None

def test_hidden_by_scope_is_reported_separately():
    c=next(x for x in resolve_sample({'case_no':'A/K1/265','documents':[]},[saved(g())])['claims'] if x['id']=='site-area')['citations'][0]
    assert c['availability']=='outside_scope' and c['doc_id'] is None

def test_pending_or_failed_download_is_not_a_target():
    doc=saved(g());doc['status']='error'
    assert first({'case_no':'A/K1/265','documents':[doc]})['availability']=='missing_original'

def test_json_source_is_never_a_pdf_target():
    c=first({'case_no':'A/K1/265','documents':[]},index=1)
    assert c['availability']=='not_pdf' and c['json_path']=='Data[0].subj[0].planArea'

def test_other_case_is_rejected():
    with pytest.raises(KeyError):resolve_sample({'case_no':'A/K1/265-1','documents':[]})
