import hashlib, json, os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = os.getenv('KAIRO_BLOCKCHAIN_URL', 'http://127.0.0.1:8090')

def custody_digest(record: dict) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def status():
    try:
        with urlopen(f'{BASE}/health', timeout=2) as r:
            data=json.loads(r.read().decode())
            return {'configured': True, 'reachable': True, **data}
    except Exception as e:
        return {'configured': bool(BASE), 'reachable': False, 'message': str(e)}

def anchor(payload: dict):
    body=json.dumps(payload).encode()
    req=Request(f'{BASE}/anchor', data=body, headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except (HTTPError, URLError, TimeoutError) as e:
        return {'ok': False, 'message': str(e)}

def read(anchor_id: str):
    try:
        with urlopen(f'{BASE}/anchor/{anchor_id}', timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {'ok': False, 'message': str(e)}
