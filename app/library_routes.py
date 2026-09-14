"""Folder API, immutable view downloads and independent UI state."""
import copy
import json
import re
import tempfile
import threading
import zipfile
from datetime import date
from pathlib import Path
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from starlette.background import BackgroundTask
from app.domain import today,normalize_case
from app.library import ACTIVE

class StateInput(BaseModel):
    value:dict

class CollectInput(BaseModel):
    question:str=Field(default='',max_length=2000)
    cutoff:date=Field(default_factory=lambda:date.fromisoformat(today()))
    parent:str|None=None
    candidate_index:int|None=Field(default=None,ge=0)
    retry_file:str|None=None

def attach_library_routes(app,lib,schedule,ProjectInput,public):
    router=APIRouter();lock=threading.Lock()
    def view(id,run=None,cutoff=None):
        if run and cutoff:raise HTTPException(422,'請選擇日期或檢索記錄其中一項')
        if cutoff:
            try:
                parsed=date.fromisoformat(cutoff)
                if parsed.isoformat()!=cutoff or parsed>date.fromisoformat(today()):raise ValueError()
            except ValueError:raise HTTPException(422,'日期不正確')
        try:return lib.view(id,run,cutoff)
        except KeyError:raise HTTPException(404,'找不到資料夾或檢索記錄')

    @router.get('/api/folders')
    def folders():return lib.folders()

    @router.post('/api/folders',status_code=202)
    def create(value:ProjectInput):
        with lock:
            fid=lib.find(value.case_no)
            if fid:return {'id':fid,'created':False}
            p=lib.store.create(value.case_no,value.question,value.cutoff.isoformat());fid=lib.import_run(p)
            try:schedule(p['id'])
            except HTTPException:
                p['phase']='interrupted';p['error']='尚未排程，請更新資料';lib.store.save(p);lib.finish(p['id']);raise
            return {'id':fid,'created':True}

    @router.get('/api/folders/{id}')
    def folder(id:str,run:str|None=None,cutoff:str|None=None):return public(view(id,run,cutoff))

    @router.post('/api/folders/{id}/collect',status_code=202)
    def collect(id:str,value:CollectInput):
        if value.cutoff>date.fromisoformat(today()):raise HTTPException(422,'截止日期不能晚於今天')
        with lock:
            current=view(id)
            if current['live_phase'] in ACTIVE:raise HTTPException(409,'此資料夾正在搜集')
            kwargs={};source=None
            if value.parent:
                source=view(id,value.parent)
                if value.candidate_index is not None:
                    candidates=source['candidates']
                    if value.candidate_index>=len(candidates) or normalize_case(candidates[value.candidate_index]['caseNo'])!=current['case_no']:
                        raise HTTPException(422,'請以完整編號另建資料夾')
                    kwargs['selection']=value.candidate_index
                if value.retry_file:
                    d=next((d for d in source['documents'] if d['id']==value.retry_file),None)
                    if not d or d['status']=='ready':raise HTTPException(422,'請選擇失敗文件')
                    kwargs['retry_file']=value.retry_file
            elif value.candidate_index is not None or value.retry_file:raise HTTPException(422,'缺少原檢索記錄')
            p=lib.begin(id,value.question,value.cutoff.isoformat(),value.parent)
            if source:
                # Copy only original research fields, not aggregate view metadata.
                raw=next(p0 for p0,_ in lib.snapshots(id) if p0['id']==value.parent)
                if kwargs:
                    for key in ['documents','application','events','related','candidates','issues','selected_candidate']:
                        if key in raw:p[key]=copy.deepcopy(raw[key])
                    p['cutoff']=raw['cutoff'];p['question']=raw['question']
                    lib.store.save(p)
            try:schedule(p['id'],**kwargs)
            except HTTPException:
                p['phase']='interrupted';p['error']='尚未排程，請更新資料';lib.store.save(p);lib.finish(p['id']);raise
            return {'id':lib.resolve(id),'run_id':p['id']}

    @router.get('/api/folders/{id}/files/{run_id}/{docid}')
    def file(id:str,run_id:str,docid:str):
        p=view(id,run_id);d=next((d for d in p['documents'] if d['id']==docid and d['status']=='ready'),None)
        if not d:raise HTTPException(404,'文件未取得')
        try:path=lib.store.file(d)
        except FileNotFoundError:raise HTTPException(404,'本地文件不存在')
        return FileResponse(path,media_type='application/pdf',headers={'Content-Disposition':'inline'})

    @router.get('/api/folders/{id}/archive')
    def archive(id:str,run:str|None=None,cutoff:str|None=None):
        p=view(id,run,cutoff);docs=[d for d in p['documents'] if d['status']=='ready']
        if not docs:raise HTTPException(409,'尚無可下載文件')
        with tempfile.NamedTemporaryFile(suffix='.zip',delete=False) as f:path=Path(f.name)
        safe=re.sub(r'[^A-Z0-9_-]','_',p['case_no'])
        try:
            with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
                for d in docs:
                    label=re.sub(r'[^\w-]','_',d['title'])[:90]
                    z.write(lib.store.file(d),f"{safe}/{d['kind']}/{d.get('event_date') or 'undated'}_{label}_{d['id']}.pdf")
        except Exception:
            path.unlink(missing_ok=True);raise HTTPException(409,'本地文件缺失，請重新搜集')
        return FileResponse(path,filename=safe+'.zip',media_type='application/zip',background=BackgroundTask(path.unlink,missing_ok=True))

    @router.get('/api/state/{key}')
    def get_state(key:str):return lib.get_state(key)

    @router.post('/api/state/{key}')
    def set_state(key:str,value:StateInput):
        if len(key)>256 or len(json.dumps(value.value))>32000:raise HTTPException(422,'閱讀狀態過大')
        lib.set_state(key,value.value);return value.value

    @router.get('/api/environment')
    def environment():return {'test':app.state.test_mode}
    app.include_router(router)
