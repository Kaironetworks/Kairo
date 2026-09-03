const API_BASE = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

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
  login: (email,password)=>request("/api/auth/login",{method:"POST",body:JSON.stringify({email,password}),timeout:10000}),
  me: ()=>request("/api/auth/me",{timeout:8000}),
  permissions: ()=>request("/api/auth/permissions"),
  dashboard: ()=>request("/api/dashboard",{timeout:10000}),
  cases: ()=>request("/api/cases",{timeout:10000}),
  createCase: body=>request("/api/cases",{method:"POST",body:JSON.stringify(body)}),
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
  download: async docId=>(await blobRequest(`/api/documents/${docId}/download`)).blob,
  downloadVersion: async (docId,version)=>{
    const {res,blob}=await blobRequest(`/api/documents/${docId}/versions/${version}/download`);
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
  incomingShares: ()=>request("/api/shares/incoming"), downloadShared: async id=>(await blobRequest(`/api/shares/${id}/download`)).blob, outgoingShares: ()=>request("/api/shares/outgoing"),
  revokeShare: id=>request(`/api/shares/${id}/revoke`,{method:"POST"}),
  sign: docId=>request(`/api/documents/${docId}/sign`,{method:"POST"}),
  signatures: docId=>request(`/api/documents/${docId}/signatures`),
  verifySignature: (docId,sigId)=>request(`/api/documents/${docId}/signatures/${sigId}/verify`,{method:"POST"}),
  governance: docId=>request(`/api/documents/${docId}/governance`), governanceSummary: ()=>request("/api/governance/summary"),
  retention: (docId,body)=>request(`/api/documents/${docId}/retention`,{method:"POST",body:JSON.stringify(body)}),
  legalHold: (docId,body)=>request(`/api/documents/${docId}/legal-hold`,{method:"POST",body:JSON.stringify(body)}),
  forensicExport: async (docId,includeBytes=false)=>{const {blob}=await blobRequest(`/api/documents/${docId}/forensic-export?include_bytes=${includeBytes}`);return {blob,filename:`KAIRO-DOC-${String(docId).padStart(5,"0")}-forensic-package.zip`};},
  securityPosture: ()=>request("/api/security/posture"),
};
