from __future__ import annotations
import hashlib, json, os, secrets, time, uuid, io, zipfile, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import jwt
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOCAL_EVIDENCE = DATA / "evidence"
LOCAL_TRUSTED = DATA / "trusted"
DB_PATH = DATA / "kairo.db"
DATA.mkdir(exist_ok=True); LOCAL_EVIDENCE.mkdir(exist_ok=True); LOCAL_TRUSTED.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("KAIRO_DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SECRET = os.getenv("KAIRO_SECRET", "kairo-sih-2026-demo-secret-change-me-please")
ATTACK_KEY = os.getenv("KAIRO_ATTACK_KEY", "KAIRO-LAB-2026")
MAX_UPLOAD = int(os.getenv("KAIRO_MAX_UPLOAD_MB", "100")) * 1024 * 1024
RESET_DEMO_PASSWORDS = os.getenv("KAIRO_RESET_DEMO_PASSWORDS", "1" if DATABASE_URL.startswith("sqlite") else "0") == "1"

S3_ENDPOINT = os.getenv("KAIRO_S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("KAIRO_S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("KAIRO_S3_SECRET_KEY", "minioadmin")
S3_REGION = os.getenv("KAIRO_S3_REGION", "us-east-1")
EVIDENCE_BUCKET = os.getenv("KAIRO_S3_EVIDENCE_BUCKET", "kairo-evidence")
TRUSTED_BUCKET = os.getenv("KAIRO_S3_TRUSTED_BUCKET", "kairo-trusted")

try:
    import boto3
except Exception:
    boto3 = None

app = FastAPI(title="KAIRO Secure Evidence Platform", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ROLES = {
    "POLICE": {"label":"Law Enforcement / Police Agencies", "permissions":{"case.create","case.read","case.update","evidence.create","evidence.read","evidence.verify","evidence.share"}},
    "INVESTIGATOR": {"label":"Investigative / Specialized Agencies", "permissions":{"case.create","case.read","case.update","evidence.create","evidence.read","evidence.verify","evidence.share","investigation.write","intelligence.read"}},
    "FORENSIC": {"label":"Forensic / Scientific Laboratories", "permissions":{"case.read","evidence.read","evidence.verify","evidence.restore","forensic.write","report.create","trust.read","intelligence.read"}},
    "LEGAL": {"label":"Judiciary / Legal Institutions", "permissions":{"case.read","evidence.read","evidence.verify","report.read","trust.read","governance.read"}},
    "AUDITOR": {"label":"Audit / Compliance", "permissions":{"case.read","evidence.read","audit.read","incident.read","trust.read","governance.read"}},
    "ADMIN": {"label":"System Administration", "permissions":{"*"}},
}
USERS = {
    "police@kairo.local": ("Police Officer", "POLICE", "KairoDemo!2026"),
    "investigator@kairo.local": ("Investigation Officer", "INVESTIGATOR", "KairoDemo!2026"),
    "forensic@kairo.local": ("Forensic Examiner", "FORENSIC", "KairoDemo!2026"),
    "legal@kairo.local": ("Judicial Reviewer", "LEGAL", "KairoDemo!2026"),
    "auditor@kairo.local": ("Compliance Auditor", "AUDITOR", "KairoDemo!2026"),
    "admin@kairo.local": ("System Administrator", "ADMIN", "KairoDemo!2026"),
}

SCHEMA = [
"""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, email VARCHAR(255) UNIQUE NOT NULL, name VARCHAR(255) NOT NULL, role VARCHAR(40) NOT NULL, password_hash TEXT NOT NULL, active INTEGER DEFAULT 1, created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, case_no VARCHAR(120) UNIQUE NOT NULL, title VARCHAR(255) NOT NULL, description TEXT, classification VARCHAR(80), priority VARCHAR(40), status VARCHAR(80), created_by INTEGER, created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS members(case_id INTEGER NOT NULL, user_id INTEGER NOT NULL, UNIQUE(case_id,user_id))""",
"""CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_no VARCHAR(80) UNIQUE NOT NULL, case_id INTEGER NOT NULL, title VARCHAR(255) NOT NULL, kind VARCHAR(100), classification VARCHAR(80), current_version INTEGER NOT NULL, status VARCHAR(80), created_by INTEGER, created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, filename VARCHAR(500), object_key TEXT NOT NULL, trusted_key TEXT NOT NULL, sha256 VARCHAR(64) NOT NULL, size INTEGER NOT NULL, created_by INTEGER, created_at TEXT NOT NULL, restored_from INTEGER, reason TEXT, UNIQUE(evidence_id,version))""",
"""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, event_id VARCHAR(80) UNIQUE NOT NULL, actor_id INTEGER, action VARCHAR(120), target_type VARCHAR(80), target_id VARCHAR(120), result VARCHAR(40), details TEXT, created_at TEXT NOT NULL, prev_hash VARCHAR(64), event_hash VARCHAR(64))""",
"""CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, incident_no VARCHAR(80) UNIQUE NOT NULL, evidence_id INTEGER NOT NULL, expected_hash VARCHAR(64), observed_hash VARCHAR(64), status VARCHAR(40), detected_at TEXT, resolved_at TEXT, resolved_by INTEGER, details TEXT)""",
"""CREATE TABLE IF NOT EXISTS trust(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, sha256 VARCHAR(64), event_hash VARCHAR(64), anchor_id VARCHAR(120) UNIQUE NOT NULL, proof VARCHAR(64), provider VARCHAR(120), created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS shares(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_id INTEGER NOT NULL, from_user INTEGER NOT NULL, to_user INTEGER NOT NULL, expires_at TEXT, status VARCHAR(30), created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS signatures(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, signer_id INTEGER NOT NULL, signature TEXT NOT NULL, algorithm VARCHAR(80), created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS governance(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_id INTEGER UNIQUE NOT NULL, retention_days INTEGER, legal_hold INTEGER DEFAULT 0, hold_reason TEXT, sealed_version INTEGER, updated_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS redactions(id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, object_key TEXT NOT NULL, count INTEGER NOT NULL, created_by INTEGER NOT NULL, created_at TEXT NOT NULL)""",
]
# SQLite needs AUTOINCREMENT syntax instead of PostgreSQL identity. Keep a portable schema string set.
if engine.url.get_backend_name() == "sqlite":
    SCHEMA = [s.replace("INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY", "INTEGER PRIMARY KEY AUTOINCREMENT") for s in SCHEMA]


def conn(): return engine.connect()
def tx(): return engine.begin()
def now(): return datetime.now(timezone.utc).isoformat()
def rows(result): return [dict(r._mapping) for r in result]
def one(result):
    r=result.first(); return dict(r._mapping) if r else None

def password_hash(password, salt=None):
    salt=salt or secrets.token_bytes(16); dk=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000); return salt.hex()+":"+dk.hex()
def password_verify(password, stored):
    try:
        s,d=stored.split(":",1); got=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(s),310000).hex(); return secrets.compare_digest(got,d)
    except Exception: return False
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def safe_name(name): return Path(name or "evidence.bin").name.replace("..", "_")[:200]

class Storage:
    def __init__(self):
        self.s3=None
        if S3_ENDPOINT and boto3:
            self.s3=boto3.client("s3",endpoint_url=S3_ENDPOINT,aws_access_key_id=S3_ACCESS_KEY,aws_secret_access_key=S3_SECRET_KEY,region_name=S3_REGION)
            self._ensure_buckets()
    def _ensure_buckets(self):
        for bucket in (EVIDENCE_BUCKET, TRUSTED_BUCKET):
            try:self.s3.head_bucket(Bucket=bucket)
            except Exception:self.s3.create_bucket(Bucket=bucket)
            try:self.s3.put_bucket_versioning(Bucket=bucket,VersioningConfiguration={"Status":"Enabled"})
            except Exception:pass
    @property
    def mode(self): return "S3-compatible/MinIO" if self.s3 else "local-versioned-fallback"
    def put(self,bucket,key,data):
        if self.s3: self.s3.put_object(Bucket=bucket,Key=key,Body=data,ContentType="application/octet-stream")
        else:
            base=LOCAL_EVIDENCE if bucket==EVIDENCE_BUCKET else LOCAL_TRUSTED; p=base/key; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
    def get(self,bucket,key):
        if self.s3: return self.s3.get_object(Bucket=bucket,Key=key)["Body"].read()
        base=LOCAL_EVIDENCE if bucket==EVIDENCE_BUCKET else LOCAL_TRUSTED; return (base/key).read_bytes()
    def exists(self,bucket,key):
        try:self.get(bucket,key); return True
        except Exception:return False
    def tamper(self,key):
        data=self.get(EVIDENCE_BUCKET,key)+b"\n[KAIRO SECURITY LAB - SIMULATED STORAGE MODIFICATION]\n"; self.put(EVIDENCE_BUCKET,key,data); return sha_bytes(data)
    def url(self,bucket,key):
        if self.s3:
            try:return self.s3.generate_presigned_url("get_object",Params={"Bucket":bucket,"Key":key},ExpiresIn=300)
            except Exception:return None
        return None
storage=Storage()

def init_db():
    with tx() as c:
        for s in SCHEMA: c.execute(text(s))
        for email,(name,role,pw) in USERS.items():
            existing=one(c.execute(text("SELECT id FROM users WHERE email=:e"),{"e":email}))
            if not existing:
                c.execute(text("INSERT INTO users(email,name,role,password_hash,active,created_at) VALUES(:e,:n,:r,:p,1,:t)"),{"e":email,"n":name,"r":role,"p":password_hash(pw),"t":now()})
            elif RESET_DEMO_PASSWORDS:
                c.execute(text("UPDATE users SET name=:n,role=:r,password_hash=:p,active=1 WHERE email=:e"),{"e":email,"n":name,"r":role,"p":password_hash(pw)})

def user_by_id(uid):
    with conn() as c:return one(c.execute(text("SELECT * FROM users WHERE id=:i AND active=1"),{"i":uid}))
def user_by_email(email):
    with conn() as c:return one(c.execute(text("SELECT * FROM users WHERE lower(email)=:e"),{"e":email.lower()}))
def token_for(u):return jwt.encode({"sub":str(u["id"]),"exp":int(time.time())+8*3600,"jti":uuid.uuid4().hex},SECRET,algorithm="HS256")
def auth(authz):
    if not authz or not authz.startswith("Bearer "):raise HTTPException(401,"Authentication required")
    try:p=jwt.decode(authz[7:],SECRET,algorithms=["HS256"])
    except Exception:raise HTTPException(401,"Invalid session")
    u=user_by_id(int(p["sub"]))
    if not u:raise HTTPException(401,"User inactive")
    return u
def require(u,perm):
    if "*" not in ROLES[u["role"]]["permissions"] and perm not in ROLES[u["role"]]["permissions"]:
        audit(u,"AUTHZ_DENIED","PERMISSION",perm,"DENIED",json.dumps({"role":u["role"]})); raise HTTPException(403,"This action is not permitted for your role")

def table_exists(name):
    with conn() as c:
        if engine.url.get_backend_name()=="sqlite": r=c.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),{"n":name}).first()
        else: r=c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name=:n"),{"n":name}).first()
    return bool(r)

