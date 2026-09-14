"""Durable project snapshots and immutable content-addressed originals."""
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from app.domain import now,normalize_case

class Store:
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        (self.root/'files').mkdir(exist_ok=True)
        self.db=self.root/'library.sqlite'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, updated TEXT NOT NULL, snapshot TEXT NOT NULL)')

    def connect(self):return sqlite3.connect(self.db,timeout=15)
    def save(self,project):
        project['updated_at']=now()
        with self.connect() as db:
            db.execute('INSERT INTO projects VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,snapshot=excluded.snapshot',
                       (project['id'],project['updated_at'],json.dumps(project,ensure_ascii=False)))
    def create(self,case,question,cutoff):
        p=dict(id=uuid.uuid4().hex,case_no=normalize_case(case),input_case=case,question=question,cutoff=cutoff,
               created_at=now(),phase='queued',error=None,candidates=[],application=None,related=[],events=[],documents=[],issues=[])
        self.save(p);return p
    def get(self,id):
        with self.connect() as db:row=db.execute('SELECT snapshot FROM projects WHERE id=?',(id,)).fetchone()
        if row is None:raise KeyError(id)
        return json.loads(row[0])
    def list(self):
        with self.connect() as db:rows=db.execute('SELECT snapshot FROM projects ORDER BY updated DESC').fetchall()
        return [json.loads(row[0]) for row in rows]
    def content(self,body,suffix='.pdf'):
        name=hashlib.sha256(body).hexdigest()+suffix
        target=self.root/'files'/name
        if not target.exists():
            temp=target.with_suffix('.'+uuid.uuid4().hex+'.tmp');temp.write_bytes(body);temp.replace(target)
        return str(target.relative_to(self.root))
    def file(self,document):
        path=(self.root/(document.get('path') or '')).resolve()
        if path.parent!=self.root/'files' or not path.is_file():raise FileNotFoundError('文件未儲存')
        return path
    def recover(self):
        for p in self.list():
            if p['phase'] in ('queued','searching','collecting'):
                p['phase']='interrupted';p['error']='搜集已中斷';self.save(p)
