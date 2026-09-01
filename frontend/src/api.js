const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("kairo_token");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) headers.set("Content-Type", "application/json");
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : detail?.message || `Request failed (${res.status})`;
    const error = new Error(message);
    error.status = res.status; error.code = detail?.code; error.detail = detail;
    throw error;
  }
  return data;
}

export const api = {
  login: (email,password)=>request("/api/auth/login",{method:"POST",body:JSON.stringify({email,password})}),
  me: ()=>request("/api/auth/me"),
  permissions: ()=>request("/api/auth/permissions"),
  dashboard: ()=>request("/api/dashboard"),
  cases: ()=>request("/api/cases"),
  case: id=>request(`/api/cases/${id}`),
  documents: caseId=>request(`/api/cases/${caseId}/documents`),
  search: (q="",filters={})=>{const p=new URLSearchParams();if(q.trim())p.set("q",q.trim());if(filters.caseId)p.set("case_id",filters.caseId);if(filters.documentType)p.set("document_type",filters.documentType);if(filters.classification)p.set("classification",filters.classification);p.set("limit",filters.limit||50);return request(`/api/search?${p.toString()}`);},
  versions: docId=>request(`/api/documents/${docId}/versions`),
  upload: (caseId, file, meta)=>{
    const f=new FormData(); f.append("file",file); f.append("title",meta.title);
    f.append("document_type",meta.document_type); f.append("classification",meta.classification);
    return request(`/api/cases/${caseId}/documents`,{method:"POST",body:f});
  },
  newVersion: (docId,file)=>{
    const f=new FormData(); f.append("file",file);
    return request(`/api/documents/${docId}/versions`,{method:"POST",body:f});
  },
  verify: docId=>request(`/api/documents/${docId}/verify`,{method:"POST"}),
  download: docId=>request(`/api/documents/${docId}/download`),
  downloadVersion: async (docId,version)=>{
    const token=localStorage.getItem("kairo_token");
    const res=await fetch(`${API_BASE}/api/documents/${docId}/versions/${version}/download`,{headers:{Authorization:`Bearer ${token}`}});
    if(!res.ok){let d=null;try{d=await res.json()}catch{};throw new Error(typeof d?.detail==="string"?d.detail:d?.detail?.message||`Download failed (${res.status})`);}
    const blob=await res.blob();
    const cd=res.headers.get("Content-Disposition")||"";
    const match=cd.match(/filename="?([^";]+)"?/i);
    return {blob,filename:match?.[1]||`kairo-document-v${version}`};
  },
  audit: ()=>request("/api/audit"),
  trustLedger: (limit=50)=>request(`/api/trust/ledger?limit=${limit}`),
  trustVerify: ()=>request("/api/trust/verify"),
  documentTrust: docId=>request(`/api/documents/${docId}/trust`),
  custody: docId=>request(`/api/documents/${docId}/custody`),
  blockchainStatus: ()=>request("/api/blockchain/status"),
  blockchainAnchor: docId=>request(`/api/documents/${docId}/blockchain-anchor`,{method:"POST"}),
  blockchainAnchorRead: docId=>request(`/api/documents/${docId}/blockchain-anchor`),
  incidents: (status="")=>request(`/api/incidents${status?`?status=${encodeURIComponent(status)}`:""}`),
  resolveIncident: (id,resolution)=>request(`/api/incidents/${id}/resolve`,{method:"POST",body:JSON.stringify({resolution})}),
  collaborators: ()=>request("/api/users/collaborators"),
  share: (docId,body)=>request(`/api/documents/${docId}/shares`,{method:"POST",body:JSON.stringify(body)}),
  incomingShares: ()=>request("/api/shares/incoming"), downloadShared: id=>request(`/api/shares/${id}/download`), outgoingShares: ()=>request("/api/shares/outgoing"),
  revokeShare: id=>request(`/api/shares/${id}/revoke`,{method:"POST"}),
  sign: docId=>request(`/api/documents/${docId}/sign`,{method:"POST"}),
  signatures: docId=>request(`/api/documents/${docId}/signatures`),
  verifySignature: (docId,sigId)=>request(`/api/documents/${docId}/signatures/${sigId}/verify`,{method:"POST"}),
  governance: docId=>request(`/api/documents/${docId}/governance`), governanceSummary: ()=>request("/api/governance/summary"),
  retention: (docId,body)=>request(`/api/documents/${docId}/retention`,{method:"POST",body:JSON.stringify(body)}),
  legalHold: (docId,body)=>request(`/api/documents/${docId}/legal-hold`,{method:"POST",body:JSON.stringify(body)}),
  forensicExport: async (docId,includeBytes=false)=>{const token=localStorage.getItem("kairo_token");const res=await fetch(`${API_BASE}/api/documents/${docId}/forensic-export?include_bytes=${includeBytes}`,{headers:{Authorization:`Bearer ${token}`}});if(!res.ok){let d=null;try{d=await res.json()}catch{};throw new Error(typeof d?.detail==="string"?d.detail:d?.detail?.message||`Export failed (${res.status})`)}const blob=await res.blob();return {blob,filename:`KAIRO-DOC-${String(docId).padStart(5,"0")}-forensic-package.zip`}},
  securityPosture: ()=>request("/api/security/posture"),
};
