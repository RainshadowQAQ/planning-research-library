"""Bounded retrieval from explicit official hosts with auditable raw responses."""
import hashlib
import ipaddress
import json
import socket
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse,urljoin
import httpx
from app.domain import now

ALLOWED_HOSTS={'www.tpb.gov.hk','www.ozp.tpb.gov.hk'}
MAX_BYTES=128*1024*1024

class FetchError(Exception):pass

def validate_url(url,resolve=True):
    try:
        p=urlparse(url)
        if p.scheme!='https' or p.hostname not in ALLOWED_HOSTS or p.username or p.password or p.port not in (None,443):
            raise FetchError('來源網址不在已核實的官方範圍')
        if resolve:
            addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise FetchError('來源網址解析至非公開網絡')
    except (ValueError,OSError) as exc:raise FetchError('無法核實官方來源網址') from exc
    return url

class OfficialClient:
    _rate_lock=threading.Lock()
    _last_request=0.0

    def __init__(self,root,transport=None,resolve=True):
        self.root=Path(root)/'requests';self.root.mkdir(parents=True,exist_ok=True)
        self.client=httpx.Client(timeout=30,follow_redirects=False,trust_env=False,transport=transport,
                                 limits=httpx.Limits(max_keepalive_connections=0),
                                 headers={'User-Agent':'PlanningResearchLibrary/0.1 (local research)'})
        self.resolve=resolve

    def close(self):self.client.close()

    def request(self,url,data=None):
        original=url
        for attempt in range(2):
            record={'run_id':getattr(self,'run_id',None),'url':original,'method':'POST' if data is not None else 'GET','parameters':data,'at':now(),'attempt':attempt+1}
            try:
                current=url;started=time.monotonic()
                for redirect in range(6):
                    validate_url(current,self.resolve)
                    with self._rate_lock:
                        time.sleep(max(0,.2-(time.monotonic()-OfficialClient._last_request)))
                        OfficialClient._last_request=time.monotonic()
                    # Pin the verified public IP while keeping Host and TLS SNI.
                    # Disable pooled keepalive so distinct official hosts sharing an IP
                    # never reuse a TLS session validated for a different hostname.
                    hostname=urlparse(current).hostname
                    target=current;headers={};extensions={}
                    if self.resolve:
                        addresses=socket.getaddrinfo(hostname,443,type=socket.SOCK_STREAM)
                        ips=[a[4][0] for a in addresses]
                        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):raise FetchError('來源解析至非公開網絡')
                        ip=next((ip for ip in ips if ':' not in ip),ips[0])
                        target=httpx.URL(current).copy_with(host=ip)
                        headers={'Host':hostname};extensions={'sni_hostname':hostname}
                    with self.client.stream('POST' if data is not None else 'GET',target,data=data,headers=headers,extensions=extensions) as response:
                        record.update(status=response.status_code,final_url=current)
                        if response.is_redirect:
                            if redirect==5:raise FetchError('官方來源轉址次數過多')
                            current=urljoin(current,response.headers.get('location',''))
                            continue
                        response.raise_for_status()
                        chunks=[];size=0
                        for chunk in response.iter_bytes():
                            size+=len(chunk)
                            if time.monotonic()-started>180:raise FetchError('下載超過 180 秒，請重試')
                            if size>MAX_BYTES:raise FetchError('文件超過 128 MB 限制')
                            chunks.append(chunk)
                        body=b''.join(chunks)
                        if not body:raise FetchError('官方來源返回空白內容')
                        digest=hashlib.sha256(body).hexdigest()
                        (self.root/(digest+'.bin')).write_bytes(body)
                        record.update(bytes=size,sha256=digest,content_type=response.headers.get('content-type'))
                        return body
            except (httpx.HTTPError,FetchError) as exc:
                record['error']=str(exc)
                retry=isinstance(exc,(httpx.TimeoutException,httpx.NetworkError)) or isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in (429,500,502,503,504)
                if retry and attempt==0:time.sleep(1);continue
                if isinstance(exc,httpx.HTTPStatusError):raise FetchError(f'官方來源返回 HTTP {exc.response.status_code}') from exc
                if isinstance(exc,httpx.TimeoutException):raise FetchError('連線逾時，請重試') from exc
                raise FetchError(str(exc)) from exc
            finally:
                (self.root/(uuid.uuid4().hex+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))
        raise FetchError('官方資料未能取得')
