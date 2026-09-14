"""Local-only HTTP boundary; no externally provided URL or path routes."""
import copy
import os
import re
import tempfile
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import urlparse,quote
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,field_validator
from starlette.background import BackgroundTask
from app.domain import normalize_case,today
from app.store import Store
from app.research import ResearchService
from app.library import Library
from app.library_routes import attach_library_routes

BASE=Path(__file__).resolve().parent.parent

class ProjectInput(BaseModel):
    case_no:str=Field(min_length=1,max_length=64)
    question:str=Field(default='',max_length=2000)
    cutoff:date=Field(default_factory=lambda:date.fromisoformat(today()))
    @field_validator('case_no')
    @classmethod
    def valid_case(cls,value):normalize_case(value);return value
    @field_validator('cutoff')
    @classmethod
    def valid_date(cls,value):
        if value>date.fromisoformat(today()):raise ValueError('截止日期不能晚於今天')
        return value

class ResumeInput(BaseModel):
    candidate_index:int|None=Field(default=None,ge=0)

def public(p):
    result=copy.deepcopy(p)
    def strip(value):
        if isinstance(value,dict):
            value.pop('path',None)
            for v in value.values():strip(v)
        elif isinstance(value,list):
            for v in value:strip(v)
    strip(result)
    return result

def create_app(root=None):
    data_root=Path(root or os.environ.get('PLANNING_DATA_DIR',str(BASE/'.data-library'))).resolve()
    test_mode=os.environ.get('PLANNING_TEST_MODE')=='1'
    if test_mode and data_root in ((BASE/'.data').resolve(),(BASE/'.data-library').resolve()):raise ValueError('测试服务不能使用日常资料目录')
    store=Store(data_root);lib=Library(store)
    pool=ThreadPoolExecutor(max_workers=2);active=set();lock=threading.Lock()
    service=ResearchService(store)
    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        for p in store.list():
            lib.import_run(p)
            if p['phase'] not in ('queued','searching','collecting'):lib.finish(p['id'])
        yield
        pool.shutdown(wait=True)
    app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None)
    app.state.store=store;app.state.service=service;app.state.library=lib;app.state.test_mode=test_mode

    @app.middleware('http')
    async def local_boundary(request:Request,call_next):
        host=request.headers.get('host','')
        if urlparse('http://'+host).hostname not in ('localhost','127.0.0.1','::1'):
            return JSONResponse({'detail':'僅供本機使用'},status_code=400)
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin=request.headers.get('origin')
            if origin and origin not in ('http://'+host,'https://'+host):
                return JSONResponse({'detail':'請從資料室頁面操作'},status_code=403)
            if not request.headers.get('content-type','').startswith('application/json'):
                return JSONResponse({'detail':'需要 JSON 請求'},status_code=415)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; worker-src 'self' blob:; font-src 'self' blob: data:; frame-src 'self'; object-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'"
        return response

    def get(id):
        try:return store.get(id)
        except KeyError:raise HTTPException(404,'找不到研究')
    def getdoc(id,docid):
        p=get(id)
        doc=next((d for d in p['documents'] if d['id']==docid),None)
        if not doc:raise HTTPException(404,'找不到文件')
        return p,doc
    def schedule(id,**kwargs):
        group=lib.import_run(get(id))
        with lock:
            if group in active or len(active)>=10:
                rejected=get(id);rejected['phase']='failed';rejected['error']='搜集未啟動：此申請正在搜集或佇列已滿';store.save(rejected);lib.finish(id)
                if group in active:raise HTTPException(409,'此研究正在搜集')
                raise HTTPException(429,'研究佇列已滿，請稍後再試')
            active.add(group)
        def work():
            try:app.state.service.run(id,**kwargs)
            finally:
                lib.finish(id)
                with lock:active.discard(group)
        p=get(id);p['phase']='queued';p['error']=None;store.save(p)
        pool.submit(work)
        return public(p)

    @app.get('/api/projects')
    def projects():return [public(p) for p in store.list()]
    @app.post('/api/projects',status_code=202)
    def create(value:ProjectInput):
        p=store.create(value.case_no,value.question,value.cutoff.isoformat())
        return schedule(p['id'])
    @app.get('/api/projects/{id}')
    def project(id:str):return public(get(id))
    def child_run(p):
        fid=lib.import_run(p)
        child=lib.begin(fid,p['question'],p['cutoff'],p['id'])
        for key in ['documents','application','events','related','candidates','issues','selected_candidate']:
            if key in p:child[key]=copy.deepcopy(p[key])
        store.save(child);return child
    @app.post('/api/projects/{id}/resume',status_code=202)
    def resume(id:str,value:ResumeInput):
        p=get(id)
        if value.candidate_index is not None:
            if value.candidate_index>=len(p['candidates']) or normalize_case(p['candidates'][value.candidate_index]['caseNo'])!=p['case_no']:raise HTTPException(422,'請重新選擇申請')
        if p['phase']=='awaiting_selection' and value.candidate_index is None:raise HTTPException(409,'請先確認申請')
        fid=lib.import_run(p)
        with lock:
            if fid in active:raise HTTPException(409,'此研究正在搜集')
        child=child_run(p)
        if value.candidate_index is None:child['documents']=[];store.save(child)
        return schedule(child['id'],selection=value.candidate_index)
    @app.post('/api/projects/{id}/documents/{docid}/retry',status_code=202)
    def retry(id:str,docid:str):
        p,doc=getdoc(id,docid)
        if doc['status']=='ready':raise HTTPException(409,'此文件已儲存')
        fid=lib.import_run(p)
        with lock:
            if fid in active:raise HTTPException(409,'此研究正在搜集')
        child=child_run(p)
        return schedule(child['id'],retry_file=docid)
    @app.get('/api/projects/{id}/documents/{docid}/file')
    def file(id:str,docid:str):
        _,doc=getdoc(id,docid)
        if doc['status']!='ready':raise HTTPException(404,'文件未取得')
        try:path=store.file(doc)
        except FileNotFoundError:raise HTTPException(404,'本地文件不存在，請重新搜集')
        return FileResponse(path,media_type='application/pdf',headers={'Content-Disposition':'inline'})
    @app.get('/api/projects/{id}/archive')
    def archive(id:str):
        p=get(id);docs=[d for d in p['documents'] if d['status']=='ready']
        if not docs:raise HTTPException(409,'尚無可下載文件')
        with tempfile.NamedTemporaryFile(suffix='.zip',delete=False) as stream:path=Path(stream.name)
        safe=re.sub(r'[^A-Z0-9_-]','_',p['case_no'])
        folders={'Gist':'02_Gist','會議文件':'03_會議文件','會議記錄':'04_會議記錄'}
        try:
            with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
                for doc in docs:
                    label=re.sub(r'[^\w\-]','_',doc['title'])[:90]
                    filename=f"{safe}_{doc.get('event_date') or 'undated'}_{label}_{doc['id']}.pdf"
                    z.write(store.file(doc),f"{safe}/{folders.get(doc['kind'],'01_申請資料')}/{filename}")
        except Exception:
            path.unlink(missing_ok=True);raise HTTPException(409,'有本地文件缺失，請重新搜集')
        return FileResponse(path,media_type='application/zip',filename=safe+'.zip',background=BackgroundTask(path.unlink,missing_ok=True))
    attach_library_routes(app,lib,schedule,ProjectInput,public)
    app.mount('/',StaticFiles(directory=BASE/'web',html=True),name='web')
    return app

app=create_app()