def audit(actor,action,target_type,target_id,result="SUCCESS",details=""):
    with tx() as c:
        prev=one(c.execute(text("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1"))); ph=prev["event_hash"] if prev else "GENESIS"; eid="EVT-"+uuid.uuid4().hex[:12].upper(); ts=now(); payload=f"{eid}|{actor['id'] if actor else 'SYSTEM'}|{action}|{target_type}|{target_id}|{result}|{details}|{ts}|{ph}"; eh=sha_bytes(payload.encode())
        c.execute(text("INSERT INTO events(event_id,actor_id,action,target_type,target_id,result,details,created_at,prev_hash,event_hash) VALUES(:eid,:a,:ac,:tt,:tid,:r,:d,:t,:p,:h)"),{"eid":eid,"a":actor["id"] if actor else None,"ac":action,"tt":target_type,"tid":str(target_id),"r":result,"d":details,"t":ts,"p":ph,"h":eh})
    return eid,eh

def case_access(u,cid):
    if u["role"] in ("ADMIN","AUDITOR"):return
    with conn() as c:
        if not one(c.execute(text("SELECT 1 FROM members WHERE case_id=:c AND user_id=:u"),{"c":cid,"u":u["id"]})):raise HTTPException(403,"You are not assigned to this case")
def evidence_access(u,eid):
    with conn() as c:e=one(c.execute(text("SELECT * FROM evidence WHERE id=:i"),{"i":eid}))
    if not e:raise HTTPException(404,"Evidence not found")
    case_access(u,e["case_id"]);return e

def seed_demo():
    with conn() as c:
        if one(c.execute(text("SELECT id FROM cases LIMIT 1"))):return
        inv=user_by_email("investigator@kairo.local"); forensic=user_by_email("forensic@kairo.local"); legal=user_by_email("legal@kairo.local"); police=user_by_email("police@kairo.local")
    ts=now()
    with tx() as c:
        c.execute(text("INSERT INTO cases(case_no,title,description,classification,priority,status,created_by,created_at) VALUES(:n,:t,:d,'RESTRICTED','HIGH','UNDER INVESTIGATION',:u,:ts)"),{"n":"NCRB-WS-2026-0047","t":"Project Sakshi","d":"Synthetic demonstration investigation for secure evidence lifecycle.","u":inv["id"],"ts":ts}); cid=one(c.execute(text("SELECT id FROM cases WHERE case_no='NCRB-WS-2026-0047'")))["id"]
        for u in (inv,forensic,legal,police): c.execute(text("INSERT INTO members(case_id,user_id) VALUES(:c,:u)"),{"c":cid,"u":u["id"]})
    demo=[("First Information Report","FIR","FIR_Project_Sakshi.pdf"),("Witness Statement","WITNESS STATEMENT","Witness_Statement_Project_Sakshi.pdf"),("Forensic Examination Note","FORENSIC REPORT","Forensic_Report_Project_Sakshi.pdf")]
    for title,kind,fn in demo:
        p=DATA/"demo"/fn
        if not p.exists():continue
        data=p.read_bytes(); create_evidence_internal(inv,cid,title,kind,"RESTRICTED",fn,data,"DEMO_SEED")
    audit(inv,"DEMO_CASE_SEEDED","CASE",cid,details=json.dumps({"case_no":"NCRB-WS-2026-0047","synthetic":True}))

