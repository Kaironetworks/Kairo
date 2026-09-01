import express from 'express';
import fs from 'fs';
import crypto from 'crypto';
import { connect, signers } from '@hyperledger/fabric-gateway';
import * as grpc from '@grpc/grpc-js';

const app = express();
app.use(express.json({ limit: '256kb' }));
const PORT = Number(process.env.PORT || 8090);
const CHANNEL = process.env.FABRIC_CHANNEL || 'mychannel';
const CHAINCODE = process.env.FABRIC_CHAINCODE || 'kairo-trust';
const MSP = process.env.FABRIC_MSP_ID || 'Org1MSP';
const PEER_ENDPOINT = process.env.FABRIC_PEER_ENDPOINT || 'localhost:7051';
const CERT = process.env.FABRIC_CERT;
const KEY = process.env.FABRIC_KEY;
const TLS_CERT = process.env.FABRIC_TLS_CERT;

function sha(v){ return crypto.createHash('sha256').update(v).digest('hex'); }
function gateway(){
  if(!CERT || !KEY || !TLS_CERT) throw new Error('Fabric identity paths are not configured');
  const tls = grpc.credentials.createSsl(fs.readFileSync(TLS_CERT));
  const client = new grpc.Client(PEER_ENDPOINT, tls, { 'grpc.ssl_target_name_override': process.env.FABRIC_TLS_HOSTNAME || 'peer0.org1.example.com' });
  const identity = { mspId: MSP, credentials: fs.readFileSync(CERT) };
  const signer = signers.newPrivateKeySigner(fs.readFileSync(KEY));
  const gw = connect({ client, identity, signer });
  return { gw, client };
}

app.get('/health', (req,res)=>res.json({service:'kairo-blockchain-gateway', blockchain:'hyperledger-fabric', configured:!!(CERT&&KEY&&TLS_CERT)}));
app.post('/anchor', async (req,res)=>{
  let gw;
  try {
    const {anchorId, documentId, version, evidenceHash, custodyHash, actor, action, timestamp} = req.body || {};
    if(!anchorId || !documentId || !version || !evidenceHash) return res.status(400).json({ok:false,message:'anchorId, documentId, version and evidenceHash are required'});
    ({gw}=gateway());
    const network = gw.getNetwork(CHANNEL);
    const contract = network.getContract(CHAINCODE);
    const result = await contract.submitTransaction('Anchor', anchorId, String(documentId), String(version), evidenceHash, custodyHash||'', actor||'', action||'DOCUMENT_TRUST_ANCHOR', timestamp||new Date().toISOString());
    const record = JSON.parse(Buffer.from(result).toString());
    return res.json({ok:true,record});
  } catch(e) {
    return res.status(503).json({ok:false,message:e.message});
  } finally { if(gw) gw.close(); }
});
app.get('/anchor/:id', async (req,res)=>{
  let gw;
  try { ({gw}=gateway()); const contract=gw.getNetwork(CHANNEL).getContract(CHAINCODE); const result=await contract.evaluateTransaction('ReadAnchor', req.params.id); return res.json({ok:true,record:JSON.parse(Buffer.from(result).toString())}); }
  catch(e){ return res.status(503).json({ok:false,message:e.message}); }
  finally { if(gw) gw.close(); }
});
app.listen(PORT, ()=>console.log(`KAIRO blockchain gateway listening on ${PORT}`));
