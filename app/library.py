"""Application folders, immutable retrieval snapshots, and independent reading state."""
import copy
import json
import uuid
from app.domain import normalize_case,now

ACTIVE={'queued','searching','collecting'}

class Library:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS folders(id TEXT PRIMARY KEY,case_no TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,folder_id TEXT NOT NULL,snapshot TEXT,created TEXT NOT NULL,parent TEXT);
            CREATE TABLE IF NOT EXISTS ui_state(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')

    def folder(self,case):
        case=normalize_case(case)
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO folders VALUES (?,?)',(uuid.uuid4().hex,case))
            return db.execute('SELECT id FROM folders WHERE case_no=?',(case,)).fetchone()[0]

    def find(self,case):
        with self.store.connect() as db:
            row=db.execute('SELECT id FROM folders WHERE case_no=?',(normalize_case(case),)).fetchone()
            return row[0] if row else None

    def resolve(self,id):
        with self.store.connect() as db:
            if db.execute('SELECT 1 FROM folders WHERE id=?',(id,)).fetchone():return id
            row=db.execute('SELECT folder_id FROM runs WHERE id=?',(id,)).fetchone()
            if row:return row[0]
        raise KeyError(id)

    def import_run(self,p,parent=None):
        fid=self.folder(p['case_no'])
        snapshot=None if p['phase'] in ACTIVE else json.dumps(p,ensure_ascii=False)
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO runs VALUES(?,?,?,?,?)',(p['id'],fid,snapshot,p['created_at'],parent))
        return fid

    def begin(self,fid,question,cutoff,parent=None):
        fid=self.resolve(fid)
        with self.store.connect() as db:case=db.execute('SELECT case_no FROM folders WHERE id=?',(fid,)).fetchone()[0]
        p=self.store.create(case,question,cutoff);self.import_run(p,parent);return p

    def finish(self,id):
        p=self.store.get(id)
        with self.store.connect() as db:
            db.execute('UPDATE runs SET snapshot=? WHERE id=? AND snapshot IS NULL',(json.dumps(p,ensure_ascii=False),id))

    def snapshots(self,fid):
        fid=self.resolve(fid)
        with self.store.connect() as db:
            rows=db.execute('SELECT id,snapshot,parent FROM runs WHERE folder_id=? ORDER BY created,rowid',(fid,)).fetchall()
        return [(json.loads(snap) if snap else self.store.get(id),parent) for id,snap,parent in rows]

    def folders(self):
        with self.store.connect() as db:rows=db.execute('SELECT id,case_no FROM folders ORDER BY case_no').fetchall()
        result=[]
        for fid,case in rows:
            ps=self.snapshots(fid);last=ps[-1][0] if ps else {}
            result.append(dict(id=fid,case_no=case,phase=last.get('phase','empty'),updated_at=last.get('updated_at'),run_count=len(ps)))
        return result

    def view(self,fid,run_id=None,cutoff=None):
        fid=self.resolve(fid);pairs=self.snapshots(fid)
        if not pairs:raise KeyError(fid)
        all_ps=[p for p,_ in pairs]
        selected=next((p for p in all_ps if p['id']==run_id),None) if run_id else None
        if run_id and selected is None:raise KeyError(run_id)
        ps=[selected] if selected else all_ps
        result=copy.deepcopy(ps[-1]);result['id']=fid;result['run_id']=ps[-1]['id']
        result['runs']=[dict(id=p['id'],created_at=p['created_at'],cutoff=p['cutoff'],question=p['question'],phase=p['phase'],parent=parent,legacy=p.get('legacy_import',False)) for p,parent in reversed(pairs)]
        result['scope']=dict(run=run_id,cutoff=cutoff)
        result['live_phase']=all_ps[-1]['phase'];result['live_run_id']=all_ps[-1]['id']
        # Dates/sources belong to each version; never overwrite older run dictionaries.
        versions={};chosen={};events={};application=None;omitted=[]
        for p in ps:
            if p.get('application'):application=p['application']
            for e in p.get('events',[]):events[(e.get('authTypeCode'),str(e.get('meetNo')),e.get('event_date'))]=e
            for original in p['documents']:
                d=copy.deepcopy(original);d['source_run']=p['id']
                if cutoff and (not d.get('event_date') or d['event_date']>cutoff):
                    omitted.append(d);continue
                key=d.get('url') or d['id']
                if d['status']=='ready':
                    candidates=versions.setdefault(key,[])
                    if not any(v.get('sha256')==d.get('sha256') for v in candidates):candidates.append(copy.deepcopy(d))
                if key not in chosen or d['status']=='ready' or chosen[key]['status']!='ready':chosen[key]=d
        docs=list(chosen.values())
        for d in docs:d['versions']=versions.get(d.get('url') or d['id'],[])
        result['documents']=docs;result['application']=copy.deepcopy(application)
        result['events']=[e for e in events.values() if not cutoff or e.get('event_date','9999')<=cutoff]
        if cutoff:
            result['issues']=[f"{d.get('title',d['id'])}：未確認歷史日期，未納入。" for d in omitted if not d.get('event_date')]
        if not run_id and not cutoff:
            broad=max(enumerate(all_ps),key=lambda pair:(pair[1]['cutoff'],pair[0]))[1]
            result['issues']=copy.deepcopy(broad.get('issues',[]))
        result['issues']=list(dict.fromkeys(result.get('issues',[])))
        return result

    def get_state(self,key):
        with self.store.connect() as db:row=db.execute('SELECT value FROM ui_state WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else {}

    def set_state(self,key,value):
        with self.store.connect() as db:db.execute('INSERT INTO ui_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))
