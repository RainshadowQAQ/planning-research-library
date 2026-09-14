import hashlib,json
import pytest
from app.store import Store
from app.library import Library
from app.migrate import migrate,TEST_IDS

def legacy(root):
    s=Store(root)
    for i,case in enumerate(['A/K1/265','A/K1/265','A/H7/183']):
        p=s.create(case,str(i),'2022-08-01' if i==1 else '2026-09-08')
        if i==2:
            with s.connect() as db:db.execute('DELETE FROM projects WHERE id=?',(p['id'],))
            p['id']=next(iter(TEST_IDS))
        body=b'%PDF-test';p['phase']='complete'
        p['documents']=[dict(id='d',url='https://www.tpb.gov.hk/a.pdf',title='paper',status='ready',path=s.content(body),sha256=hashlib.sha256(body).hexdigest())]
        s.save(p)
    return s

def test_migration_preserves_and_isolates(tmp_path):
    s=legacy(tmp_path/'old');before=s.list()
    report=migrate(s.root,tmp_path/'daily',tmp_path/'test')
    assert s.list()==before
    lib=Library(Store(tmp_path/'daily'));assert len(lib.folders())==1
    assert len(lib.view(lib.folders()[0]['id'])['runs'])==2
    assert Library(Store(tmp_path/'test')).folders()[0]['case_no']=='A/H7/183'
    assert migrate(s.root,tmp_path/'daily',tmp_path/'test')==report

def test_bad_hash_does_not_activate(tmp_path):
    s=legacy(tmp_path/'old');p=s.list()[0];s.file(p['documents'][0]).write_bytes(b'broken')
    with pytest.raises(ValueError,match='哈希'):migrate(s.root,tmp_path/'daily',tmp_path/'test')
    assert not (tmp_path/'daily').exists()
    assert s.db.exists()
