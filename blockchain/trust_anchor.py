"""Small local trust-anchor adapter for the prototype.
It is deliberately separated so a Hyperledger Fabric provider can replace it
without changing the evidence lifecycle API.
"""
import hashlib, json, time, uuid

def anchor(evidence_no, version, sha256, event_hash):
    anchor_id='ANCHOR-'+uuid.uuid4().hex[:12].upper()
    proof=hashlib.sha256(f'{evidence_no}|{version}|{sha256}|{event_hash}|{anchor_id}'.encode()).hexdigest()
    return {'anchor_id':anchor_id,'proof':proof,'timestamp':time.time(),'provider':'local-permissioned-adapter'}