def create_evidence_internal(u,cid,title,kind,classification,filename,data,reason):
    h=sha_bytes(data); ts=now(); eno="E-"+uuid.uuid4().hex[:8].upper()
    with tx() as c:
        c.execute(text("INSERT INTO evidence(evidence_no,case_id,title,kind,classification,current_version,status,created_by,created_at) VALUES(:no,:cid,:t,:k,:cl,1,'VERIFIED',:u,:ts)"),{"no":eno,"cid":cid,"t":title,"k":kind,"cl":classification,"u":u["id"],"ts":ts}); eid=one(c.execute(text("SELECT id FROM evidence WHERE evidence_no=:n"),{"n":eno}))["id"]
        key=f"cases/{cid}/evidence/{eid}/v1/{safe_name(filename)}"; trusted=f"evidence/{eid}/v1/{safe_name(filename)}"; c.execute(text("INSERT INTO versions(evidence_id,version,filename,object_key,trusted_key,sha256,size,created_by,created_at,reason) VALUES(:e,1,:f,:o,:tr,:h,:s,:u,:t,:r)"),{"e":eid,"f":safe_name(filename),"o":key,"tr":trusted,"h":h,"s":len(data),"u":u["id"],"t":ts,"r":reason}); c.execute(text("INSERT INTO governance(evidence_id,retention_days,legal_hold,updated_at) VALUES(:e,3650,0,:t)"),{"e":eid,"t":ts})
    storage.put(EVIDENCE_BUCKET,key,data);storage.put(TRUSTED_BUCKET,trusted,data);audit(u,"EVIDENCE_REGISTERED","EVIDENCE",eid,details=json.dumps({"evidence_no":eno,"sha256":h,"version":1,"reason":reason}));return eid

@app.on_event("startup")
def startup():init_db();seed_demo()

@app.get("/api/health")
def health():
    with conn() as c: counts={k:one(c.execute(text(q)))["n"] for k,q in {"cases":"SELECT COUNT(*) n FROM cases","evidence":"SELECT COUNT(*) n FROM evidence","events":"SELECT COUNT(*) n FROM events"}.items()}
    return {"status":"ok","database":"postgresql" if engine.url.get_backend_name()!="sqlite" else "sqlite-fallback","storage":storage.mode,"integrity":"sha256","trust":"trust-anchor-ready","counts":counts}

@app.post("/api/login")
def login(body:dict):
    u=user_by_email(body.get("email","").strip());
    if not u or not password_verify(body.get("password",""),u["password_hash"]):raise HTTPException(401,"Invalid credentials")
    audit(u,"LOGIN","SESSION",u["id"]);return {"access_token":token_for(u),"user":{"id":u["id"],"email":u["email"],"name":u["name"],"role":u["role"],"department":ROLES[u["role"]]["label"]}}
@app.get("/api/me")
def me(authorization:Optional[str]=Header(None)):
    u=auth(authorization);return {"id":u["id"],"email":u["email"],"name":u["name"],"role":u["role"],"department":ROLES[u["role"]]["label"],"permissions":sorted(ROLES[u["role"]]["permissions"])}
@app.get("/api/permissions")
def permissions(authorization:Optional[str]=Header(None)):
    u=auth(authorization);return {"role":u["role"],"department":ROLES[u["role"]]["label"],"permissions":sorted(ROLES[u["role"]]["permissions"])}
@app.post("/api/logout")
def logout(authorization:Optional[str]=Header(None)):
    u=auth(authorization);audit(u,"LOGOUT","SESSION",u["id"]);return {"ok":True}

@app.post("/api/cases")
def create_case(body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"case.create"); n=body.get("case_no") or f"KAIRO-{datetime.now().year}-{secrets.randbelow(9000)+1000}"
    try:
        with tx() as c:
            c.execute(text("INSERT INTO cases(case_no,title,description,classification,priority,status,created_by,created_at) VALUES(:n,:t,:d,:cl,:p,'UNDER INVESTIGATION',:u,:ts)"),{"n":n,"t":body.get("title","Untitled Investigation"),"d":body.get("description",""),"cl":body.get("classification","RESTRICTED"),"p":body.get("priority","HIGH"),"u":u["id"],"ts":now()});cid=one(c.execute(text("SELECT id FROM cases WHERE case_no=:n"),{"n":n}))["id"];c.execute(text("INSERT INTO members(case_id,user_id) VALUES(:c,:u)"),{"c":cid,"u":u["id"]})
    except Exception as e:raise HTTPException(409,"Case number already exists or could not be created")
    audit(u,"CASE_CREATED","CASE",cid);return case_detail_data(cid)

def case_detail_data(cid):
    with conn() as c:
        ca=one(c.execute(text("SELECT * FROM cases WHERE id=:i"),{"i":cid}));ev=rows(c.execute(text("SELECT * FROM evidence WHERE case_id=:i ORDER BY id DESC"),{"i":cid}))
    if not ca:raise HTTPException(404,"Case not found");return {"case":ca,"evidence":ev}
    return {"case":ca,"evidence":ev}
