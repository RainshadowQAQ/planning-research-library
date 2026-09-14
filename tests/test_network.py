import pytest
from app.network import validate_url, FetchError

@pytest.mark.parametrize('url',['http://www.tpb.gov.hk/a','https://localhost/a','https://www.tpb.gov.hk.evil.test/a','https://127.0.0.1/a','https://user@www.tpb.gov.hk/a','https://www.tpb.gov.hk:444/a'])
def test_disallowed_url(url):
    with pytest.raises(FetchError): validate_url(url,resolve=False)
def test_public_dns_only(monkeypatch):
    monkeypatch.setattr('socket.getaddrinfo',lambda *args,**kwargs:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(FetchError):validate_url('https://www.tpb.gov.hk/a')

def test_redirect_is_checked(tmp_path):
    import httpx
    from app.network import OfficialClient
    calls=[]
    def handle(req):
        calls.append(str(req.url));return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
    client=OfficialClient(tmp_path,httpx.MockTransport(handle),resolve=False)
    with pytest.raises(FetchError):client.request('https://www.tpb.gov.hk/a')
    assert len(calls)==1

def test_transient_retry_and_forbidden(tmp_path):
    import httpx
    from app.network import OfficialClient
    calls=[]
    def handle(req):
        calls.append(req);return httpx.Response(503 if len(calls)==1 else 200,content=b'good')
    client=OfficialClient(tmp_path,httpx.MockTransport(handle),resolve=False)
    assert client.request('https://www.tpb.gov.hk/a')==b'good'
    assert len(calls)==2
    forbidden=OfficialClient(tmp_path,httpx.MockTransport(lambda r:httpx.Response(403)),resolve=False)
    with pytest.raises(FetchError,match='403'):forbidden.request('https://www.tpb.gov.hk/a')

def test_pin_public_ip_keeps_host_and_sni(tmp_path,monkeypatch):
    import httpx
    from app.network import OfficialClient
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**kw:[(2,1,6,'',('8.8.8.8',443))])
    seen=[]
    def handle(req):
        seen.append(req);return httpx.Response(200,content=b'data')
    c=OfficialClient(tmp_path,httpx.MockTransport(handle))
    assert c.request('https://www.tpb.gov.hk/file')==b'data'
    assert seen[0].url.host=='8.8.8.8'
    assert seen[0].headers['host']=='www.tpb.gov.hk'
    assert seen[0].extensions['sni_hostname']=='www.tpb.gov.hk'

def test_rebinding_before_connect_is_blocked(tmp_path,monkeypatch):
    import httpx
    from app.network import OfficialClient
    addresses=iter(['8.8.8.8','127.0.0.1'])
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**kw:[(2,1,6,'',(next(addresses),443))])
    def handle(req):raise AssertionError('must not connect')
    c=OfficialClient(tmp_path,httpx.MockTransport(handle))
    with pytest.raises(FetchError):c.request('https://www.tpb.gov.hk/file')
