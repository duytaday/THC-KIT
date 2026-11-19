"""Bounded public HTTP with origin-scoped credentials and resumable local files."""
import datetime,email.utils,hashlib,ipaddress,json,socket,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

AGENT='THC-KIT/1.0 (local editing library; https://github.com/duytaday/THC-KIT)'
SECRET_KEYS={'key','api_key','apikey','token','access_token','authorization','signature','sig'}

def public_url(url,resolve=True):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('Use a public HTTPS URL without embedded credentials')
    if any(k.casefold() in SECRET_KEYS for k,v in urllib.parse.parse_qsl(p.query)):raise ValueError('Credentials in media URLs are not accepted')
    if resolve:
        addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Private/local network destinations are not accepted')
    return url

def safe_url(url):
    p=urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme,p.hostname or '',p.path,'',''))

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        public_url(newurl)
        result=super().redirect_request(req,fp,code,msg,headers,newurl)
        if result and urllib.parse.urlsplit(req.full_url).netloc!=urllib.parse.urlsplit(newurl).netloc:
            for key in ('Authorization','Cookie','Proxy-authorization','X-api-key'):result.remove_header(key)
        return result

def retry_delay(value,now=None):
    if not value:return None
    try:return max(0,float(value))
    except ValueError:
        try:return max(0,email.utils.parsedate_to_datetime(value).timestamp()-(time.time() if now is None else now))
        except (TypeError,ValueError,OverflowError):return None

class RetryLater(RuntimeError):
    def __init__(self,message,not_before=None):super().__init__(message);self.not_before=not_before or time.time()+60

class Client:
    def __init__(self,cache,interval=1.1,retries=2,timeout=35):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.interval=interval;self.retries=retries;self.timeout=timeout;self.last={};self.opener=urllib.request.build_opener(Redirect())

    def open(self,url,headers=None):
        public_url(url);host=urllib.parse.urlsplit(url).hostname
        for attempt in range(self.retries+1):
            time.sleep(max(0,self.interval-(time.monotonic()-self.last.get(host,0))));self.last[host]=time.monotonic()
            try:return self.opener.open(urllib.request.Request(url,headers={'User-Agent':AGENT,**(headers or {})}),timeout=self.timeout)
            except urllib.error.HTTPError as error:
                if error.code not in (429,500,502,503,504):raise RuntimeError(f'HTTP {error.code} from {host}') from None
                delay=retry_delay(error.headers.get('Retry-After'))
                if attempt==self.retries or delay is not None and delay>30:raise RetryLater(f'HTTP {error.code}; defer {max(delay or 0,2**attempt):.0f}s at {host}',time.time()+max(delay or 0,2**attempt)) from None
                time.sleep(delay if delay is not None else 2**attempt)
            except (TimeoutError,urllib.error.URLError,OSError):
                if attempt==self.retries:raise RetryLater('Public source temporarily unavailable: '+host) from None
                time.sleep(2**attempt)

    def json(self,url,ttl=86400):
        public_url(url);file=self.cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        if file.exists() and time.time()-file.stat().st_mtime<ttl:return json.loads(file.read_text(encoding='utf-8'))
        with self.open(url) as response:
            data=response.read(8*1024*1024+1)
            if len(data)>8*1024*1024:raise ValueError('API response exceeds8MiB')
            parsed=json.loads(data)
        temp=file.with_suffix('.tmp');temp.write_text(json.dumps(parsed,ensure_ascii=False),encoding='utf-8');temp.replace(file)
        return parsed

    def download(self,url,partial,*,max_bytes,check_space,progress=None):
        partial=Path(partial);sidecar=partial.with_suffix('.http.json')
        offset=partial.stat().st_size if partial.exists() else 0
        meta=json.loads(sidecar.read_text()) if sidecar.exists() else {}
        if meta.get('url_sha256')!=hashlib.sha256(url.encode()).hexdigest():offset=0
        headers={}
        if offset:
            headers['Range']=f'bytes={offset}-'
            if meta.get('etag'):headers['If-Range']=meta['etag']
            elif meta.get('last_modified'):headers['If-Range']=meta['last_modified']
        with self.open(url,headers) as response:
            status=response.status
            if offset and status==206:
                import re
                matched=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                if not matched or int(matched[1])!=offset:raise ValueError('Invalid resumed Content-Range')
                total=int(matched[3])
            else:offset=0;total=int(response.headers.get('Content-Length') or 0)
            if total>max_bytes:raise ValueError('Source exceeds per-file disk budget')
            mime=response.headers.get('Content-Type','').split(';')[0].lower()
            if mime.startswith('text/') or mime in ('application/json','application/xhtml+xml'):raise ValueError('Source returned a page, not video')
            sidecar.write_text(json.dumps(dict(url_sha256=hashlib.sha256(url.encode()).hexdigest(),etag=response.headers.get('ETag'),last_modified=response.headers.get('Last-Modified'),mime=mime,total=total)),encoding='utf-8')
            check_space(max(0,total-offset))
            size=offset
            with partial.open('ab' if offset else 'wb') as out:
                while True:
                    try:chunk=response.read(1024*1024)
                    except (TimeoutError,OSError,__import__('http.client',fromlist=['IncompleteRead']).IncompleteRead):raise RetryLater('Interrupted stream retained for Range resume') from None
                    if not chunk:break
                    size+=len(chunk)
                    if size>max_bytes:raise ValueError('Source exceeds streamed disk budget')
                    check_space(len(chunk));out.write(chunk)
                    if progress:progress(size,total)
            if total and size!=total:raise RetryLater('Incomplete transfer retained for resume')
        return dict(bytes=size,http_mime=mime,resumed_bytes=offset)
