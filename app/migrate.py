"""Offline, staged migration. The source and full backup are never modified."""
import argparse
import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from app.store import Store
from app.library import Library,ACTIVE

TEST_IDS={'696327acba9f441cbf345cbd35109150'}

def load_legacy(source):
    with sqlite3.connect(f'file:{source / "library.sqlite"}?mode=ro',uri=True) as db:
        return [json.loads(row[0]) for row in db.execute('SELECT snapshot FROM projects')]

def migrate(source,destination,test_destination):
    source=Path(source).resolve();destination=Path(destination).resolve();test_destination=Path(test_destination).resolve()
    marker=destination/'migration.json'
    if marker.exists():
        report=json.loads(marker.read_text())
        if report['source']!=str(source) or report['test_destination']!=str(test_destination):raise ValueError('迁移目标与原记录不一致')
        if not (test_destination/'migration.json').exists():raise ValueError('测试库迁移记录缺失')
        if json.loads((test_destination/'migration.json').read_text())!=report:raise ValueError('迁移记录不一致')
        for item in report['projects']:
            target=test_destination if item['test'] else destination
            original=json.loads((target/'legacy-snapshots'/f"{item['legacy_id']}.json").read_text())
            library=Library(Store(target))
            migrated=library.view(item['folder_id'],run_id=item['legacy_id'])
            if len(migrated['documents'])!=len(original['documents']):raise ValueError('迁移文件记录不完整')
            for d in migrated['documents']:
                if d['status']=='ready' and hashlib.sha256(library.store.file(d).read_bytes()).hexdigest()!=d['sha256']:raise ValueError('迁移原件哈希不符')
        return report
    if destination.exists() or test_destination.exists():raise ValueError('目标目录已存在，拒绝覆盖')
    if destination==source or source in destination.parents or test_destination==source or source in test_destination.parents or destination==test_destination:raise ValueError('迁移目录必须独立')
    projects=load_legacy(source)
    if any(p['phase'] in ACTIVE for p in projects):raise ValueError('请先停止搜集任务和旧服务')
    backup=source.parent/('backups/legacy-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    backup.parent.mkdir(exist_ok=True);shutil.copytree(source,backup)
    stages=[p.with_name(p.name+'.staging-'+uuid.uuid4().hex[:6]) for p in [destination,test_destination]]
    report={'source':str(source),'backup':str(backup),'destination':str(destination),'test_destination':str(test_destination),'projects':[]}
    activated=[]
    try:
        stores=[Store(p) for p in stages];libs=[Library(s) for s in stores]
        for stage in stages:
            if (source/'requests').exists():shutil.copytree(source/'requests',stage/'requests')
            (stage/'legacy-snapshots').mkdir()
        for p in projects:
            index=1 if p['id'] in TEST_IDS else 0;s=stores[index]
            (stages[index]/'legacy-snapshots'/f"{p['id']}.json").write_text(json.dumps(p,ensure_ascii=False,indent=2))
            for d in p['documents']:
                if d['status']!='ready':continue
                path=(source/d['path']).resolve()
                if path.parent!=source/'files':raise ValueError('原件路径异常')
                body=path.read_bytes()
                if hashlib.sha256(body).hexdigest()!=d['sha256']:raise ValueError('原件哈希不符：'+d['id'])
                d['path']=s.content(body)
            p['legacy_import']=True
            # Preserve timestamps exactly: migration is not a new retrieval.
            with s.connect() as db:db.execute('INSERT INTO projects VALUES(?,?,?)',(p['id'],p['updated_at'],json.dumps(p,ensure_ascii=False)))
            fid=libs[index].import_run(p)
            assert s.get(p['id'])==p
            report['projects'].append({'legacy_id':p['id'],'folder_id':fid,'case_no':p['case_no'],'test':bool(index),'documents':len(p['documents'])})
        for stage in stages:(stage/'migration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        for stage,dest in zip(stages,[destination,test_destination]):stage.rename(dest);activated.append(dest)
        return report
    except Exception:
        for p in stages+activated:
            if p.exists():shutil.rmtree(p)
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('destination');parser.add_argument('test_destination')
    a=parser.parse_args();print(json.dumps(migrate(a.source,a.destination,a.test_destination),ensure_ascii=False,indent=2))
