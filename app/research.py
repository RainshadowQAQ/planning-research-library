"""One research run: identity gate, dated official sources and individual files."""
import hashlib
import json
import re
from io import BytesIO
from urllib.parse import urlparse,urljoin
from bs4 import BeautifulSoup
from pypdf import PdfReader
from app.domain import (exact_candidates,normalize_case,hk_date,documents_from_detail,
                        agenda_documents,contains_case,document,now,today)
from app.network import OfficialClient,FetchError

HOST='https://www.ozp.tpb.gov.hk'

def verify_pdf(body,case):
    if not body.startswith(b'%PDF-'):raise ValueError('來源未返回 PDF 文件')
    try:
        reader=PdfReader(BytesIO(body))
        if reader.is_encrypted:raise ValueError('PDF 已加密，無法核對')
        pages=len(reader.pages)
        if pages==0:raise ValueError('PDF 沒有頁面')
        matches=[];text_chars=0;identifiers=set()
        for index,page in enumerate(reader.pages):
            text=page.extract_text() or '';text_chars+=len(text.strip())
            pattern=r'(?<![A-Z0-9/])[AY]\s*/\s*[A-Z0-9-](?:\s*[A-Z0-9-]){0,30}\s*/\s*\d(?:\s*\d){0,5}(?:\s*-\s*\d(?:\s*\d){0,2})?(?![A-Z0-9/-]|\s*[0-9/-])'
            page_ids={re.sub(r'\s+','',m.group()) for m in re.finditer(pattern,text.upper())}
            identifiers.update(page_ids)
            if case in page_ids:matches.append(index+1)
        # Absence in a scan is not a mismatch. Provenance association remains visible.
        if not matches and identifiers:
            raise ValueError('文件內的申請編號與目標不符')
        method='原文編號及官方連結' if matches else '官方連結；原文未檢出編號'
        return {'pages':pages,'matched_pages':matches,'verification':method,'text_chars':text_chars}
    except Exception as exc:
        raise ValueError('PDF 無法讀取或核對：'+str(exc)) from exc

