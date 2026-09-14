import copy
from app.store import Store
from app.library import Library

def test_same_case_one_folder(tmp_path):
    s=Store(tmp_path);a=s.create('A/K1/265','one','2026-09-08');b=s.create('A/K1/265','two','2022-08-01')
    lib=Library(s);fid=lib.import_run(a);assert lib.import_run(b)==fid
    assert len(lib.folders())==1
    assert len(lib.view(fid)['runs'])==2
    c=s.create('A/K1/265-1','','2026-09-08');lib.import_run(c)
    assert len(lib.folders())==2

def test_frozen_versions_and_cutoff(tmp_path):
    s=Store(tmp_path);lib=Library(s)
    a=s.create('A/K1/265','old','2026-09-08');a['phase']='complete'
    a['documents']=[dict(id='d',url='https://www.tpb.gov.hk/a.pdf',status='ready',sha256='old',kind='會議文件',event_date='2022-07-15'),dict(id='g',url='https://www.tpb.gov.hk/g.pdf',status='ready',sha256='g',kind='Gist',event_date=None)]
    s.save(a);fid=lib.import_run(a)
    b=lib.begin(fid,'new','2026-09-09');b['documents']=copy.deepcopy(a['documents']);b['documents'][0]['sha256']='new';b['phase']='complete';s.save(b);lib.finish(b['id'])
    assert lib.view(fid,run_id=a['id'])['documents'][0]['sha256']=='old'
    assert lib.view(fid)['documents'][0]['sha256']=='new'
    assert len(lib.view(fid,cutoff='2022-08-01')['documents'])==1
    a['question']='mutated';s.save(a)
    assert lib.view(fid,run_id=a['id'])['question']=='old'

def test_state_separate_from_runs(tmp_path):
    lib=Library(Store(tmp_path));lib.set_state('reader:x',{'page':4,'offset':.3})
    assert lib.get_state('reader:x')['page']==4


def test_cutoff_filters_versions_before_choosing(tmp_path):
    s=Store(tmp_path);lib=Library(s)
    a=s.create('A/K1/265','','2026-09-08');a['phase']='complete'
    a['documents']=[dict(id='d',url='https://www.tpb.gov.hk/a.pdf',status='ready',sha256='old',event_date='2022-07-15')]
    s.save(a);fid=lib.import_run(a)
    b=lib.begin(fid,'','2026-09-09');b['phase']='complete';b['documents']=copy.deepcopy(a['documents']);b['documents'][0].update(sha256='new',event_date='2022-10-14');s.save(b);lib.finish(b['id'])
    docs=lib.view(fid,cutoff='2022-08-01')['documents']
    assert [d['sha256'] for d in docs]==['old']
    assert [v['sha256'] for v in docs[0]['versions']]==['old']
