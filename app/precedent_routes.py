"""Folder-scoped, read-only precedents read from the saved main paper."""
from app.precedents import precedents

def attach_precedent_routes(app,lib,view):
    @app.get('/api/folders/{id}/precedents')
    def folder_precedents(id:str,run:str|None=None,cutoff:str|None=None):
        scoped=view(id,run,cutoff)
        folder_ids={f['case_no']:f['id'] for f in lib.folders()}
        return precedents(scoped,lambda d:lib.store.file(d).read_bytes(),folder_ids)
