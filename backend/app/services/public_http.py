"""Public-source requests reject private targets and validate every redirect."""
import ipaddress
import socket
from urllib.parse import urlparse,urljoin
import httpx

def validate_public_url(url):
    parsed=urlparse(url)
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.port not in {None,80,443}:
        raise ValueError('Only public HTTP(S) source URLs on standard ports are allowed.')
    addresses=socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Private, loopback and reserved source addresses are forbidden.')

def public_get(url):
    with httpx.Client(timeout=25,follow_redirects=False,headers={'User-Agent':'VTAB-Opportunity-Agent/1.0'}) as client:
        for _ in range(5):
            validate_public_url(url)
            response=client.get(url)
            if response.status_code in {301,302,303,307,308}:
                url=urljoin(url,response.headers.get('location',''));continue
            response.raise_for_status()
            if len(response.content)>2000000: raise ValueError('Source exceeds the 2 MB response limit.')
            return response
        raise ValueError('Too many source redirects.')
