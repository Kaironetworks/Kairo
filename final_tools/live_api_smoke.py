"""Non-destructive live API smoke test for the seeded KAIRO demonstration.
Requires only Python's standard library. Run after START_KAIRO.ps1.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
PASS = 0
FAIL = 0

def call(method, path, token=None, expected=(200,), body=None):
    global PASS, FAIL
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if token: req.add_header("Authorization", f"Bearer {token}")
    if data: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            status = r.status
            raw = r.read()
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
    except Exception as e:
        FAIL += 1
        print(f"[FAIL] {method} {path}: {e}")
        return None
    if status not in expected:
        FAIL += 1
        print(f"[FAIL] {method} {path}: HTTP {status} (expected {expected})")
        return None
    PASS += 1
    print(f"[PASS] {method} {path}: HTTP {status}")
    try: return json.loads(raw.decode()) if raw else None
    except Exception: return raw

def login(user):
    result = call("POST", "/api/auth/login", expected=(200,), body={"email": user, "password": "KairoDemo!2026"})
    return result["access_token"] if result else None

print("KAIRO LIVE API SMOKE")
health = call("GET", "/api/health", expected=(200,))
if health and health.get("status") == "unavailable":
    print("[FAIL] API readiness is unavailable")
    FAIL += 1

investigator = login("investigator")
forensic = login("forensic")
auditor = login("auditor")

if investigator:
    me = call("GET", "/api/auth/me", investigator, (200,))
    cases = call("GET", "/api/cases", investigator, (200,))
    if cases:
        case_id = cases[0]["id"]
        docs = call("GET", f"/api/cases/{case_id}/documents", investigator, (200,))
        if docs:
            doc_id = docs[0]["id"]
            call("POST", f"/api/documents/{doc_id}/verify", investigator, (200,))
            call("GET", f"/api/documents/{doc_id}/custody", investigator, (200,))
            call("GET", f"/api/documents/{doc_id}/versions", investigator, (200,))
            call("GET", f"/api/documents/{doc_id}/trust", investigator, (200,))
            call("GET", f"/api/documents/{doc_id}/download", investigator, (200,))
    # Investigator must not receive the auditor-only audit trail.
    call("GET", "/api/audit", investigator, (403,))
    call("POST", "/api/auth/logout", investigator, (200,))
    call("GET", "/api/auth/me", investigator, (401,))

if auditor:
    call("GET", "/api/auth/me", auditor, (200,))
    call("GET", "/api/cases", auditor, (200,))
    call("GET", "/api/audit", auditor, (200,))
    call("GET", "/api/security/posture", auditor, (200,))

if forensic:
    call("GET", "/api/auth/me", forensic, (200,))
    call("GET", "/api/cases", forensic, (200,))

print(f"\nRESULT: {PASS} passed / {FAIL} failed")
if FAIL:
    sys.exit(1)
print("LIVE API SMOKE: PASS")
