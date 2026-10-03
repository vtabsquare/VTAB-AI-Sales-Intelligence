"""Evidence extraction never guesses a mailbox or claims fetched content is verified."""
import re
from html import unescape
from urllib.parse import urlparse
import httpx

def fetch_evidence(url):
    parsed=urlparse(url or '')
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.hostname.endswith(('.local','.invalid')):
        return {'status':'UNAVAILABLE','source_url':url,'text':'','emails':[]}
    try:
        with httpx.Client(timeout=15,follow_redirects=True,headers={'User-Agent':'VTAB-Opportunity-Agent/1.0'}) as client:
            response=client.get(url);response.raise_for_status();html=response.text[:500000]
        text=unescape(re.sub(r'<[^>]*>',' ',re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',html,flags=re.S|re.I)))
        text=re.sub(r'\s+',' ',text).strip()
        candidates=re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',unescape(html))
        emails=list(dict.fromkeys(x.lower() for x in candidates if not any(v in x.lower() for v in ['noreply','no-reply','donotreply','example.com'])))[:20]
        return {'status':'FETCHED','source_url':str(response.url),'text':text[:12000],'emails':emails}
    except Exception:
        return {'status':'UNAVAILABLE','source_url':url,'text':'','emails':[]}
