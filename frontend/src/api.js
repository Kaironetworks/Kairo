const API_BASE = import.meta.env.VITE_API_URL || window.location.origin;

async function request(path, options = {}) {
  const token = localStorage.getItem("kairo_token");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) headers.set("Content-Type", "application/json");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeout || 30000);
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal });
  } catch (err) {
    if (err?.name === "AbortError") throw new Error("KAIRO API timed out. Check that the backend is running.");
    throw new Error("KAIRO API is unreachable. Start the backend service and try again.");
  } finally {
    clearTimeout(timeout);
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    if (res.status === 401 && token) window.dispatchEvent(new Event("kairo:unauthorized"));
    const detail = data?.detail;
    const message = formatApiError(detail, res.status);
    const error = new Error(message);
    error.status = res.status; error.code = detail?.code; error.detail = detail;
    throw error;
  }
  return data;
}


function formatApiError(detail, status) {
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) {
    const fields = detail.map(x => {
      const path = Array.isArray(x?.loc) ? x.loc.filter(Boolean).join(".") : "request";
      return `${path}: ${x?.msg || "invalid value"}`;
    });
    return fields.length ? `Validation error — ${fields.join("; ")}` : `Validation error (${status})`;
  }
  return `Request failed (${status})`;
}

async function blobRequest(path, options = {}) {
  const token = localStorage.getItem("kairo_token");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeout || 30000);
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal });
    if (!res.ok) {
      let data = null;
      try { data = await res.json(); } catch {}
      if (res.status === 401 && token) window.dispatchEvent(new Event("kairo:unauthorized"));
      const detail = data?.detail;
      const message = typeof detail === "string" ? detail : detail?.message || `Request failed (${res.status})`;
      const error = new Error(message);
      error.status = res.status; error.code = detail?.code; error.detail = detail;
      throw error;
    }
    return { res, blob: await res.blob() };
  } catch (err) {
    if (err?.name === "AbortError") throw new Error("KAIRO evidence operation timed out. Check the backend and storage services.");
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  health: ()=>request("/api/health"),
  systemStatus: async ()=>{const [h,b]=await Promise.allSettled([request("/api/health",{timeout:4000}),request("/api/blockchain/status",{timeout:4000})]);return {health:h.status==="fulfilled"?h.value:null,blockchain:b.status==="fulfilled"?b.value:null};},
  login: (email,password)=>request("/api/login",{method:"POST",body:JSON.stringify({email,password}),timeout:10000}),
  me: async ()=>{const u=await request("/api/me",{timeout:8000});return {...u,full_name:u.name,role:u.role,permissions:u.permissions||[]};},
  logout: ()=>request("/api/logout",{method:"POST",timeout:5000}),
  permissions: ()=>request("/api/permissions"),
  dashboard: ()=>request("/api/dashboard",{timeout:10000}),
  cases: async ()=>{const rows=await request("/api/cases",{timeout:10000});return rows.map(x=>({...x,case_number:x.case_no,title:x.title,status:x.status,priority:x.priority,station:x.station||"—"}));},
  createCase: body=>request("/api/cases",{method:"POST",body:JSON.stringify(body)}),
  case: async id=>{const r=await request(`/api/cases/${id}`);const c=r.case||{};return {...c,case_number:c.case_no,title:c.title,status:c.status,priority:c.priority,station:c.station||"—",description:c.description||"",evidence:r.evidence||[]};},
  caseMembers: async id=>(await request(`/api/cases/${id}/members`)).map(x=>({...x,user_id:x.id,full_name:x.name,membership_role:x.role})),
  addCaseMember: (id,body)=>request(`/api/cases/${id}/members`,{method:"POST",body:JSON.stringify(body)}),
  removeCaseMember: (id,memberId)=>request(`/api/cases/${id}/members/${memberId}`,{method:"DELETE"}),
  documents: async caseId=>(await request(`/api/cases/${caseId}`)).evidence.map(x=>({...x,document_number:x.evidence_no,document_type:x.kind})),
  search: async (q="",filters={})=>{const p=new URLSearchParams();if(q.trim())p.set("q",q.trim());if(filters.caseId)p.set("case_id",filters.caseId);if(filters.documentType)p.set("document_type",filters.documentType);if(filters.classification)p.set("classification",filters.classification);p.set("limit",filters.limit||50);const rows=await request(`/api/search?${p.toString()}`);return rows.map(x=>({...x,document_id:x.id,document_number:x.evidence_no,document_type:x.kind,current_version:x.current_version,case_number:x.case_no,case_id:x.case_id,case_title:x.case_title||"",filename:x.filename||"",sha256:x.sha256||""}));},
  versions: async docId=>(await request(`/api/evidence/${docId}`)).versions.map(x=>({...x,original_filename:x.filename})),
  upload: (caseId, file, meta)=>{
    const f=new FormData(); f.append("file",file); f.append("title",meta.title);
    f.append("document_type",meta.document_type); f.append("classification",meta.classification);
    return request(`/api/cases/${caseId}/evidence`,{method:"POST",body:f});
  },
  newVersion: (docId,file)=>{
    const f=new FormData(); f.append("file",file);
    return request(`/api/evidence/${docId}/versions`,{method:"POST",body:f});
  },
  verify: docId=>request(`/api/evidence/${docId}/verify`,{method:"POST"}),
  intelligence: docId=>request(`/api/documents/${docId}/intelligence`),
  redact: docId=>request(`/api/documents/${docId}/redact`,{method:"POST"}),
  redacted: async docId=>(await blobRequest(`/api/documents/${docId}/redacted`)).blob,
  seal: (docId,version)=>request(`/api/documents/${docId}/seal`,{method:"POST",body:JSON.stringify({version})}),
  tamperDemo: docId=>request(`/api/documents/${docId}/tamper-demo`,{method:"POST"}),
  deleteDocument: docId=>request(`/api/documents/${docId}`,{method:"DELETE"}),
  restore: (docId,version)=>request(`/api/documents/${docId}/restore/${version}`,{method:"POST"}),
  download: async docId=>(await blobRequest(`/api/documents/${docId}/download`)).blob,
  downloadVersion: async (docId,version)=>{
    const {res,blob}=await blobRequest(`/api/evidence/${docId}/download?version=${version}`);
    const cd=res.headers.get("Content-Disposition")||"";
    const match=cd.match(/filename="?([^";]+)"?/i);
    return {blob,filename:match?.[1]||`kairo-document-v${version}`};
  },
  audit: ()=>request("/api/audit"),
  trustLedger: (limit=50)=>request(`/api/trust/ledger?limit=${limit}`),
  trustVerify: ()=>request("/api/trust/verify"),
  documentTrust: async docId=>{const r=await request(`/api/documents/${docId}/trust`);return {anchors:(r.anchors||[]).map((x,i)=>({...x,block_index:i+1,action:"TRUST_ANCHORED",event_hash:x.proof||x.event_hash||""}))};},
  custody: async docId=>{const events=await request(`/api/documents/${docId}/custody`);const normalized=events.map(e=>({...e,timestamp:e.created_at,actor:e.actor?{full_name:e.actor,role:e.actor_role||""}:null,details_obj:(()=>{try{return JSON.parse(e.details||"{}")}catch{return {}}})()}));const latest=[...normalized].reverse().find(e=>["EVIDENCE_REGISTERED","EVIDENCE_VERSION_CREATED","EVIDENCE_RESTORED"].includes(e.action));return {status:normalized.some(e=>e.action==="INTEGRITY_MISMATCH")?"INTEGRITY_INCIDENT":"CONTROLLED",explanation:normalized.some(e=>e.action==="INTEGRITY_MISMATCH")?"An integrity mismatch was recorded for the evidence.":"Evidence actions are recorded against authenticated KAIRO identities and chained audit events.",authorized_change:latest?{actor:latest.actor,action:latest.action,permission:"server-authorized",version:latest.details_obj?.version,timestamp:latest.timestamp}:null,events:normalized};},
  blockchainStatus: ()=>request("/api/blockchain/status"),
  blockchainAnchor: docId=>request(`/api/documents/${docId}/blockchain-anchor`,{method:"POST"}),
  blockchainAnchorRead: docId=>request(`/api/documents/${docId}/blockchain-anchor`),
  incidents: async (status="")=>{const rows=await request(`/api/incidents${status?`?status=${encodeURIComponent(status)}`:""}`);return rows.map(x=>({...x,incident_type:"INTEGRITY_MISMATCH",document_id:x.evidence_id,version:x.version||"current",severity:"HIGH",detected_by:"SYSTEM",explanation:x.details||"Stored evidence differs from its registered cryptographic identity.",expected_sha256:x.expected_hash,observed_sha256:x.observed_hash,resolution:x.details||""}));},
  resolveIncident: (id,resolution)=>request(`/api/incidents/${id}/resolve`,{method:"POST",body:JSON.stringify({resolution})}),
  collaborators: ()=>request("/api/users/collaborators"),
  share: (docId,body)=>request(`/api/documents/${docId}/shares`,{method:"POST",body:JSON.stringify(body)}),
  incomingShares: ()=>request("/api/shares/incoming"), shareRecord: id=>request(`/api/shares/${id}`), downloadShared: async id=>(await blobRequest(`/api/shares/${id}/download`)).blob, outgoingShares: ()=>request("/api/shares/outgoing"),
  revokeShare: id=>request(`/api/shares/${id}/revoke`,{method:"POST"}),
  sign: docId=>request(`/api/documents/${docId}/sign`,{method:"POST"}),
  signatures: docId=>request(`/api/documents/${docId}/signatures`),
  verifySignature: (docId,sigId)=>request(`/api/documents/${docId}/signatures/${sigId}/verify`,{method:"POST"}),
  governance: docId=>request(`/api/documents/${docId}/governance`), governanceSummary: ()=>request("/api/governance/summary"),
  retentionScan: ()=>request("/api/governance/retention/scan",{method:"POST"}), dispositions: ()=>request("/api/governance/dispositions"),
  retention: (docId,body)=>request(`/api/documents/${docId}/retention`,{method:"POST",body:JSON.stringify(body)}),
  legalHold: (docId,body)=>request(`/api/documents/${docId}/legal-hold`,{method:"POST",body:JSON.stringify(body)}),
  forensicExport: async (docId,includeBytes=false)=>{const {blob}=await blobRequest(`/api/documents/${docId}/forensic-export?include_bytes=${includeBytes}`);return {blob,filename:`KAIRO-DOC-${String(docId).padStart(5,"0")}-forensic-package.zip`};},
  securityPosture: ()=>request("/api/security/posture"),
  adminUsers: ()=>request("/api/admin/users"),
  adminCreateUser: body=>request("/api/admin/users",{method:"POST",body:JSON.stringify(body)}),
  adminUserStatus: (id,active)=>request(`/api/admin/users/${id}/status`,{method:"POST",body:JSON.stringify({active})}),
};
