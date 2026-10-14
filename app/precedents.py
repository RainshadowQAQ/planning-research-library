"""Precedents named by the Planning Department in a saved main paper, with page citations."""
import re
from datetime import date
from functools import lru_cache
from io import BytesIO
from pypdf import PdfReader

CASE=r'(?<![A-Z0-9/])[AY]/[A-Z0-9][A-Z0-9-]{0,30}/\d{1,6}(?:-\d{1,3})?(?![A-Z0-9/-])'
# A section starts at a "Previous/Similar Application(s)" heading line and ends at the next
# numbered top-level heading ("7. The Premises"), an appendix heading or another such heading.
HEADING=re.compile(r'^\s*(?:\d{1,2}(?:\.\d{1,2})?\.?\s+)?(Previous|Similar)\s+Applications?\b'
                   r'(?:\s+(?:within|in|for|on|at|covering)\b[^.]{0,80})?\s*(?:\(.*\))?\s*$',re.I)
END=re.compile(r'^\s*(?:\d{1,2}\.\s+[A-Z][A-Za-z]|Appendix\b|Plan\s+A-\d)',re.I)
SENTENCE=re.compile(r'(?<!\bNo\.)(?<!\bNos\.)(?<=[a-z0-9)\]]\.)\s+(?=[A-Z(])')
DECISIONS=[
    ('rejected',r'\brejected\b|\brejection\b'),
    ('approved_with_conditions',r'\bapproved\s+with\s+conditions?\b'),
    ('approved',r'\bapproved\b'),
    ('withdrawn',r'\bwithdrawn\b'),
    ('deferred',r'\bdeferred\b'),
]
LABELS={'approved_with_conditions':'附帶條件批准','approved':'批准','rejected':'拒絕',
        'withdrawn':'撤回','deferred':'延期','unknown':'未能判讀'}
GROUPS={'previous':'同址過往申請','similar':'同類申請'}

def _decision(text):
    """First decision word in the text; 'unknown' when the wording names none."""
    found=[(m.start(),kind) for kind,pattern in DECISIONS for m in [re.search(pattern,text,re.I)] if m]
    if not found:return 'unknown'
    first=min(found)[0]
    # "approved with conditions" also matches "approved": prefer the longer wording at that spot.
    kinds=[k for at,k in found if at==first]
    return 'approved_with_conditions' if 'approved_with_conditions' in kinds else kinds[0]

def _date(text):
    m=re.search(r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b',text)
    if not m:return None
    try:return date(int(m[3]),int(m[2]),int(m[1])).isoformat()
    except ValueError:return None

def _excerpt(sentence,case):
    """The sentence, or for long ones the clause from the application number to its decision date."""
    sentence=sentence.strip()
    if len(sentence)<=250:return sentence
    clause=sentence[sentence.index(case):]
    decision=re.search('|'.join(p for _,p in DECISIONS),clause,re.I)
    if decision:
        when=re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b').search(clause,decision.end(),decision.end()+80)
        return clause[:(when or decision).end()]
    return clause[:250]

def _sentences(text):
    """Sentence spans (start,end) over whitespace-collapsed text."""
    spans=[];start=0
    for m in SENTENCE.finditer(text):
        spans.append((start,m.start()));start=m.end()
    spans.append((start,len(text)))
    return spans

def sections(pages):
    """Yield (kind, page_number, text) for each Previous/Similar section chunk, page by page."""
    current=None
    for number,page in enumerate(pages,1):
        chunk=[]
        for line in page.splitlines():
            heading=HEADING.match(line)
            if heading or (current and END.match(line)):
                if current and chunk:yield current,number,' '.join(chunk)
                chunk=[];current=heading[1].lower() if heading else None
                continue
            if current:chunk.append(line.strip())
        if current and chunk:yield current,number,' '.join(chunk)

def extract(pages,case_no):
    """Precedents grouped as previous/similar, each with a page and a unique-ish excerpt."""
    groups={k:dict(kind=k,label=GROUPS[k],items=[],statements=[]) for k in GROUPS}
    seen=set()
    for kind,page,raw in sections(pages):
        text=re.sub(r'\s+',' ',raw).strip()
        mentions=[(m.start(),m.end(),m.group()) for m in re.finditer(CASE,text)]
        spans=_sentences(text)
        if not mentions:
            # Keep only the opening sentence: unnumbered sub-headings can run into later sections.
            first=_sentences(text)[0]
            groups[kind]['statements'].append(dict(text=text[first[0]:first[1]].strip()[:300],page=page))
            continue
        for i,(start,end,case) in enumerate(mentions):
            if case==case_no or (kind,case) in seen:continue
            seen.add((kind,case))
            sentence=next(text[a:b] for a,b in spans if a<=start<=b)
            # Table rows have no sentence breaks: read the decision up to the next application number.
            following=text[end:mentions[i+1][0] if i+1<len(mentions) else len(text)]
            decision=_decision(following)
            if decision=='unknown':decision=_decision(sentence)
            excerpt=_excerpt(sentence,case)
            groups[kind]['items'].append(dict(case_no=case,decision=decision,decision_label=LABELS[decision],
                                              decision_date=_date(following) or _date(sentence),
                                              page=page,excerpt=excerpt))
    return [groups['previous'],groups['similar']]

@lru_cache(maxsize=32)
def _pages(sha256,body):
    return tuple(page.extract_text() or '' for page in PdfReader(BytesIO(body)).pages)

def main_papers(documents):
    """Saved main papers, newest meeting first."""
    papers=[d for d in documents if d.get('status')=='ready' and d.get('kind')=='會議文件' and '主文件' in d.get('title','')]
    return sorted(papers,key=lambda d:d.get('event_date') or '',reverse=True)

def precedents(folder_view,read_file,folder_ids=None):
    """Read the newest saved main paper. `read_file(doc)` returns its bytes."""
    case_no=folder_view['case_no'];folder_ids=folder_ids or {}
    result=dict(case_no=case_no,source=None,groups=[],summary={})
    papers=main_papers(folder_view.get('documents',[]))
    if not papers:
        result['status']='no_paper';return result
    paper=papers[0]
    try:pages=_pages(paper['sha256'],read_file(paper))
    except Exception:
        result['status']='unreadable';return result
    result['source']=dict(doc_id=paper['id'],source_run=paper.get('source_run'),title=paper.get('title'),
                          sha256=paper['sha256'],url=paper.get('url'),event_date=paper.get('event_date'))
    if not any(p.strip() for p in pages):
        result['status']='no_text';return result
    result['groups']=extract(pages,case_no)
    for group in result['groups']:
        for item in group['items']:
            item['folder_id']=folder_ids.get(item['case_no'])
            item['citation']=dict(page=item['page'],excerpt=item['excerpt'],doc_id=paper['id'],
                                  source_run=paper.get('source_run'),source_sha256=paper['sha256'],availability='ready')
    decisions=[i['decision'] for i in result['groups'][1]['items']]
    approved=sum(d in ('approved','approved_with_conditions') for d in decisions)
    rejected=decisions.count('rejected')
    result['summary']=dict(approved=approved,rejected=rejected,other=len(decisions)-approved-rejected)
    result['status']='ready'
    return result