@app.get("/api/cases")
def cases(authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    with conn() as c:
        q="SELECT c.* FROM cases c" if u["role"] in ("ADMIN","AUDITOR") else "SELECT c.* FROM cases c JOIN members m ON m.case_id=c.id WHERE m.user_id=:u"
        return rows(c.execute(text(q+" ORDER BY c.id DESC"),{"u":u["id"]}))
@app.get("/api/cases/{cid}")
def case_detail(cid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);case_access(u,cid);return case_detail_data(cid)
@app.post("/api/cases/{cid}/members")
def add_member(cid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"case.update");case_access(u,cid);t=user_by_email(body.get("email","") )
    if not t:raise HTTPException(404,"User not found")
    with tx() as c:c.execute(text("INSERT INTO members(case_id,user_id) SELECT :c,:u WHERE NOT EXISTS(SELECT 1 FROM members WHERE case_id=:c AND user_id=:u)"),{"c":cid,"u":t["id"]})
    audit(u,"CASE_MEMBER_ADDED","CASE",cid,details=json.dumps({"user":t["email"],"role":t["role"]}));return {"ok":True}
@app.delete("/api/cases/{cid}/members/{mid}")
def remove_member(cid:int,mid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"case.update");case_access(u,cid)
    with tx() as c:c.execute(text("DELETE FROM members WHERE case_id=:c AND user_id=:u"),{"c":cid,"u":mid})
    audit(u,"CASE_MEMBER_REMOVED","CASE",cid,details=json.dumps({"user_id":mid}));return {"ok":True}
@app.get("/api/cases/{cid}/members")
def case_members(cid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);case_access(u,cid)
    with conn() as c:return rows(c.execute(text("SELECT u.id AS user_id,u.id,u.email,u.name,u.name AS full_name,u.role,CASE WHEN u.id=(SELECT created_by FROM cases WHERE id=:c) THEN 'CASE OWNER' ELSE 'MEMBER' END AS membership_role FROM users u JOIN members m ON m.user_id=u.id WHERE m.case_id=:c ORDER BY u.name"),{"c":cid}))

@app.post("/api/cases/{cid}/evidence")
def upload(cid:int,file:UploadFile=File(...),title:str=Form(...),kind:str=Form("FIR"),classification:str=Form("RESTRICTED"),authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.create");case_access(u,cid);data=awaitable_read(file)
    if len(data)>MAX_UPLOAD:raise HTTPException(413,f"Upload exceeds {MAX_UPLOAD//1024//1024} MB")
    eid=create_evidence_internal(u,cid,title,kind,classification,file.filename,data,"REGISTERED");return evidence_detail(eid,u)

def awaitable_read(file):
    # FastAPI UploadFile is async; endpoint wrapper is converted below by using run_until_complete safely is undesirable.
    # The route is replaced at import time with an async-compatible implementation.
    raise RuntimeError("async route shim")

# Re-register the upload route with the correct async implementation.
app.router.routes.pop()
@app.post("/api/cases/{cid}/evidence")
async def upload(cid:int,file:UploadFile=File(...),title:str=Form(...),kind:str=Form("FIR"),classification:str=Form("RESTRICTED"),authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.create");case_access(u,cid);data=await file.read()
    if len(data)>MAX_UPLOAD:raise HTTPException(413,f"Upload exceeds {MAX_UPLOAD//1024//1024} MB")
    eid=create_evidence_internal(u,cid,title,kind,classification,file.filename,data,"REGISTERED");return evidence_detail(eid,u)

@app.post("/api/evidence/{eid}/versions")
async def new_version(eid:int,file:UploadFile=File(...),reason:str=Form("Authorized update"),authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.create");e=evidence_access(u,eid);data=await file.read()
    if len(data)>MAX_UPLOAD:raise HTTPException(413,f"Upload exceeds {MAX_UPLOAD//1024//1024} MB")
    with conn() as c:latest=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e ORDER BY version DESC LIMIT 1"),{"e":eid}))
    v=latest["version"]+1;h=sha_bytes(data);fn=safe_name(file.filename);key=f"cases/{e['case_id']}/evidence/{eid}/v{v}/{fn}";trusted=f"evidence/{eid}/v{v}/{fn}";ts=now()
    with tx() as c:
        c.execute(text("INSERT INTO versions(evidence_id,version,filename,object_key,trusted_key,sha256,size,created_by,created_at,reason) VALUES(:e,:v,:f,:o,:tr,:h,:s,:u,:t,:r)"),{"e":eid,"v":v,"f":fn,"o":key,"tr":trusted,"h":h,"s":len(data),"u":u["id"],"t":ts,"r":reason});c.execute(text("UPDATE evidence SET current_version=:v,status='VERIFIED' WHERE id=:e"),{"v":v,"e":eid})
    storage.put(EVIDENCE_BUCKET,key,data);storage.put(TRUSTED_BUCKET,trusted,data);audit(u,"EVIDENCE_VERSION_CREATED","EVIDENCE",eid,details=json.dumps({"version":v,"reason":reason,"sha256":h}));return evidence_detail(eid,u)

def evidence_detail(eid,u):
    e=evidence_access(u,eid)
    with conn() as c:
        vs=rows(c.execute(text("SELECT v.*,u.name creator FROM versions v LEFT JOIN users u ON u.id=v.created_by WHERE evidence_id=:e ORDER BY version ASC"),{"e":eid}));inc=rows(c.execute(text("SELECT * FROM incidents WHERE evidence_id=:e ORDER BY id DESC"),{"e":eid}));tr=rows(c.execute(text("SELECT * FROM trust WHERE evidence_id=:e ORDER BY id DESC"),{"e":eid}));sigs=rows(c.execute(text("SELECT s.*,u.name signer_name FROM signatures s JOIN users u ON u.id=s.signer_id WHERE evidence_id=:e ORDER BY s.id DESC"),{"e":eid}))
    return {"evidence":e,"versions":vs,"incidents":inc,"trust":tr,"signatures":sigs}
@app.get("/api/evidence/{eid}")
def get_evidence(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.read");return evidence_detail(eid,u)
@app.get("/api/evidence/{eid}/download")
def download_version(eid:int,version:int=0,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.read");e=evidence_access(u,eid)
    with conn() as c:v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":version or e["current_version"]}))
    if not v:raise HTTPException(404,"Version not found")
    data=storage.get(EVIDENCE_BUCKET,v["object_key"]);audit(u,"EVIDENCE_ACCESSED","EVIDENCE",eid,details=json.dumps({"version":v["version"]}));return StreamingResponse(io.BytesIO(data),media_type="application/octet-stream",headers={"Content-Disposition":f'attachment; filename="{v["filename"]}"'})
@app.post("/api/evidence/{eid}/verify")
def verify(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.verify");e=evidence_access(u,eid)
    with conn() as c:v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}))
    try:observed=sha_bytes(storage.get(EVIDENCE_BUCKET,v["object_key"]))
    except Exception:raise HTTPException(503,"Evidence storage object unavailable")
    result="VERIFIED" if observed==v["sha256"] else "MISMATCH";audit(u,"INTEGRITY_VERIFIED" if result=="VERIFIED" else "INTEGRITY_MISMATCH","EVIDENCE",eid,result,details=json.dumps({"version":v["version"],"expected":v["sha256"],"observed":observed}))
    if result=="MISMATCH":
        with tx() as c:
            open_inc=one(c.execute(text("SELECT id FROM incidents WHERE evidence_id=:e AND status='OPEN'"),{"e":eid}))
            if not open_inc:c.execute(text("INSERT INTO incidents(incident_no,evidence_id,expected_hash,observed_hash,status,detected_at,details) VALUES(:n,:e,:x,:o,'OPEN',:t,:d)"),{"n":"INC-"+uuid.uuid4().hex[:8].upper(),"e":eid,"x":v["sha256"],"o":observed,"t":now(),"d":"Stored evidence bytes differ from registered fingerprint."})
            c.execute(text("UPDATE evidence SET status='INTEGRITY INCIDENT' WHERE id=:e"),{"e":eid})
    return {"result":result,"verified":result=="VERIFIED","expected":v["sha256"],"observed":observed,"expected_sha256":v["sha256"],"observed_sha256":observed,"version":v["version"],"evidence_no":e["evidence_no"]}
@app.post("/api/evidence/{eid}/restore")
def restore(eid:int,version:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.restore");e=evidence_access(u,eid)
    with conn() as c:src=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":version}));cur=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}))
    if not src:raise HTTPException(404,"Trusted version not found")
    try:data=storage.get(TRUSTED_BUCKET,src["trusted_key"])
    except Exception:raise HTTPException(404,"Protected trusted copy unavailable")
    if sha_bytes(data)!=src["sha256"]:raise HTTPException(409,"Trusted copy failed fingerprint verification")
    nv=cur["version"]+1;fn=src["filename"];key=f"cases/{e['case_id']}/evidence/{eid}/v{nv}/{fn}";trusted=f"evidence/{eid}/v{nv}/{fn}";ts=now()
    with tx() as c:
        c.execute(text("INSERT INTO versions(evidence_id,version,filename,object_key,trusted_key,sha256,size,created_by,created_at,restored_from,reason) VALUES(:e,:v,:f,:o,:tr,:h,:s,:u,:t,:rf,'Integrity recovery')"),{"e":eid,"v":nv,"f":fn,"o":key,"tr":trusted,"h":src["sha256"],"s":len(data),"u":u["id"],"t":ts,"rf":src["version"]});c.execute(text("UPDATE evidence SET current_version=:v,status='VERIFIED' WHERE id=:e"),{"v":nv,"e":eid});c.execute(text("UPDATE incidents SET status='RESOLVED',resolved_at=:t,resolved_by=:u WHERE evidence_id=:e AND status='OPEN'"),{"t":ts,"u":u["id"],"e":eid})
    storage.put(EVIDENCE_BUCKET,key,data);storage.put(TRUSTED_BUCKET,trusted,data);audit(u,"EVIDENCE_RESTORED","EVIDENCE",eid,details=json.dumps({"from_version":src["version"],"new_version":nv,"sha256":src["sha256"]}));return evidence_detail(eid,u)

@app.get("/api/audit")
def audit_list(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"audit.read")
    with conn() as c:return rows(c.execute(text("SELECT e.*,u.name actor,u.email actor_email FROM events e LEFT JOIN users u ON u.id=e.actor_id ORDER BY e.id DESC LIMIT 500")))
@app.get("/api/incidents")
def incidents(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"incident.read")
    with conn() as c:return rows(c.execute(text("SELECT i.*,e.evidence_no,e.title FROM incidents i JOIN evidence e ON e.id=i.evidence_id ORDER BY i.id DESC")))
@app.post("/api/incidents/{iid}/resolve")
def resolve_incident(iid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.restore")
    with tx() as c:c.execute(text("UPDATE incidents SET status='RESOLVED',resolved_at=:t,resolved_by=:u,details=COALESCE(details,'') || :d WHERE id=:i"),{"t":now(),"u":u["id"],"i":iid,"d":"\nResolution: "+str(body.get("resolution","Reviewed"))})
    audit(u,"INCIDENT_RESOLVED","INCIDENT",iid);return {"ok":True}

@app.get("/api/trust/ledger")
def trust_ledger(limit:int=50,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"trust.read")
    with conn() as c:
        evs=rows(c.execute(text("SELECT * FROM events ORDER BY id DESC LIMIT :l"),{"l":min(limit,200)}))
    blocks=[]
    for e in evs:
        blocks.append({"block_index":e["id"],"action":e["action"],"target_type":e["target_type"],"target_id":e["target_id"],"result":e["result"],"transaction_id":e["event_id"],"event_hash":e["event_hash"],"previous_hash":e["prev_hash"],"created_at":e["created_at"],"details":e["details"]})
    blocks.sort(key=lambda x:x["block_index"],reverse=True)
    verified=verify_event_chain()
    return {"status":{"verified":verified,"blocks":len(blocks),"latest_block":blocks[0]["block_index"] if blocks else 0},"blocks":blocks,"provider":"local-hash-chain"}

def verify_event_chain():
    with conn() as c: evs=rows(c.execute(text("SELECT * FROM events ORDER BY id ASC")))
    previous="GENESIS"
    for e in evs:
        payload=f"{e['event_id']}|{e['actor_id'] if e['actor_id'] is not None else 'SYSTEM'}|{e['action']}|{e['target_type']}|{e['target_id']}|{e['result']}|{e['details'] or ''}|{e['created_at']}|{previous}"
        expected=sha_bytes(payload.encode())
        if e["prev_hash"]!=previous or e["event_hash"]!=expected:return False
        previous=e["event_hash"]
    return True

@app.get("/api/trust/verify")
def trust_verify(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"trust.read")
    with conn() as c:count=one(c.execute(text("SELECT COUNT(*) n FROM events")))['n']
    return {"verified":verify_event_chain(),"blocks":count,"latest_block":count,"provider":"local-hash-chain"}
@app.get("/api/trust")
def trust_list(authorization:Optional[str]=Header(None)):return trust_ledger(50,authorization)
@app.post("/api/trust/anchor/{eid}")
def trust_anchor(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.verify");e=evidence_access(u,eid)
    with conn() as c:v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}));ev=one(c.execute(text("SELECT event_hash FROM events WHERE target_type='EVIDENCE' AND target_id=:i ORDER BY id DESC LIMIT 1"),{"i":str(eid)}))
    anchor="ANCHOR-"+uuid.uuid4().hex[:12].upper();eh=ev["event_hash"] if ev else "NONE";proof=sha_bytes(f"{e['evidence_no']}|{v['version']}|{v['sha256']}|{eh}|{anchor}".encode());provider=os.getenv("KAIRO_TRUST_PROVIDER","local-permissioned-trust")
    with tx() as c:c.execute(text("INSERT INTO trust(evidence_id,version,sha256,event_hash,anchor_id,proof,provider,created_at) VALUES(:e,:v,:s,:eh,:a,:p,:pr,:t)"),{"e":eid,"v":v["version"],"s":v["sha256"],"eh":eh,"a":anchor,"p":proof,"pr":provider,"t":now()})
    audit(u,"TRUST_ANCHORED","EVIDENCE",eid,details=json.dumps({"anchor_id":anchor,"provider":provider,"proof":proof}));return {"anchor_id":anchor,"proof":proof,"provider":provider,"mode":provider}
@app.get("/api/documents/{eid}/trust")
def document_trust(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"trust.read");e=evidence_access(u,eid)
    with conn() as c:
        anchors=rows(c.execute(text("SELECT * FROM trust WHERE evidence_id=:e ORDER BY id DESC"),{"e":eid}))
    for a in anchors:
        a.setdefault("block_index",a["id"]);a.setdefault("action","TRUST_ANCHORED");a.setdefault("event_hash",a.get("event_hash") or a.get("proof") or "");a.setdefault("transaction_id",a.get("anchor_id",""))
    return {"evidence_id":eid,"evidence_no":e["evidence_no"],"anchors":anchors,"anchored":bool(anchors)}

@app.post("/api/attack/tamper")
def attack(body:dict,x_kairo_lab_key:Optional[str]=Header(None)):
    if x_kairo_lab_key!=ATTACK_KEY:raise HTTPException(403,"Security Lab key required")
    eid=int(body.get("evidence_id"));version=int(body.get("version",0))
    with conn() as c:v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":version}))
    if not v:raise HTTPException(404,"Target version not found")
    try:newsha=storage.tamper(v["object_key"])
    except Exception as ex:raise HTTPException(503,f"Storage tamper simulation failed: {ex}")
    audit(None,"SECURITY_LAB_TAMPER","EVIDENCE",eid,"SIMULATED",json.dumps({"version":version,"source":"attackvector CLI"}));return {"ok":True,"evidence_id":eid,"version":version,"new_sha256":newsha,"message":"Controlled storage modification applied"}

@app.get("/api/search")
def search(q:str="",limit:int=50,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.read");like=f"%{q}%"
    with conn() as c:
        if u["role"] in ("ADMIN","AUDITOR"):sql="SELECT e.*,c.case_no,c.title case_title,v.filename,v.sha256 FROM evidence e JOIN cases c ON c.id=e.case_id LEFT JOIN versions v ON v.evidence_id=e.id AND v.version=e.current_version WHERE e.title LIKE :q OR e.evidence_no LIKE :q OR e.kind LIKE :q ORDER BY e.id DESC LIMIT :l"
        else:sql="SELECT e.*,c.case_no,c.title case_title,v.filename,v.sha256 FROM evidence e JOIN cases c ON c.id=e.case_id JOIN members m ON m.case_id=c.id LEFT JOIN versions v ON v.evidence_id=e.id AND v.version=e.current_version WHERE m.user_id=:u AND (e.title LIKE :q OR e.evidence_no LIKE :q OR e.kind LIKE :q) ORDER BY e.id DESC LIMIT :l"
        return rows(c.execute(text(sql),{"q":like,"u":u["id"],"l":min(limit,200)}))

@app.get("/api/users/collaborators")
def collaborators(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.share")
    with conn() as c:return rows(c.execute(text("SELECT id,email,name,role FROM users WHERE active=1 AND id<>:i ORDER BY name"),{"i":u["id"]}))
@app.post("/api/documents/{eid}/shares")
def share(eid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"evidence.share");e=evidence_access(u,eid);to=user_by_email(body.get("email",""));
    if not to:raise HTTPException(404,"Recipient not found")
    exp=body.get("expires_at") or (datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()
    with tx() as c:c.execute(text("INSERT INTO shares(evidence_id,from_user,to_user,expires_at,status,created_at) VALUES(:e,:f,:t,:x,'ACTIVE',:n)"),{"e":eid,"f":u["id"],"t":to["id"],"x":exp,"n":now()});sid=one(c.execute(text("SELECT id FROM shares WHERE evidence_id=:e AND from_user=:f AND to_user=:t ORDER BY id DESC LIMIT 1"),{"e":eid,"f":u["id"],"t":to["id"]}))["id"]
    audit(u,"EVIDENCE_SHARED","EVIDENCE",eid,details=json.dumps({"share_id":sid,"recipient":to["email"],"expires_at":exp}));return {"id":sid,"status":"ACTIVE","expires_at":exp}
@app.get("/api/shares/incoming")
def incoming(authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    with conn() as c:return rows(c.execute(text("SELECT s.*,e.evidence_no,e.title,u.name sender FROM shares s JOIN evidence e ON e.id=s.evidence_id JOIN users u ON u.id=s.from_user WHERE s.to_user=:u AND s.status='ACTIVE' ORDER BY s.id DESC"),{"u":u["id"]}))
@app.get("/api/shares/outgoing")
def outgoing(authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    with conn() as c:return rows(c.execute(text("SELECT s.*,e.evidence_no,e.title,u.name recipient FROM shares s JOIN evidence e ON e.id=s.evidence_id JOIN users u ON u.id=s.to_user WHERE s.from_user=:u ORDER BY s.id DESC"),{"u":u["id"]}))
@app.get("/api/shares/{sid}")
def share_record(sid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    with conn() as c:r=one(c.execute(text("SELECT * FROM shares WHERE id=:i"),{"i":sid}))
    if not r or (r["from_user"]!=u["id"] and r["to_user"]!=u["id"]):raise HTTPException(404,"Share not found")
    if r["expires_at"] and r["expires_at"]<now() and r["status"]=="ACTIVE":
        with tx() as c:c.execute(text("UPDATE shares SET status='EXPIRED' WHERE id=:i"),{"i":sid});r["status"]="EXPIRED"
    return r
@app.post("/api/shares/{sid}/revoke")
def revoke_share(sid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    with tx() as c:r=one(c.execute(text("SELECT * FROM shares WHERE id=:i AND from_user=:u"),{"i":sid,"u":u["id"]}));
    if not r:raise HTTPException(404,"Share not found")
    with tx() as c:c.execute(text("UPDATE shares SET status='REVOKED' WHERE id=:i"),{"i":sid})
    audit(u,"SHARE_REVOKED","SHARE",sid);return {"ok":True}
@app.get("/api/shares/{sid}/download")
def shared_download(sid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);r=share_record(sid,authorization)
    if r["status"]!="ACTIVE":raise HTTPException(403,"Share is not active")
    e=evidence_access(u,r["evidence_id"]);return download_version(r["evidence_id"],e["current_version"],authorization)

@app.post("/api/documents/{eid}/sign")
def sign(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"report.create");e=evidence_access(u,eid)
    with conn() as c:
        v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}))
        existing=one(c.execute(text("SELECT s.*,u.email signer_email FROM signatures s JOIN users u ON u.id=s.signer_id WHERE s.evidence_id=:e AND s.version=:v ORDER BY s.id DESC LIMIT 1"),{"e":eid,"v":e["current_version"]}))
    if existing:return {"ok":True,"existing":True,"signature":existing["signature"],"algorithm":existing["algorithm"],"version":existing["version"],"signer_email":existing["signer_email"]}
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        seed=hashlib.sha256((SECRET+str(u["id"])).encode()).digest();key=ed25519.Ed25519PrivateKey.from_private_bytes(seed);sig=key.sign(v["sha256"].encode()).hex();algo="Ed25519/SHA-256 evidence fingerprint"
    except Exception: sig=hashlib.sha256((SECRET+v["sha256"]+str(u["id"])).encode()).hexdigest();algo="HMAC-like prototype signature"
    with tx() as c:c.execute(text("INSERT INTO signatures(evidence_id,version,signer_id,signature,algorithm,created_at) VALUES(:e,:v,:s,:g,:a,:t)"),{"e":eid,"v":v["version"],"s":u["id"],"g":sig,"a":algo,"t":now()})
    audit(u,"EVIDENCE_SIGNED","EVIDENCE",eid);return {"ok":True,"existing":False,"signature":sig,"algorithm":algo,"version":v["version"],"signer_email":u["email"]}
@app.get("/api/documents/{eid}/signatures")
def signatures(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);evidence_access(u,eid)
    with conn() as c:return rows(c.execute(text("SELECT s.*,u.name signer_name,u.email signer_email FROM signatures s JOIN users u ON u.id=s.signer_id WHERE s.evidence_id=:e ORDER BY s.id DESC"),{"e":eid}))
@app.post("/api/documents/{eid}/signatures/{sid}/verify")
def verify_signature(eid:int,sid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);e=evidence_access(u,eid)
    with conn() as c:s=one(c.execute(text("SELECT * FROM signatures WHERE id=:i AND evidence_id=:e"),{"i":sid,"e":eid}));v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":s["version"] if s else -1}))
    if not s or not v:raise HTTPException(404,"Signature not found")
    valid=False
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        seed=hashlib.sha256((SECRET+str(s["signer_id"])).encode()).digest();key=ed25519.Ed25519PrivateKey.from_private_bytes(seed);key.public_key().verify(bytes.fromhex(s["signature"]),v["sha256"].encode());valid=True
    except Exception:valid=False
    audit(u,"SIGNATURE_VERIFIED","EVIDENCE",eid,"VERIFIED" if valid else "FAILED");return {"valid":valid,"verified":valid,"signature_id":sid,"version":s["version"]}

@app.get("/api/documents/{eid}/custody")
def custody(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);e=evidence_access(u,eid)
    with conn() as c:
        evs=rows(c.execute(text("SELECT e.*,u.name actor_name,u.email actor_email,u.role actor_role FROM events e LEFT JOIN users u ON u.id=e.actor_id WHERE e.target_type='EVIDENCE' AND e.target_id=:i ORDER BY e.id ASC"),{"i":str(eid)}))
        inc=one(c.execute(text("SELECT * FROM incidents WHERE evidence_id=:e AND status='OPEN' ORDER BY id DESC LIMIT 1"),{"e":eid}))
    if inc:
        status="INTEGRITY_INCIDENT"; explanation="Stored evidence bytes differ from the registered fingerprint. Review the incident and restore a trusted version if appropriate."
    else:
        status="CONTROLLED"; explanation="Evidence actions are represented by authenticated custody events. Legitimate changes create new immutable versions."
    actor_event=next((x for x in reversed(evs) if x.get("actor_id") is not None and x.get("action") in {"EVIDENCE_REGISTERED","EVIDENCE_VERSION_CREATED","EVIDENCE_RESTORED","EVIDENCE_ACCESSED","EVIDENCE_SIGNED","EVIDENCE_SEALED"}),None)
    actor=None; authorized=None
    if actor_event:
        actor={"full_name":actor_event.get("actor_name"),"email":actor_event.get("actor_email"),"role":actor_event.get("actor_role")}
        try:details=json.loads(actor_event.get("details") or "{}")
        except Exception:details={}
        authorized={"actor":actor,"action":actor_event.get("action"),"permission":"server policy","version":details.get("version") or e["current_version"],"timestamp":actor_event.get("created_at")}
    return {"status":status,"explanation":explanation,"authorized_change":authorized,"events":evs,"incident":inc}

@app.post("/api/documents/{eid}/seal")
def seal(eid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"forensic.write");e=evidence_access(u,eid);v=int(body.get("version",e["current_version"]))
    with tx() as c:c.execute(text("UPDATE governance SET sealed_version=:v,updated_at=:t WHERE evidence_id=:e"),{"v":v,"t":now(),"e":eid})
    audit(u,"EVIDENCE_SEALED","EVIDENCE",eid);return {"ok":True,"sealed_version":v}
@app.get("/api/documents/{eid}/governance")
def governance(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);e=evidence_access(u,eid)
    with conn() as c:g=one(c.execute(text("SELECT * FROM governance WHERE evidence_id=:e"),{"e":eid}))
    if not g:g={"evidence_id":eid,"retention_days":3650,"legal_hold":0,"hold_reason":"","sealed_version":None}
    retain_until=(datetime.now(timezone.utc)+timedelta(days=int(g.get("retention_days") or 3650))).isoformat()
    return {"evidence_id":eid,"retention":{"retain_until":retain_until,"retention_days":g.get("retention_days"),"reason":"Investigation retention requirement"},"legal_hold":{"active":bool(g.get("legal_hold")),"reason":g.get("hold_reason") or ""},"sealed":bool(g.get("sealed_version")),"sealed_version":g.get("sealed_version")}
@app.get("/api/governance/summary")
def governance_summary(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"governance.read")
    with conn() as c:
        holds=one(c.execute(text("SELECT COUNT(*) n FROM governance WHERE legal_hold=1")))["n"]
        policies=one(c.execute(text("SELECT COUNT(*) n FROM governance WHERE retention_days IS NOT NULL")))["n"]
        sigs=one(c.execute(text("SELECT COUNT(*) n FROM signatures")))["n"]
        shares=one(c.execute(text("SELECT COUNT(*) n FROM shares WHERE status='ACTIVE' AND (expires_at IS NULL OR expires_at>:t)"),{"t":now()}))["n"]
    return {"records":policies,"active_legal_holds":holds,"retention_policies":policies,"signatures":sigs,"active_shares":shares}
@app.post("/api/documents/{eid}/retention")
def retention(eid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);e=evidence_access(u,eid)
    if u["role"] not in ("ADMIN","AUDITOR"):raise HTTPException(403,"Governance policy administration is restricted")
    if body.get("retain_until"):
        until=datetime.fromisoformat(str(body["retain_until"]).replace("Z","+00:00"));days=max(1,int((until-datetime.now(timezone.utc)).total_seconds()/86400))
    else:days=int(body.get("retention_days",3650))
    with tx() as c:c.execute(text("UPDATE governance SET retention_days=:d,updated_at=:t WHERE evidence_id=:e"),{"d":days,"t":now(),"e":eid})
    audit(u,"RETENTION_UPDATED","EVIDENCE",eid,details=json.dumps({"retention_days":days,"reason":body.get("reason","Investigation retention requirement")}));return governance(eid,authorization)
@app.post("/api/documents/{eid}/legal-hold")
def legal_hold(eid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);e=evidence_access(u,eid)
    if u["role"] not in ("ADMIN","AUDITOR","LEGAL"):raise HTTPException(403,"Legal hold authority required")
    enabled=1 if body.get("enabled",True) else 0
    with tx() as c:c.execute(text("UPDATE governance SET legal_hold=:h,hold_reason=:r,updated_at=:t WHERE evidence_id=:e"),{"h":enabled,"r":body.get("reason",""),"t":now(),"e":eid})
    audit(u,"LEGAL_HOLD_UPDATED","EVIDENCE",eid);return governance(eid,authorization)
@app.post("/api/governance/retention/scan")
def retention_scan(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"audit.read");return {"eligible":0,"held":0,"action":"No automatic deletion performed; disposition remains explicit."}
@app.get("/api/governance/dispositions")
def dispositions(authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"audit.read");return []

@app.get("/api/documents/{eid}/intelligence")
def intelligence(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"intelligence.read");e=evidence_access(u,eid)
    with conn() as c:
        v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}))
        vs=rows(c.execute(text("SELECT version,filename,sha256,created_at FROM versions WHERE evidence_id=:e ORDER BY version"),{"e":eid}))
        g=one(c.execute(text("SELECT * FROM governance WHERE evidence_id=:e"),{"e":eid}))
        red=one(c.execute(text("SELECT COUNT(*) n FROM redactions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]})) if table_exists("redactions") else {"n":0}
    data=storage.get(EVIDENCE_BUCKET,v["object_key"]);txt=data.decode("utf-8","ignore")[:200000];patterns={"email":r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}","phone":r"\b(?:\+91[- ]?)?[6-9]\d{9}\b","id_reference":r"\b(?:FIR|CASE|EVIDENCE)[-_A-Z0-9]+\b"};findings={k:re.findall(p,txt,re.I) for k,p in patterns.items()};count=sum(len(x) for x in findings.values());
    return {"document_number":e["evidence_no"],"document_type":e["kind"],"classification":e["classification"],"ai_classification":e["kind"],"ai_confidence":0.98,"extraction_method":"deterministic text extraction","extracted_text":txt,"extracted_text_preview":txt[:12000],"redaction_count":int(red["n"] if red else 0),"findings":findings,"sealed":bool(g and g.get("sealed_version") and g.get("sealed_version")>=e["current_version"]),"current_version":e["current_version"],"versions":vs,"merkle_root":v["sha256"]}
@app.post("/api/documents/{eid}/redact")
def redact(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"forensic.write");e=evidence_access(u,eid)
    with conn() as c:v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}))
    data=storage.get(EVIDENCE_BUCKET,v["object_key"]);txt=data.decode("utf-8","ignore")
    patterns=[r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",r"\b(?:\+91[- ]?)?[6-9]\d{9}\b"]
    redacted=txt;count=0
    for pat in patterns:
        redacted,n=re.subn(pat,"[REDACTED]",redacted);count+=n
    key=f"derivatives/redacted/evidence/{eid}/v{v['version']}/{safe_name(v['filename'])}.redacted.txt"
    storage.put(EVIDENCE_BUCKET,key,redacted.encode())
    with tx() as c:c.execute(text("INSERT INTO redactions(evidence_id,version,object_key,count,created_by,created_at) VALUES(:e,:v,:o,:c,:u,:t)"),{"e":eid,"v":v["version"],"o":key,"c":count,"u":u["id"],"t":now()})
    audit(u,"REDACTION_COPY_CREATED","EVIDENCE",eid,details=json.dumps({"version":v["version"],"count":count}));return {"ok":True,"count":count,"evidence_id":eid,"version":v["version"]}
@app.get("/api/documents/{eid}/redacted")
def redacted(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"forensic.write");e=evidence_access(u,eid)
    with conn() as c:r=one(c.execute(text("SELECT * FROM redactions WHERE evidence_id=:e ORDER BY id DESC LIMIT 1"),{"e":eid}))
    if not r:raise HTTPException(404,"No redacted derivative exists yet")
    data=storage.get(EVIDENCE_BUCKET,r["object_key"]);return StreamingResponse(io.BytesIO(data),media_type="text/plain",headers={"Content-Disposition":f'attachment; filename="REDACTED-EVIDENCE-{eid}.txt"'})
@app.post("/api/documents/{eid}/seal")
def seal(eid:int,body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"forensic.write");e=evidence_access(u,eid);v=int(body.get("version",e["current_version"]))
    with tx() as c:c.execute(text("UPDATE governance SET sealed_version=:v,updated_at=:t WHERE evidence_id=:e"),{"v":v,"t":now(),"e":eid})
    audit(u,"EVIDENCE_SEALED","EVIDENCE",eid);return {"ok":True,"sealed_version":v}
@app.post("/api/documents/{eid}/tamper-demo")
def tamper_demo(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"forensic.write");e=evidence_access(u,eid)
    # same controlled lab operation, only exposed to privileged forensic/admin users.
    with conn() as c:v=one(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e AND version=:v"),{"e":eid,"v":e["current_version"]}))
    newsha=storage.tamper(v["object_key"]);audit(u,"SECURITY_LAB_TAMPER","EVIDENCE",eid,"SIMULATED");return {"ok":True,"new_sha256":newsha}
@app.delete("/api/documents/{eid}")
def delete_document(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);e=evidence_access(u,eid)
    if u["role"]!="ADMIN":raise HTTPException(403,"Evidence deletion is restricted to system administration and policy controls")
    with tx() as c:c.execute(text("UPDATE evidence SET status='DISPOSITION PENDING' WHERE id=:e"),{"e":eid})
    audit(u,"EVIDENCE_DISPOSITION_REQUESTED","EVIDENCE",eid);return {"ok":True,"status":"DISPOSITION PENDING"}
@app.get("/api/documents/{eid}/download")
def document_download(eid:int,authorization:Optional[str]=Header(None)):e=download_version(eid,0,authorization);return e
@app.get("/api/documents/{eid}/blockchain-anchor")
def blockchain_anchor_read(eid:int,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"trust.read");e=evidence_access(u,eid)
    with conn() as c:return one(c.execute(text("SELECT * FROM trust WHERE evidence_id=:e ORDER BY id DESC LIMIT 1"),{"e":eid})) or {"anchored":False}
@app.post("/api/documents/{eid}/blockchain-anchor")
def blockchain_anchor(eid:int,authorization:Optional[str]=Header(None)):return trust_anchor(eid,authorization)
@app.get("/api/blockchain/status")
def blockchain_status(authorization:Optional[str]=Header(None)):
    auth(authorization);return {"provider":os.getenv("KAIRO_TRUST_PROVIDER","local-permissioned-trust"),"network":"ready","mode":"adapter","fabric_connected":False,"message":"Use KAIRO_TRUST_PROVIDER=fabric when the Fabric gateway is deployed."}
@app.get("/api/security/posture")
def security_posture(authorization:Optional[str]=Header(None)):
    u=auth(authorization);return {"rbac":"server-enforced","case_membership":"server-enforced","integrity":"sha256","audit":"hash-chained","storage":storage.mode,"max_upload_mb":MAX_UPLOAD//1024//1024}
@app.get("/api/documents/{eid}/forensic-export")
def forensic_export(eid:int,include_bytes:bool=False,authorization:Optional[str]=Header(None)):
    u=auth(authorization);require(u,"report.create");e=evidence_access(u,eid)
    with conn() as c:vs=rows(c.execute(text("SELECT * FROM versions WHERE evidence_id=:e ORDER BY version"),{"e":eid}));events=rows(c.execute(text("SELECT * FROM events WHERE target_type='EVIDENCE' AND target_id=:i ORDER BY id"),{"i":str(eid)}));inc=rows(c.execute(text("SELECT * FROM incidents WHERE evidence_id=:e"),{"e":eid}))
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json",json.dumps({"evidence":e,"versions":vs,"custody":events,"incidents":inc},indent=2,default=str))
        if include_bytes:
            for v in vs:
                data=storage.get(EVIDENCE_BUCKET,v["object_key"])
                if sha_bytes(data)!=v["sha256"]:
                    raise HTTPException(409,f"Evidence version {v['version']} failed integrity verification; export refused")
                z.writestr(f"evidence/v{v['version']}/{v['filename']}",data)
    buf.seek(0);audit(u,"FORENSIC_EXPORT_CREATED","EVIDENCE",eid);return StreamingResponse(buf,media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="KAIRO-DOC-{eid:05d}-forensic-package.zip"'})

@app.get("/api/admin/users")
def admin_users(authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    if u["role"]!="ADMIN":raise HTTPException(403,"Administrator access required")
    with conn() as c:return rows(c.execute(text("SELECT id,email,name,role,active,created_at FROM users ORDER BY name")))
@app.post("/api/admin/users")
def admin_create_user(body:dict,authorization:Optional[str]=Header(None)):
    u=auth(authorization)
    if u["role"]!="ADMIN":raise HTTPException(403,"Administrator access required")
    role=body.get("role","POLICE").upper()
    if role not in ROLES:raise HTTPException(400,"Invalid role")
    with tx() as c:c.execute(text("INSERT INTO users(email,name,role,password_hash,active,created_at) VALUES(:e,:n,:r,:p,1,:t)"),{"e":body["email"].lower(),"n":body["name"],"r":role,"p":password_hash(body["password"]),"t":now()})
    audit(u,"USER_CREATED","USER",body["email"]);return {"ok":True}

FRONT=ROOT/"frontend"/"dist"
if FRONT.exists():app.mount("/",StaticFiles(directory=FRONT,html=True),name="frontend")
