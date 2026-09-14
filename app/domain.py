"""Official identity, dates and document associations; no network or persistence."""
import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

HK = ZoneInfo('Asia/Hong_Kong')

def now():
    return datetime.now(HK).isoformat(timespec='seconds')

def today():
    return datetime.now(HK).date().isoformat()

def normalize_case(value):
    value=value.strip().upper()
    if not re.fullmatch(r'[AY]/[A-Z0-9][A-Z0-9-]{0,30}/[0-9]{1,6}(?:-[0-9]{1,3})?',value):
        raise ValueError('請輸入完整申請編號，例如 A/K1/265')
    return value

def contains_case(text, case):
    return bool(re.search(r'(?<![A-Z0-9/])'+re.escape(case)+r'(?![A-Z0-9/-])',text.upper()))

def exact_candidates(rows,case):
    return [r for r in rows if str(r.get('caseNo','')).strip().upper()==case]

def hk_date(value):
    if not value:return None
    match=re.search(r'/Date\((-?\d+)',str(value))
    if match:return datetime.fromtimestamp(int(match[1])/1000,HK).date().isoformat()
    try:
        parsed=datetime.fromisoformat(str(value))
        return (parsed.astimezone(HK) if parsed.tzinfo else parsed).date().isoformat()
    except ValueError:return None

def document(url,kind,title,source,language='EN',event_date=None):
    return dict(id=hashlib.sha256(url.encode()).hexdigest()[:20],url=url,kind=kind,title=title,
                discovered_from=source,language=language,event_date=event_date,file_date=None,
                status='pending',error=None,path=None,sha256=None,bytes=0,pages=0,matched_pages=[],retrieved_at=None)

def documents_from_detail(detail,cutoff):
    source='https://www.ozp.tpb.gov.hk/api/Perm/Detail/'
    docs=[]
    # Undated Gist is a current snapshot, not evidence of a historical website state.
    if cutoff>=today():
        for lang in ['EN','TC']:
            if detail.get('gist'+lang):
                docs.append(document(detail['gist'+lang],'Gist','申請摘要 · '+('英文' if lang=='EN' else '中文'),source,lang))
        if detail.get('paper') and isinstance(detail['paper'],str):
            docs.append(document(detail['paper'],'會議文件','申請會議文件',source))
    for event in detail.get('meetDetail') or []:
        date=hk_date(event.get('deciDate'))
        if not date or date>cutoff:continue
        for lang in ['EN','TC']:
            if event.get('MinsLink'+lang):
                docs.append(document(event['MinsLink'+lang],'會議記錄',f"第 {event.get('meetNo','—')} 次會議 · 會議記錄 · {lang}",source,lang,date))
    return list({d['url']:d for d in docs}.values())

def agenda_documents(html,page_url,case,date):
    soup=BeautifulSoup(html,'html.parser')
    docs=[]
    for row in soup.find_all('tr'):
        if not contains_case(row.get_text(' ',strip=True),case):continue
        # Ignore enclosing rows containing another matching nested row.
        if any(contains_case(child.get_text(' ',strip=True),case) for child in row.find_all('tr')):continue
        for a in row.find_all('a',href=True):
            url=urljoin(page_url,a['href'])
            if not urlparse(url).path.lower().endswith('.pdf'):continue
            label=a.get_text(' ',strip=True) or urlparse(url).path.rsplit('/',1)[-1]
            lower=(label+' '+url).lower()
            kind='附件' if 'appendix' in lower or '附件' in lower else '圖則' if 'plan' in lower or '圖' in label else '主文件'
            docs.append(document(url,'會議文件',f'{date} · {kind}',page_url,'EN',date))
    return list({d['url']:d for d in docs}.values())
