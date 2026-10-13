"""Reviewed A/K1/265 site-fact sample, bound to saved originals by content hash."""
import copy
import json
from functools import lru_cache
from pathlib import Path

SAMPLE=Path(__file__).resolve().parent/'sample_data'/'ak1_265.json'
QUESTIONS={'identity','use','scale','meaning','planning','history','unknowns'}

@lru_cache(maxsize=1)
def _sample():
    data=json.loads(SAMPLE.read_text(encoding='utf-8'))
    ids=[c['id'] for c in data['claims']]
    if len(ids)!=len(set(ids)):raise ValueError('場地資料編號重複')
    issues={i['id'] for i in data['issues']}
    for claim in data['claims']:
        if claim['question'] not in QUESTIONS:raise ValueError('未知研究問題：'+claim['id'])
        if not set(claim['issue_ids'])<=issues:raise ValueError('未知待查事項：'+claim['id'])
        for c in claim['citations']:
            if c['source'] not in data['sources']:raise ValueError('未知來源：'+claim['id'])
    return data

def load_sample():
    """The immutable sample with source identity copied into every citation."""
    data=copy.deepcopy(_sample())
    for row in [*data['claims'],*data['interpretations']]:
        for c in row['citations']:
            s=data['sources'][c['source']]
            c.update(source_sha256=s['sha256'],source_url=s['url'],source_title=s['title'],
                     source_format=s['format'],source_date=s['document_date'])
            c.setdefault('page',None);c.setdefault('json_path',None)
            c.setdefault('context_before','');c.setdefault('context_after','')
    return data

def _versions(documents):
    for display in documents:
        yield display
        yield from display.get('versions',[])

def matching_version(documents,citation):
    """Exact bytes decide identity; the URL only orders equal-hash copies and warns."""
    matches=[v for v in _versions(documents) if v.get('sha256')==citation['source_sha256'] and v.get('status')=='ready']
    if not matches:return None
    matches.sort(key=lambda v:(v.get('url')!=citation.get('source_url'),v.get('source_run',''),v.get('id','')))
    chosen=matches[0];observed=chosen.get('url')
    warnings=([] if observed==citation.get('source_url') else
              ['source_url_missing'] if not observed else ['source_url_changed'])
    return {'doc_id':chosen['id'],'source_run':chosen['source_run'],'observed_url':observed,'warnings':warnings}

def _resolve(citation,documents,history):
    citation.update(doc_id=None,source_run=None,observed_url=None,warnings=[])
    if citation['source_format']!='pdf':
        citation['availability']='not_pdf';return
    found=matching_version(documents,citation)
    if found:
        citation.update(found,availability='ready');return
    if history is not None and matching_version(history,citation):
        citation['availability']='outside_scope';return
    same_source=[v for v in _versions(documents) if v.get('url')==citation['source_url'] and v.get('status')=='ready']
    citation['availability']='version_mismatch' if same_source else 'missing_original'

def resolve_sample(folder_view,history_documents=None):
    """Return the sample with each PDF citation bound to a visible saved version, if any.

    `history_documents` is the unscoped folder view, used only to tell a version hidden
    by the selected run/date (outside_scope) apart from one that was never saved."""
    data=load_sample()
    if folder_view.get('case_no')!=data['case_no']:raise KeyError(folder_view.get('case_no'))
    documents=folder_view.get('documents',[])
    for row in [*data['claims'],*data['interpretations']]:
        for c in row['citations']:_resolve(c,documents,history_documents)
    del data['sources']
    return data
