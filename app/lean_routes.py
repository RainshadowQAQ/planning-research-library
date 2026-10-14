"""Folder-scoped, read-only draft lean built from site facts and precedents."""
from datetime import date
from fastapi import HTTPException
from app.domain import today
from app.lean import preliminary_lean
from app.precedents import precedents
from app.site_facts import resolve_sample

def attach_lean_routes(app,lib,view):
    @app.get('/api/folders/{id}/lean')
    def folder_lean(id:str,run:str|None=None,cutoff:str|None=None,as_of:date|None=None):
        scoped=view(id,run,cutoff)
        history=lib.view(id)['documents'] if (run or cutoff) else None
        try:facts=resolve_sample(scoped,history)
        except KeyError:raise HTTPException(404,'此資料夾沒有場地資料樣板')
        folder_ids={f['case_no']:f['id'] for f in lib.folders()}
        found=precedents(scoped,lambda d:lib.store.file(d).read_bytes(),folder_ids)
        return preliminary_lean(facts,found,as_of or date.fromisoformat(today()))
