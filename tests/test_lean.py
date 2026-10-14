import copy
from datetime import date
from app.lean import preliminary_lean
from app.site_facts import load_sample
from tests.test_site_fact_api import client,seed

PRECEDENTS=dict(status='ready',summary=dict(approved=1,rejected=0,other=0),groups=[
    dict(kind='previous',items=[],statements=[]),
    dict(kind='similar',statements=[],items=[dict(case_no='A/K1/250',page=4,citation=dict(page=4,excerpt='x',doc_id='d'))])])

def finding(result,check):
    return next(f for g in result['groups'] for f in g['findings'] if f['check']==check)

def close(facts,*ids):
    for i in facts['issues']:
        if i['id'] in ids:i['status']='resolved'
    return facts

def test_open_permission_issue_blocks_the_lean():
    result=preliminary_lean(load_sample(),PRECEDENTS,date(2026,10,13))
    assert result['lean']['value']=='insufficient' and 'C4' in result['lean']['reason']
    c4=finding(result,'C4')
    assert (c4['outcome'],c4['severity'])==('cannot_assess','blocker') and '尚餘 1 日' in c4['text']
    assert c4['basis']==['original-expiry'] and c4['citations'][0]['page']==12

def test_findings_follow_rules_and_cite_sources():
    result=preliminary_lean(load_sample(),PRECEDENTS,date(2026,10,13))
    c1=finding(result,'C1')
    assert (c1['outcome'],c1['severity'],c1['provisional'])==('limit','major',True)
    assert all(c['label'] and c['excerpt'] for c in c1['citations'])
    assert finding(result,'C3')['outcome']=='planner'
    assert finding(result,'C6')['outcome']=='support' and finding(result,'C6')['citations'][0]['label']=='主文件 · p.4'
    assert {finding(result,c)['outcome'] for c in ('C2','C5','C7')}=={'cannot_assess'}
    assert [g['label'] for g in result['groups']][0]=='用途是否允許？'
    assert result['unknowns']['items'][0]['priority']==1

def test_counts_decide_direction_once_blockers_close():
    facts=close(load_sample(),'permission-status-eot')
    # C4 in period + C6 approvals vs C1 needing s.16.
    lean=preliminary_lean(facts,PRECEDENTS,date(2026,10,13))['lean']
    assert lean['value']=='optimistic' and lean['provisional'] and '支持 2（' in lean['reason']
    # A tie is not forced into a direction.
    split=copy.deepcopy(PRECEDENTS);split['summary']=dict(approved=1,rejected=1,other=0)
    assert preliminary_lean(facts,split,date(2026,10,13))['lean']['value']=='insufficient'
    rejected=copy.deepcopy(PRECEDENTS);rejected['summary']=dict(approved=0,rejected=2,other=0)
    assert preliminary_lean(facts,rejected,date(2026,11,1))['lean']['value']=='pessimistic'

def test_expired_permission_without_open_issue_is_a_limit():
    facts=close(load_sample(),'permission-status-eot')
    c4=finding(preliminary_lean(facts,PRECEDENTS,date(2026,11,1)),'C4')
    assert (c4['outcome'],c4['text'].count('已過期 18 日'))==('limit',1)

def test_lean_api_uses_saved_paper(client):
    fid,_=seed(client)
    r=client.get(f'/api/folders/{fid}/lean?as_of=2026-10-13');assert r.status_code==200
    data=r.json()
    assert data['lean']['label']=='證據不足' and data['as_of']=='2026-10-13'
    c6=finding(data,'C6')
    assert c6['outcome']=='support' and c6['citations'][0]['availability']=='ready'
    assert finding(data,'C4')['citations'][0]['availability']=='missing_original'  # minutes not saved here
    assert '"path"' not in r.text
    fid,_=seed(client,case='A/H7/183')
    assert client.get(f'/api/folders/{fid}/lean').status_code==404
