"""Folder-scoped, read-only site-fact sample."""
from fastapi import HTTPException
from app.site_facts import resolve_sample

def attach_site_fact_routes(app,lib,view):
    @app.get('/api/folders/{id}/site-facts')
    def site_facts(id:str,run:str|None=None,cutoff:str|None=None):
        scoped=view(id,run,cutoff)
        history=lib.view(id)['documents'] if (run or cutoff) else None
        try:return resolve_sample(scoped,history)
        except KeyError:raise HTTPException(404,'此資料夾沒有場地資料樣板')
