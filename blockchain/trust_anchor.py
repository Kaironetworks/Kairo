"""Trust-anchor boundary.

The application stores document bytes off-chain. This provider records a
cryptographic proof that can be replaced by a Hyperledger Fabric gateway in
production without changing the evidence lifecycle API.
"""
import hashlib, uuid

def anchor(evidence_no, version, sha256, event_hash, provider="local-permissioned-trust"):
    anchor_id = "ANCHOR-" + uuid.uuid4().hex[:12].upper()
    proof = hashlib.sha256(f"{evidence_no}|{version}|{sha256}|{event_hash}|{anchor_id}".encode()).hexdigest()
    return {"anchor_id": anchor_id, "proof": proof, "provider": provider}