class ResearchService:
    def __init__(self,store,client_factory=OfficialClient):
        self.store=store;self.client_factory=client_factory

    def _json(self,client,url,data):
        payload=json.loads(client.request(url,data))
        if not isinstance(payload,dict) or payload.get('IsSuccess') is not True or not isinstance(payload.get('Data'),list):
            raise FetchError('官方接口返回未成功或未知格式')
        return payload['Data']

    def run(self,id,selection=None,retry_file=None):
        p=self.store.get(id);client=self.client_factory(self.store.root);client.run_id=id
        try:
            if retry_file:
                doc=next(d for d in p['documents'] if d['id']==retry_file)
                p['phase']='collecting';p['error']=None;self.store.save(p)
                self._download(p,doc,client)
                self._finish(p);return
            p['phase']='searching';p['error']=None;p['issues']=[];self.store.save(p)
            endpoint=HOST+('/api/Amend' if p['case_no'].startswith('Y/') else '/api/Perm')
            if selection is not None:
                candidates=p['candidates']
                if not isinstance(selection,int) or not 0<=selection<len(candidates):raise ValueError('請重新選擇申請')
                chosen=candidates[selection];p['case_no']=normalize_case(chosen['caseNo'])
                p['selected_candidate']=chosen
                endpoint=HOST+('/api/Amend' if p['case_no'].startswith('Y/') else '/api/Perm')
            else:
                rows=self._json(client,endpoint,{'caseNo':p['case_no']})
                # Byte-identical duplicates are one identity; differing metadata needs selection.
                candidates=list({json.dumps(r,sort_keys=True):r for r in exact_candidates(rows,p['case_no'])}.values())
                if len(candidates)!=1:
                    p['candidates']=candidates or rows
                    p['phase']='awaiting_selection' if candidates else 'no_match'
                    p['error']=None if candidates else '未找到完整編號相符的申請'
                    self.store.save(p);return
                chosen=candidates[0];p['selected_candidate']=chosen
            detail_rows=self._json(client,endpoint+'/Detail/',{'caseNo':p['case_no'],'appType':'amendment' if p['case_no'].startswith('Y/') else 'permission'})
            matches=exact_candidates(detail_rows,p['case_no'])
            if chosen.get('planNo'):
                matches=[r for r in matches if r.get('planNo')==chosen['planNo']]
            if len(matches)!=1:raise FetchError('申請詳情無法唯一對應已選記錄')
            detail=matches[0]
            received=hk_date(detail.get('receDate'))
            if received and received>p['cutoff']:
                p['phase']='no_match';p['error']='此申請的接收日期晚於資料截止日期';p['candidates']=[];self.store.save(p);return
            p['application']={k:v for k,v in detail.items() if k not in ('appDeciCode','meetDetail')}
            p['application']['retrieved_at']=now()
            p['related']=list(dict.fromkeys(str(detail[k]) for k in ['prevCaseNo','nextCaseNo'] if detail.get(k)))
            p['events']=[dict(e,event_date=hk_date(e.get('deciDate'))) for e in detail.get('meetDetail',[]) if hk_date(e.get('deciDate')) and hk_date(e.get('deciDate'))<=p['cutoff']]
            p['phase']='collecting';self.store.save(p)
            docs=documents_from_detail(detail,p['cutoff'])
            if p['cutoff']<today() and any(detail.get('gist'+lang) for lang in ['EN','TC']):
                p['issues'].append('Gist：未能確認此文件在截止日期前的版本，未納入資料包。')
            if not p['events']:p['issues'].append('會議資料：截止日期前未取得可確認日期的會議記錄。')
            for event in p['events']:
                auth=event.get('authTypeCode');num=event.get('meetNo')
                if auth not in ('MPC','RNTPC','TPB') or not str(num).isdigit():
                    p['issues'].append('會議文件：缺少可核實的會議編號。');continue
                for lang in ['EN','TC']:
                    if event.get('MinsLink'+lang) or any(d['kind']=='會議記錄' and d['event_date']==event['event_date'] and d['language']==lang and d['status']=='ready' for d in p['documents']):continue
                    try:
                        found=self._minutes_fallback(client,auth,num,lang,event['event_date'])
                        docs.extend(found)
                        if not found:p['issues'].append(f'第 {num} 次會議記錄（{lang}）：官方頁面未找到連結。')
                    except Exception as exc:p['issues'].append(f'第 {num} 次會議記錄（{lang}）：{exc}')
                # Agenda pattern is grounded in the official meeting index; PDF paths come only from page anchors.
                agenda=f'https://www.tpb.gov.hk/en/meetings/{auth}/Agenda/{num}_{auth.lower()}_agenda.html'
                try:
                    html=client.request(agenda).decode('utf-8-sig',errors='replace')
                    found=agenda_documents(html,agenda,p['case_no'],event['event_date'])
                    docs.extend(found)
                    if not found:p['issues'].append(f"第 {num} 次會議文件：官方議程未找到此申請的 PDF 連結。")
                except Exception as exc:p['issues'].append(f'第 {num} 次會議文件：{exc}')
            previous={d['url']:d for d in p['documents']}
            for d in docs:previous.setdefault(d['url'],d)
            p['documents']=list(previous.values())
            self.store.save(p)
            for doc in sorted(p['documents'],key=lambda d: (0 if '主文件' in d['title'] else 1 if d['kind']=='會議記錄' else 2 if '圖則' in d['title'] else 3 if d['kind']=='Gist' else 4)):
                if doc['status']=='ready':
                    try:
                        if hashlib.sha256(self.store.file(doc).read_bytes()).hexdigest()==doc['sha256']:continue
                    except FileNotFoundError:pass
                self._download(p,doc,client)
            if not p['documents']:p['issues'].append('本次未找到可下載的文件。')
            self._finish(p)
        except Exception as exc:
            p['phase']='error';p['error']=str(exc);self.store.save(p)
        finally:client.close()

    def _minutes_fallback(self,client,auth,num,lang,date):
        page=f'https://www.tpb.gov.hk/{lang.lower()}/meetings/{auth.lower()}_meeting.html'
        pages=[page];result=[]
        for index,url in enumerate(pages):
            soup=BeautifulSoup(client.request(url).decode('utf-8-sig',errors='replace'),'html.parser')
            for a in soup.find_all('a',href=True):
                link=urljoin(url,a['href']);path=urlparse(link).path
                if re.fullmatch(r'/'+lang.lower()+r'/meetings/'+auth+r'/Minutes/m'+str(num)+auth.lower()+('_e' if lang=='EN' else '_c')+r'\.pdf',path,re.I):
                    result.append(document(link,'會議記錄',f'第 {num} 次會議 · 會議記錄 · {lang}',url,lang,date))
                elif index==0 and len(pages)==1 and path.endswith('/'+auth.lower()+'_meeting_archive.html') and link not in pages:
                    pages.append(link)
            if result:return list({d['url']:d for d in result}.values())
        return []

    def _download(self,p,doc,client):
        doc['status']='pending';doc['error']=None;self.store.save(p)
        try:
            body=client.request(doc['url']);info=verify_pdf(body,p['case_no'])
            doc.update(info,status='ready',path=self.store.content(body),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),retrieved_at=now())
        except Exception as exc:doc.update(status='error',error=str(exc),path=None,sha256=None)
        self.store.save(p)

    def _finish(self,p):
        p['phase']='partial' if p['issues'] or any(d['status']!='ready' for d in p['documents']) else 'complete'
        p['error']=None;self.store.save(p)
