from datetime import datetime, timezone
from pathlib import Path
import base64, hashlib, json, secrets
from sqlalchemy import text

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError:  # handled by API with a clear message
    hashes = serialization = padding = rsa = None

KEY_DIR = Path(__file__).resolve().parent.parent / 'keys'


def ensure_governance(db):
    db.execute(text('''CREATE TABLE IF NOT EXISTS document_shares (
        id SERIAL PRIMARY KEY, document_id INTEGER NOT NULL, shared_by INTEGER NOT NULL,
        shared_with INTEGER NOT NULL, permission VARCHAR(20) NOT NULL DEFAULT 'VIEW',
        expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ NULL, token_hash VARCHAR(64) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )'''))
    db.execute(text('''CREATE TABLE IF NOT EXISTS document_signatures (
        id SERIAL PRIMARY KEY, document_id INTEGER NOT NULL, version INTEGER NOT NULL,
        signer_id INTEGER NOT NULL, algorithm VARCHAR(80) NOT NULL, signature_b64 TEXT NOT NULL,
        public_key_pem TEXT NOT NULL, signed_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )'''))
    db.execute(text('''CREATE TABLE IF NOT EXISTS retention_policies (
        id SERIAL PRIMARY KEY, document_id INTEGER UNIQUE NOT NULL, retain_until TIMESTAMPTZ NOT NULL,
        reason TEXT NOT NULL DEFAULT '', updated_by INTEGER NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )'''))
    db.execute(text('''CREATE TABLE IF NOT EXISTS legal_holds (
        id SERIAL PRIMARY KEY, document_id INTEGER UNIQUE NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
        reason TEXT NOT NULL, placed_by INTEGER NOT NULL, placed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        released_by INTEGER NULL, released_at TIMESTAMPTZ NULL
    )'''))
    db.commit()


def _key_path(user_id):
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    return KEY_DIR / f'user_{user_id}.pem'


def _get_private_key(user_id):
    if rsa is None:
        raise RuntimeError('cryptography package is required for digital signatures')
    p = _key_path(user_id)
    if p.exists():
        return serialization.load_pem_private_key(p.read_bytes(), password=None)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    p.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try: p.chmod(0o600)
    except OSError: pass
    return key


def sign_hash(user_id, digest):
    key = _get_private_key(user_id)
    sig = key.sign(digest.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return base64.b64encode(sig).decode(), pub


def verify_signature(signature_b64, public_key_pem, digest):
    if serialization is None:
        raise RuntimeError('cryptography package is required for digital signatures')
    pub = serialization.load_pem_public_key(public_key_pem.encode())
    pub.verify(base64.b64decode(signature_b64), digest.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return True


def create_share(db, document_id, shared_by, shared_with, permission, expires_at):
    raw = secrets.token_urlsafe(32)
    h = hashlib.sha256(raw.encode()).hexdigest()
    row = db.execute(text('''INSERT INTO document_shares(document_id,shared_by,shared_with,permission,expires_at,token_hash)
        VALUES(:d,:b,:w,:p,:e,:h) RETURNING id,created_at'''), {'d':document_id,'b':shared_by,'w':shared_with,'p':permission,'e':expires_at,'h':h}).mappings().one()
    db.commit()
    return {**dict(row), 'token': raw}


def list_shares(db, user_id, document_id=None, incoming=False):
    where = 's.shared_with=:u' if incoming else 's.shared_by=:u'
    params={'u':user_id}
    extra=''
    if document_id is not None: extra=' AND s.document_id=:d'; params['d']=document_id
    return [dict(r) for r in db.execute(text(f'''SELECT s.*, u1.email AS shared_by_email, u2.email AS shared_with_email
        FROM document_shares s JOIN users u1 ON u1.id=s.shared_by JOIN users u2 ON u2.id=s.shared_with
        WHERE {where}{extra} ORDER BY s.created_at DESC'''), params).mappings().all()]


def revoke_share(db, share_id, user_id):
    row=db.execute(text('UPDATE document_shares SET revoked_at=NOW() WHERE id=:i AND shared_by=:u RETURNING id'), {'i':share_id,'u':user_id}).mappings().first()
    db.commit(); return dict(row) if row else None


def sign_record(db, document_id, version, signer_id, digest):
    existing = db.execute(text('''SELECT * FROM document_signatures
        WHERE document_id=:d AND version=:v AND signer_id=:s AND signed_hash=:h
        ORDER BY id DESC LIMIT 1'''), {'d':document_id, 'v':version, 's':signer_id, 'h':digest}).mappings().first()
    if existing:
        result = dict(existing)
        result.setdefault("algorithm", "RSA-PSS-SHA256")
        result.setdefault("signed_hash", digest)
        result["existing"] = True
        return result
    sig,pub=sign_hash(signer_id,digest)
    row=db.execute(text('''INSERT INTO document_signatures(document_id,version,signer_id,algorithm,signature_b64,public_key_pem,signed_hash)
      VALUES(:d,:v,:s,:a,:sig,:pub,:h) RETURNING id,created_at'''), {'d':document_id,'v':version,'s':signer_id,'a':'RSA-PSS-SHA256','sig':sig,'pub':pub,'h':digest}).mappings().one()
    db.commit(); return {**dict(row), 'signature_b64':sig, 'public_key_pem':pub, 'signed_hash':digest, 'existing': False}


def list_signatures(db, document_id):
    return [dict(r) for r in db.execute(text('''SELECT ds.id,ds.document_id,ds.version,ds.signer_id,u.email AS signer_email,
      ds.algorithm,ds.signature_b64,ds.public_key_pem,ds.signed_hash,ds.created_at FROM document_signatures ds
      JOIN users u ON u.id=ds.signer_id WHERE ds.document_id=:d ORDER BY ds.created_at DESC'''), {'d':document_id}).mappings().all()]


def set_retention(db, document_id, until, reason, user_id):
    row=db.execute(text('''INSERT INTO retention_policies(document_id,retain_until,reason,updated_by)
      VALUES(:d,:u,:r,:by) ON CONFLICT(document_id) DO UPDATE SET retain_until=:u,reason=:r,updated_by=:by,updated_at=NOW()
      RETURNING *'''), {'d':document_id,'u':until,'r':reason,'by':user_id}).mappings().one(); db.commit(); return dict(row)


def set_hold(db, document_id, active, reason, user_id):
    if active:
        row=db.execute(text('''INSERT INTO legal_holds(document_id,active,reason,placed_by)
          VALUES(:d,TRUE,:r,:u) ON CONFLICT(document_id) DO UPDATE SET active=TRUE,reason=:r,placed_by=:u,placed_at=NOW(),released_by=NULL,released_at=NULL RETURNING *'''), {'d':document_id,'r':reason,'u':user_id}).mappings().one()
    else:
        row=db.execute(text('''UPDATE legal_holds SET active=FALSE,released_by=:u,released_at=NOW() WHERE document_id=:d RETURNING *'''), {'d':document_id,'u':user_id}).mappings().first()
    db.commit(); return dict(row) if row else None


def governance(db, document_id):
    hold=db.execute(text('SELECT * FROM legal_holds WHERE document_id=:d'), {'d':document_id}).mappings().first()
    retention=db.execute(text('SELECT * FROM retention_policies WHERE document_id=:d'), {'d':document_id}).mappings().first()
    return {'legal_hold':dict(hold) if hold else None, 'retention':dict(retention) if retention else None}
