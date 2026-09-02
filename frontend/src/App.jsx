import {useEffect,useMemo,useState} from "react";
import {
 ShieldCheck,LockKeyhole,ArrowRight,Activity,Database,FileCheck2,Fingerprint,
 Search,LogOut,Menu,X,ChevronRight,RefreshCw,CircleCheck,AlertTriangle,
 Eye,UploadCloud,History,ShieldAlert,UserRound,KeyRound,Server,Plus,
 ExternalLink,Clock3,Blocks,Link2,CheckCircle2,FileArchive
} from "lucide-react";
import {api} from "./api";

const DEMO_EMAIL="investigator@kairo.local", DEMO_PASSWORD="KairoDemo!2026";

const roleLabel=r=>(r||"").replaceAll("_"," ");
function Logo(){return <div className="brand"><span className="brand-mark">K</span><span>KAIRO</span></div>}

function Login({onLogin}){
 const [email,setEmail]=useState(DEMO_EMAIL),[password,setPassword]=useState(DEMO_PASSWORD),[busy,setBusy]=useState(false),[error,setError]=useState("");
 async function submit(e){e.preventDefault();setBusy(true);setError("");try{const r=await api.login(email,password);localStorage.setItem("kairo_token",r.access_token);onLogin()}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <main className="login-page"><div className="ambient a1"/><div className="ambient a2"/>
 <nav className="topbar"><Logo/><div className="top-status"><span className="status-dot"/>SECURE ENVIRONMENT</div></nav>
 <section className="login-grid"><div className="hero-copy"><div className="eyebrow"><ShieldCheck size={14}/> DIGITAL EVIDENCE INFRASTRUCTURE</div>
 <h1>Trust,<br/><em>engineered.</em></h1><p>KAIRO is a secure digital document management and evidence integrity platform built for legal and investigative workflows.</p>
 <div className="proof-row"><div><b>SHA-256</b><span>Content integrity</span></div><div><b>JWT</b><span>Identity control</span></div><div><b>RBAC</b><span>Least privilege</span></div></div></div>
 <form className="login-card" onSubmit={submit}><div className="card-kicker">AUTHORIZED ACCESS</div><h2>Enter KAIRO</h2><p className="muted">Authenticate to access the evidence workspace.</p>
 <label>Official email<input value={email} onChange={e=>setEmail(e.target.value)}/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
 {error&&<div className="error"><AlertTriangle size={16}/>{error}</div>}<button className="primary full" disabled={busy}>{busy?"Authenticating…":"Authenticate"}<ArrowRight size={17}/></button>
 <div className="login-foot"><LockKeyhole size={14}/> Signed session · least-privilege access</div></form></section>
 <footer><span>KAIRO</span><span>Trust, engineered.</span><span>Secure Digital Document Management System for Legal and Investigation Documents</span></footer>
 </main>
}

function Shell({user,page,setPage,onLogout,theme,onToggleTheme,children}){
 const [open,setOpen]=useState(false);
 const nav=[
  ["overview","Overview",Activity],
  ["cases","Investigations",Search],
  ["search","Search & retrieval",Search],
  ["integrity","Integrity",Fingerprint],
  ["trust","Trust ledger",Blocks],
  ["security","Security",ShieldAlert],
  ...(user.role!=="AUDITOR"?[["incidents","Incidents",AlertTriangle],["sharing","Secure sharing",ExternalLink],["signatures","Signatures",KeyRound],["forensics","Forensic export",FileArchive]]:[]),
  ["governance","Governance",LockKeyhole],
  ...(user.role==="AUDITOR"?[["audit","Audit trail",History]]:[])
 ];
 return <div className="app-shell"><aside className={open?"sidebar open":"sidebar"}><div className="side-head"><Logo/><button className="icon-btn mobile" onClick={()=>setOpen(false)}><X/></button></div>
 <div className="side-label">COMMAND CENTER · {roleLabel(user.role)}</div>{nav.map(([id,l,I])=><button key={id} className={"nav-item "+(page===id?"active":"")} onClick={()=>{setPage(id);setOpen(false)}}><I size={18}/><span>{l}</span><ChevronRight size={14}/></button>)}
 <div className="side-bottom"><div className="secure-box"><ShieldCheck size={17}/><div><b>Trust layer</b><span>Policy enforced</span></div></div><button className="nav-item logout" onClick={onLogout}><LogOut size={18}/><span>Sign out</span></button></div></aside>
 <div className="main"><header className="appbar"><button className="icon-btn mobile" onClick={()=>setOpen(true)}><Menu/></button><div className="crumb">KAIRO / <b>{page}</b></div>
 <div className="header-actions">
  <button className="theme-toggle" onClick={onToggleTheme} title={theme==="light"?"Switch to dark mode":"Switch to light mode"}>
    {theme==="light"?<span>☾</span>:<span>☀</span>} <span>{theme==="light"?"Dark":"Light"}</span>
  </button>
  <div className="identity"><div className="avatar">{user.full_name.split(" ").map(x=>x[0]).join("")}</div><div><b>{user.full_name}</b><span>{roleLabel(user.role)}</span></div></div>
</div></header><LiveTrustRail/><div className="content">{children}</div></div></div>
}
function LiveTrustRail(){
 const [tick,setTick]=useState(0);
 useEffect(()=>{const id=setInterval(()=>setTick(t=>t+1),3200);return()=>clearInterval(id)},[]);
 const signals=["Identity verified","Evidence store reachable","Integrity engine ready","Audit trail recording","Policy controls active"];
 return <aside className="live-rail" aria-label="KAIRO system status">
   <div className="live-rail-head"><span className="live-pulse"/><span>LIVE TRUST SIGNAL</span><b>#{String(tick+1).padStart(3,"0")}</b></div>
   <div className="signal-stack">{signals.map((x,i)=><div className="signal" key={x}><span className="signal-line"/><div><b>{x}</b><small>{i===0?"Authenticated session":i===1?"Protected object storage":i===2?"SHA-256 verification":i===3?"Every protected action":"RBAC + governance"}</small></div><CircleCheck2 size={14}/></div>)}</div>
   <div className="rail-foot"><span>CONTROL PLANE</span><strong>OPERATIONAL</strong></div>
 </aside>
}

function PageTitle({eyebrow,title,desc,action}){return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{desc}</p></div>{action&&<div>{action}</div>}</div>}
function PanelHead({title,action}){return <div className="panel-head"><h3>{title}</h3>{action}</div>}
function Stat({Icon,label,value,detail}){return <div className="stat"><div className="stat-icon"><Icon size={18}/></div><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></div>}
function Empty({children="No records available."}){return <div className="empty">{children}</div>}

function Overview({user,setPage}){
 const [data,setData]=useState(null),[cases,setCases]=useState([]),[err,setErr]=useState("");
 async function load(){try{setErr("");const [d,c]=await Promise.all([api.dashboard(),api.cases()]);setData(d);setCases(c)}catch(e){setErr(e.message)}}
 useEffect(()=>{load()},[]);
 return <><PageTitle eyebrow="SECURITY OPERATIONS" title="Evidence command center" desc={`Good to see you, ${user.full_name.split(" ")[0]}. KAIRO keeps identity, evidence integrity and access decisions connected.`} action={<button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button>}/>
 {err&&<div className="error banner">{err}</div>}<div className="stats">
 <Stat Icon={Database} label="Active cases" value={data?.cases??"—"} detail="investigation registry"/>
 <Stat Icon={FileCheck2} label="Protected documents" value={data?.documents??"—"} detail="object storage"/>
 <Stat Icon={Fingerprint} label="Tracked versions" value={data?.versions??"—"} detail="content lineage"/>
 <Stat Icon={Activity} label="Recorded events" value={data?.audit_events??"—"} detail="audit activity"/>
 </div>
 <div className="grid-2"><section className="panel"><PanelHead title="Active investigations" action={<button className="text-btn" onClick={()=>setPage("cases")}>View all <ArrowRight size={14}/></button>}/>
 {cases.length?cases.slice(0,4).map(c=><div className="case-row" key={c.id}><div className="case-icon"><Search size={17}/></div><div className="case-main"><b>{c.case_number}</b><span>{c.title}</span></div><span className="pill high">{c.priority}</span><ChevronRight size={16}/></div>):<Empty/>}</section>
 <section className="panel"><PanelHead title="Protection posture"/><div className="posture"><div className="posture-icon"><ShieldCheck/></div><div><b>Least privilege active</b><span>Your role is enforced by the API. Protected actions are denied server-side and can be audited.</span></div></div>
 <div className="mini-grid"><div><span>IDENTITY</span><b>JWT signed</b></div><div><span>STORAGE</span><b>MinIO</b></div><div><span>INTEGRITY</span><b>SHA-256</b></div><div><span>AUTHZ</span><b>RBAC</b></div></div></section></div>
 <div className="trust-strip"><ShieldCheck/><div><b>KAIRO treats evidence as a lifecycle.</b><span>Capture → version → fingerprint → verify → audit. The blockchain trust anchor will extend this chain without replacing the operational database or object store.</span></div></div></>
}

function SearchPage({setSelected}){
 const [q,setQ]=useState(""),[type,setType]=useState(""),[classification,setClassification]=useState(""),[caseId,setCaseId]=useState(""),[items,setItems]=useState([]),[loading,setLoading]=useState(false),[searched,setSearched]=useState(false),[error,setError]=useState(""),[cases,setCases]=useState([]),[downloading,setDownloading]=useState(null);
 useEffect(()=>{api.cases().then(setCases).catch(()=>{})},[]);
 async function run(e){e?.preventDefault();setLoading(true);setError("");try{setItems(await api.search(q,{caseId,documentType:type,classification}));setSearched(true)}catch(e){setError(e.message)}finally{setLoading(false)}}
 async function download(item){setDownloading(`${item.document_id}:${item.current_version}`);try{const r=await api.downloadVersion(item.document_id,item.current_version);const url=URL.createObjectURL(r.blob);const a=document.createElement("a");a.href=url;a.download=r.filename;a.click();URL.revokeObjectURL(url)}catch(e){setError(e.message)}finally{setDownloading(null)}}
 return <><PageTitle eyebrow="EVIDENCE RETRIEVAL" title="Search & retrieval" desc="Find protected evidence by case, document number, title, filename, type or classification without exposing document bytes in the search index." action={<button className="secondary" onClick={()=>run()}><RefreshCw size={15}/>Refresh search</button>}/>
 <form className="panel search-panel" onSubmit={run}><div className="search-input-wrap"><Search size={18}/><input autoFocus value={q} onChange={e=>setQ(e.target.value)} placeholder="Search case number, document, filename, type or station…"/></div><div className="search-filters"><select value={caseId} onChange={e=>setCaseId(e.target.value)}><option value="">All cases</option>{cases.map(c=><option key={c.id} value={c.id}>{c.case_number}</option>)}</select><select value={type} onChange={e=>setType(e.target.value)}><option value="">All document types</option><option>FIR</option><option>EVIDENCE</option><option>FORENSIC_REPORT</option><option>WITNESS_STATEMENT</option><option>CHARGE_SHEET</option></select><select value={classification} onChange={e=>setClassification(e.target.value)}><option value="">All classifications</option><option>RESTRICTED</option><option>CONFIDENTIAL</option><option>HIGHLY_RESTRICTED</option></select><button className="primary" disabled={loading}>{loading?"Searching…":"Search evidence"}<ArrowRight size={15}/></button></div></form>
 {error&&<div className="error banner">{error}</div>}
 {searched&&<div className="search-summary"><span>{items.length} result{items.length!==1?"s":""}</span><span>Metadata-only search · protected by document:read</span></div>}
 <section className="panel search-results">{!searched?<Empty>Enter a search term or choose filters to find evidence.</Empty>:loading?<Empty>Searching protected evidence index…</Empty>:items.length?items.map(item=><div className="search-result" key={item.document_id}><div className="doc-icon"><FileCheck2/></div><div className="search-result-main"><div><b>{item.document_number} · {item.title}</b><span>{item.case_number} · {item.case_title}</span></div><div className="result-meta"><span>{item.document_type}</span><span>{item.classification}</span><span>Version {item.current_version}</span><span>{item.filename||"No filename"}</span></div><code>{item.sha256||"No fingerprint"}</code></div><div className="result-actions"><button className="secondary" onClick={()=>setSelected(item.case_id)}><Eye size={15}/>Open case</button><button className="secondary" onClick={()=>download(item)} disabled={downloading===`${item.document_id}:${item.current_version}`}>{downloading===`${item.document_id}:${item.current_version}`?"Retrieving…":"Retrieve current"}<ExternalLink size={14}/></button></div></div>):<Empty>No protected evidence matched your search.</Empty>}</section>
 <div className="trust-strip"><Search/><div><b>Retrieval is still security-controlled.</b><span>Search returns metadata only. Actual evidence bytes are retrieved through an authorized endpoint, integrity-checked before release, and the retrieval is recorded as a custody/audit event.</span></div></div></>
}

function Cases({setSelected,onCreate}){
 const [items,setItems]=useState([]),[loading,setLoading]=useState(true);
 async function load(){setLoading(true);try{setItems(await api.cases())}finally{setLoading(false)}}
 useEffect(()=>{load()},[]);
 return <><PageTitle eyebrow="INVESTIGATION REGISTRY" title="Cases" desc="The operational entry point for case files and evidence collections." action={<div className="actions"><button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button><button className="primary" onClick={onCreate}><Plus size={15}/>Add evidence</button></div>}/>
 <section className="panel"><div className="table-head"><span>CASE</span><span>STATUS</span><span>PRIORITY</span><span>STATION</span><span></span></div>
 {loading?<Empty>Loading registry…</Empty>:items.map(c=><button className="table-row" key={c.id} onClick={()=>setSelected(c.id)}><div><b>{c.case_number}</b><span>{c.title}</span></div><span className="pill success">{c.status.replaceAll("_"," ")}</span><span className="pill high">{c.priority}</span><span>{c.station}</span><ChevronRight/></button>)}</section></>
}

function CaseDetail({id,onBack}){
 const [data,setData]=useState(null),[docs,setDocs]=useState([]),[selected,setSelected]=useState(null),[versions,setVersions]=useState([]),[anchors,setAnchors]=useState([]),[custody,setCustody]=useState(null),[verify,setVerify]=useState(null),[showUpload,setShowUpload]=useState(false);
 async function load(){const [c,d]=await Promise.all([api.case(id),api.documents(id)]);setData(c);setDocs(d)}
 useEffect(()=>{load()},[id]);
 async function inspect(d){setSelected(d);setVerify(null);const [v,t,c]=await Promise.all([api.versions(d.id),api.documentTrust(d.id),api.custody(d.id)]);setVersions(v);setAnchors(t.anchors||[]);setCustody(c)}
 async function verifyDoc(){setVerify({busy:true});try{setVerify(await api.verify(selected.id))}catch(e){setVerify({error:e.message})}}
 if(!data)return <div className="loading">Loading investigation…</div>;
 return <><button className="back-btn" onClick={onBack}>← Cases</button><PageTitle eyebrow={data.case_number} title={data.title} desc={data.description} action={<button className="primary" onClick={()=>setShowUpload(true)}><UploadCloud size={16}/>Add evidence</button>}/>
 <div className="case-banner"><div><span>LOCATION</span><b>{data.station}</b></div><div><span>STATUS</span><b>{data.status.replaceAll("_"," ")}</b></div><div><span>PRIORITY</span><b>{data.priority}</b></div><div><span>CASE ID</span><b>#{data.id}</b></div></div>
 <section className="panel"><PanelHead title="Evidence collection" action={<span className="panel-meta">{docs.length} document{docs.length!==1?"s":""}</span>}/>{docs.length?docs.map(d=><div className="doc-row" key={d.id}><div className="doc-icon"><FileCheck2/></div><div className="doc-main"><b>{d.document_number} · {d.title}</b><span>{d.document_type} · {d.classification} · Version {d.current_version}</span></div><button className="secondary" onClick={()=>inspect(d)}><Eye size={15}/>Inspect</button></div>):<Empty/>}</section>
 {selected&&<EvidenceInspector doc={selected} versions={versions} anchors={anchors} custody={custody} verify={verify} onVerify={verifyDoc} onClose={()=>setSelected(null)} onVersion={async file=>{await api.newVersion(selected.id,file);await inspect(selected);await load()}}/>}
 {showUpload&&<UploadModal caseId={id} onClose={()=>setShowUpload(false)} onDone={()=>{setShowUpload(false);load()}}/>}</>
}

function EvidenceInspector({doc,versions,anchors,custody,verify,onVerify,onClose,onVersion}){
 const [file,setFile]=useState(null),[busy,setBusy]=useState(false),[msg,setMsg]=useState(""),[retrieving,setRetrieving]=useState(null);
 async function retrieve(v){setRetrieving(v.version);setMsg("");try{const r=await api.downloadVersion(doc.id,v.version);const url=URL.createObjectURL(r.blob);const a=document.createElement("a");a.href=url;a.download=r.filename;a.click();URL.revokeObjectURL(url);setMsg(`Version ${v.version} retrieved after integrity verification.`)}catch(e){setMsg(e.message)}finally{setRetrieving(null)}}
 async function addVersion(){if(!file)return;setBusy(true);setMsg("");try{await onVersion(file);setFile(null);setMsg("New evidence version committed and custody recorded. Select another file for the next version.")}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 const controlled=custody?.status==="CONTROLLED";
 const incident=custody?.status==="INTEGRITY_INCIDENT";
 const actor=custody?.authorized_change?.actor;
 return <section className="panel inspect"><PanelHead title="Evidence trust record" action={<button className="icon-btn" onClick={onClose}><X size={16}/></button>}/>
 <div className="inspect-grid"><div><span>DOCUMENT</span><b>{doc.document_number}</b></div><div><span>VERSION</span><b>{doc.current_version}</b></div><div><span>CLASSIFICATION</span><b>{doc.classification}</b></div><div><span>CUSTODY</span><b>{controlled?"CONTROLLED":incident?"INCIDENT":"REVIEW"}</b></div></div>
 <div className={`custody-hero ${incident?"incident":""}`}><div className="custody-seal">{incident?<AlertTriangle/>:<ShieldCheck/>}</div><div><div className="eyebrow">CHAIN OF CUSTODY</div><h3>{incident?"Unauthorized modification detected":controlled?"Authorized evidence state":"Custody requires review"}</h3><p>{custody?.explanation||"Loading custody assessment…"}</p></div></div>
 {actor&&<div className="custody-grid"><div><span>AUTHORIZED ACTOR</span><b>{actor.full_name}</b><small>{actor.email}</small></div><div><span>ROLE</span><b>{roleLabel(actor.role)}</b><small>Authenticated account</small></div><div><span>AUTHORIZED ACTION</span><b>{custody.authorized_change.action?.replaceAll("_"," ")}</b><small>Permission: {custody.authorized_change.permission}</small></div><div><span>VERSION</span><b>Version {custody.authorized_change.version}</b><small>{new Date(custody.authorized_change.timestamp).toLocaleString()}</small></div></div>}
 <div className="custody-note"><UserRound size={15}/><span>KAIRO can prove which authenticated account and role performed an authorized action. It does not claim to identify the physical person behind a credential.</span></div>
 <div className="inspect-actions"><button className="primary" onClick={onVerify} disabled={verify?.busy}><Fingerprint size={16}/>{verify?.busy?"Verifying…":"Verify current bytes"}</button><label className="secondary upload-btn"><UploadCloud size={15}/>{file?"Change file":"Select new version"}<input type="file" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>{file&&<button className="secondary" onClick={addVersion} disabled={busy}>{busy?"Committing…":"Commit selected file"}</button>}</div>
 {msg&&<div className="notice"><CircleCheck size={16}/>{msg}</div>}
 {verify&&!verify.error&&!verify.busy&&<div className={verify.verified?"verify-good":"verify-bad"}>{verify.verified?<CircleCheck/>:<AlertTriangle/>}<div><b>{verify.result}</b><span>{verify.verified?"The current bytes match the registered version fingerprint.":"The bytes differ from the registered fingerprint. No authorized version event explains this change."}</span><code>expected {verify.expected_sha256}<br/>observed&nbsp; {verify.observed_sha256}</code></div></div>}
 {verify?.error&&<div className="error">{verify.error}</div>}
 <div className="anchor-panel"><div><span>TRUST ANCHORS</span><b>{anchors.length} ledger event{anchors.length!==1?"s":""}</b></div><div className="anchor-line">{anchors.slice(0,4).map(a=><div key={a.block_index}><span>#{a.block_index}</span><b>{a.action.replaceAll("_"," ")}</b><code>{a.event_hash.slice(0,16)}…</code></div>)}</div><div className="anchor-status"><Link2 size={14}/><span>Anchored independently outside the document bytes</span></div></div>
 <div className="versions"><div className="version-head"><b>Immutable version history</b><span>{versions.length} recorded</span></div>{versions.map(v=><div className="version-row" key={v.id}><History size={15}/><div><b>Version {v.version}</b><span>{v.original_filename} · {new Date(v.created_at).toLocaleString()}</span></div><code>{v.sha256.slice(0,16)}…</code><button className="secondary" onClick={()=>retrieve(v)} disabled={retrieving===v.version}>{retrieving===v.version?"Retrieving…":"Retrieve"}</button></div>)}</div>
 <div className="custody-events"><div className="version-head"><b>Custody events</b><span>{custody?.events?.length||0} recorded</span></div>{(custody?.events||[]).slice().reverse().map(e=><div className="custody-event" key={e.id}><div className={e.result==="SUCCESS"||e.result==="VERIFIED"?"event-dot good":"event-dot"}/><div><b>{e.action.replaceAll("_"," ")}</b><span>{e.actor?`${e.actor.full_name} · ${roleLabel(e.actor.role)}`:"SYSTEM"} · {new Date(e.timestamp).toLocaleString()}</span></div><strong>{e.result}</strong></div>)}</div>
 </section>
}

function UploadModal({caseId,onClose,onDone}){
 const [title,setTitle]=useState("Evidence document"),[type,setType]=useState("EVIDENCE"),[classification,setClassification]=useState("RESTRICTED"),[file,setFile]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 const submit=async e=>{e.preventDefault();setError("");
   if(!title.trim())return setError("Document title is required.");
   if(!file)return setError("Select an evidence file.");
   if(file.size>25*1024*1024)return setError("File exceeds the 25 MB upload limit.");
   setBusy(true);
   try{await api.upload(caseId,file,{title:title.trim(),document_type:type,classification});onDone()}
   catch(err){setError(err.message||"Evidence upload failed.")}
   finally{setBusy(false)}
 };
 return <div className="modal-backdrop"><form className="modal" onSubmit={submit}>
  <div className="modal-head"><div><div className="eyebrow">EVIDENCE INGESTION</div><h2>Secure new evidence</h2><p className="muted">Case #{caseId} · content is fingerprinted before registration.</p></div><button type="button" className="icon-btn" onClick={onClose}><X/></button></div>
  <label>Document title<input value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g. Forensic analysis report"/></label>
  <div className="form-grid">
   <label>Document type<select value={type} onChange={e=>setType(e.target.value)}><option>FIR</option><option>EVIDENCE</option><option>FORENSIC_REPORT</option><option>WITNESS_STATEMENT</option><option>CHARGE_SHEET</option></select></label>
   <label>Classification<select value={classification} onChange={e=>setClassification(e.target.value)}><option>RESTRICTED</option><option>CONFIDENTIAL</option><option>HIGHLY_RESTRICTED</option></select></label>
  </div>
  <label className="dropzone"><UploadCloud size={26}/><b>{file?file.name:"Choose evidence file"}</b><span>{file?`${(file.size/1024/1024).toFixed(2)} MB · ready to secure`:"PDF, DOCX, images or other case material · max 25 MB"}</span><input type="file" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
  {error&&<div className="error"><AlertTriangle size={15}/>{error}</div>}
  <div className="modal-actions"><button type="button" className="secondary" onClick={onClose} disabled={busy}>Cancel</button><button className="primary" disabled={busy}>{busy?"Securing evidence…":"Secure document"}<ArrowRight size={16}/></button></div>
 </form></div>
}

function Integrity(){
 const [cases,setCases]=useState([]),[docs,setDocs]=useState([]),[selected,setSelected]=useState(null),[result,setResult]=useState(null);
 useEffect(()=>{api.cases().then(async cs=>{setCases(cs);if(cs[0])setDocs(await api.documents(cs[0].id))})},[]);
 async function verify(){setResult({busy:true});try{setResult(await api.verify(selected.id))}catch(e){setResult({error:e.message})}}
 return <><PageTitle eyebrow="CRYPTOGRAPHIC ASSURANCE" title="Integrity" desc="Read the evidence bytes from object storage and independently compare them with the fingerprint recorded at ingestion."/>
 <div className="integrity-hero"><div className="shield-ring"><Fingerprint size={42}/></div><div><div className="eyebrow">VERIFICATION ENGINE</div><h2>Evidence can prove itself.</h2><p>KAIRO does not trust a filename, timestamp or UI state. It recalculates the content fingerprint.</p></div></div>
 <section className="panel"><PanelHead title="Select evidence"/>{docs.map(d=><div className="doc-row" key={d.id}><div className="doc-icon"><Fingerprint/></div><div className="doc-main"><b>{d.document_number} · {d.title}</b><span>{d.document_type} · v{d.current_version} · {d.classification}</span></div><button className="secondary" onClick={()=>{setSelected(d);setResult(null)}}>Verify <Fingerprint size={15}/></button></div>)}</section>
 {selected&&<section className="panel inspect"><PanelHead title="Verification result" action={<button className="icon-btn" onClick={()=>setSelected(null)}><X/></button>}/><div className="inspect-grid"><div><span>DOCUMENT</span><b>{selected.document_number}</b></div><div><span>VERSION</span><b>{selected.current_version}</b></div><div><span>RECORDED</span><b>SHA-256</b></div><div><span>STORAGE</span><b>MINIO</b></div></div><button className="primary" onClick={verify} disabled={result?.busy}><Fingerprint size={16}/>{result?.busy?"Reading + hashing…":"Run verification"}</button>
 {result&&!result.error&&!result.busy&&<div className={result.verified?"verify-good":"verify-bad"}>{result.verified?<CircleCheck/>:<AlertTriangle/>}<div><b>{result.result}</b><span>{result.verified?"The current object matches the recorded fingerprint.":"The object differs from the recorded fingerprint — an integrity incident is present."}</span><code>expected {result.expected_sha256}<br/>observed&nbsp; {result.observed_sha256}</code></div></div>}{result?.error&&<div className="error">{result.error}</div>}</section>}
 </>}

function TrustLedger(){
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[fabric,setFabric]=useState(null),[doc,setDoc]=useState(""),[anchor,setAnchor]=useState(null);
 async function load(){try{setError("");const [ledger,bc]=await Promise.all([api.trustLedger(80),api.blockchainStatus()]);setData(ledger);setFabric(bc)}catch(e){setError(e.message)}}
 async function verify(){setBusy(true);try{const r=await api.trustVerify();setData(d=>d?{...d,status:r}:d);await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function anchorNow(){if(!doc)return setError("Select evidence first.");setBusy(true);setError("");setAnchor(null);try{const r=await api.blockchainAnchor(Number(doc));setAnchor(r);await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
 useEffect(()=>{load()},[]);
 const status=data?.status;
 return <><PageTitle eyebrow="INDEPENDENT TRUST ANCHOR" title="Trust ledger" desc="A cryptographically chained record of KAIRO security events, with optional permissioned Hyperledger Fabric anchoring for independently verifiable evidence proof." action={<button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button>}/>
 {error&&<div className="error banner">{error}</div>}
 <div className="ledger-hero"><div className={"ledger-seal "+(status?.verified===false?"bad":"")}><Blocks size={34}/></div><div className="ledger-copy"><div className="eyebrow">KAIRO TRUST CHAIN</div><h2>{status?.verified===false?"LEDGER INTEGRITY FAILED":status?"LEDGER VERIFIED":"Loading trust state…"}</h2><p>{status?`${status.blocks} blocks linked by SHA-256 event hashes. Every block points to the previous block.`:"Building independent trust state."}</p></div><button className="primary" onClick={verify} disabled={busy||!data}>{busy?"Working…":"Verify ledger chain"}<CheckCircle2 size={16}/></button></div>
 <div className="stats ledger-stats"><Stat Icon={Blocks} label="Blocks" value={status?.blocks??"—"} detail="anchored events"/><Stat Icon={Link2} label="Latest block" value={status?.latest_block??"—"} detail="chain height"/><Stat Icon={Fingerprint} label="Hashing" value="SHA-256" detail="event fingerprints"/><Stat Icon={Server} label="Fabric" value={fabric?.reachable?"CONNECTED":"OFFLINE"} detail={fabric?.blockchain||"permissioned anchor"}/></div>
 <section className="panel"><PanelHead title="Hyperledger Fabric anchor" action={<span className="panel-meta">Evidence bytes remain off-chain</span>}/><div className="toolbar"><DocumentPicker value={doc} onChange={setDoc}/><button className="primary" disabled={busy||!doc||!fabric?.reachable} onClick={anchorNow}>{busy?"Anchoring…":"Anchor current version"}<Link2 size={15}/></button></div>{fabric&&!fabric.reachable&&<div className="notice banner">Fabric gateway is not reachable. Start the Fabric network and gateway to enable a real ledger transaction.</div>}{anchor&&<div className="notice banner">Fabric transaction confirmed: <code>{anchor.fabric?.txId||anchor.fabric?.tx_id||"transaction returned"}</code></div>}<p className="muted">The anchor contains the evidence SHA-256, custody digest, actor and action. A successful operation must return a Fabric transaction ID; otherwise KAIRO reports the anchor as unavailable.</p></section>
 <section className="panel"><PanelHead title="Immutable trust sequence" action={<span className="panel-meta">Newest first</span>}/>{data?.blocks?.length?data.blocks.map(b=><div className="ledger-row" key={b.block_index}><div className="block-number">#{b.block_index}</div><div className="ledger-main"><b>{b.action.replaceAll("_"," ")}</b><span>{b.target_type} · {b.target_id} · {b.result}</span><code>tx {b.transaction_id.slice(0,20)}…</code></div><div className="hash-pair"><span>EVENT</span><code>{b.event_hash.slice(0,18)}…</code><span>PREVIOUS</span><code>{b.previous_hash.slice(0,18)}…</code></div><CheckCircle2 size={17}/></div>):<Empty>Loading trust ledger…</Empty>}</section>
 <div className="trust-strip"><Blocks/><div><b>Two trust layers</b><span>KAIRO's local chain detects audit-history changes; Hyperledger Fabric provides an independent permissioned ledger anchor for selected evidence proofs.</span></div></div></>
}

function Incidents(){
 const [items,setItems]=useState([]),[loading,setLoading]=useState(true),[filter,setFilter]=useState("OPEN"),[busy,setBusy]=useState(null),[msg,setMsg]=useState("");
 async function load(){setLoading(true);setMsg("");try{setItems(await api.incidents(filter))}catch(e){setMsg(e.message)}finally{setLoading(false)}}
 useEffect(()=>{load()},[filter]);
 async function resolve(id){const resolution=window.prompt("Resolution / analyst action:","Evidence restored from controlled backup after incident investigation.");if(!resolution)return;setBusy(id);try{await api.resolveIncident(id,resolution);await load()}catch(e){setMsg(e.message)}finally{setBusy(null)}}
 return <><PageTitle eyebrow="INCIDENT RESPONSE" title="Security incidents" desc="KAIRO separates a legitimate authorized evidence change from a later modification that has no corresponding authorized custody event." action={<div className="actions"><select className="select" value={filter} onChange={e=>setFilter(e.target.value)}><option value="OPEN">Open incidents</option><option value="RESOLVED">Resolved incidents</option><option value="">All incidents</option></select><button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button></div>}/>
 {msg&&<div className="error banner">{msg}</div>}
 {loading?<div className="loading">Loading incident register…</div>:items.length?items.map(i=><section className="panel incident-card" key={i.id}><div className="incident-top"><div><span className="eyebrow">INCIDENT #{i.id}</span><h3>{i.incident_type.replaceAll("_"," ")}</h3></div><span className={"pill "+(i.status==="OPEN"?"danger":"success")}>{i.status}</span></div><div className="incident-grid"><div><span>DOCUMENT</span><b>KAIRO-DOC-{String(i.document_id).padStart(5,"0")}</b></div><div><span>VERSION</span><b>V{i.version}</b></div><div><span>SEVERITY</span><b>{i.severity}</b></div><div><span>DETECTED BY</span><b>Authenticated KAIRO user #{i.detected_by??"—"}</b></div></div><p className="incident-explain">{i.explanation}</p><div className="hash-pair"><div><span>REGISTERED SHA-256</span><code>{i.expected_sha256}</code></div><div><span>OBSERVED SHA-256</span><code>{i.observed_sha256}</code></div></div>{i.status==="OPEN"&&<div className="incident-actions"><span><ShieldAlert size={15}/> Do not treat the detector as proof of attacker identity.</span><button className="primary" disabled={busy===i.id} onClick={()=>resolve(i.id)}>{busy===i.id?"Resolving…":"Record resolution"}</button></div>}{i.status==="RESOLVED"&&<div className="resolved-note">Resolution: {i.resolution}</div>}</section>):<div className="empty">No incidents in this view.</div>}
 </>
}

function Security({user}){
 return <><PageTitle eyebrow="SECURITY OPERATIONS" title="Security lab" desc="See the difference between an authorized evidence change and an unauthorized modification of stored bytes."/>
 <div className="grid-2"><section className="panel security-card"><div className="security-icon"><UserRound/></div><div className="eyebrow">AUTHORIZED CHANGE</div><h2>Identity → permission → custody event.</h2><p>Your current account is <b>{roleLabel(user.role)}</b>. When you create a version through KAIRO, the API checks your role before writing the new evidence version.</p><div className="security-flow"><span>ACCOUNT</span><b>{roleLabel(user.role)}</b><ArrowRight/><span>RBAC</span><b>ALLOW</b><ArrowRight/><span>RECORD</span><b>WHO + WHAT + WHEN</b></div><div className="notice">The version is legitimate in KAIRO's workflow because an authenticated account with the required permission performed the protected action.</div></section>
 <section className="panel security-card"><div className="security-icon"><ShieldAlert/></div><div className="eyebrow">UNAUTHORIZED MODIFICATION</div><h2>Changed bytes without a new authorized version.</h2><p>If the stored object changes outside the version-creation workflow, its bytes produce a different SHA-256 while the registered version fingerprint stays unchanged.</p><div className="security-flow"><span>STORAGE</span><b>MINIO</b><ArrowRight/><span>HASH</span><b>MISMATCH</b><ArrowRight/><span>CUSTODY</span><b>INCIDENT</b></div><div className="notice">KAIRO does not magically identify the attacker. It proves that the current bytes changed and that no authorized version event explains that change.</div></section></div>
 <div className="trust-strip"><ShieldCheck/><div><b>The evidence decision rule</b><span>Authorized account + required permission + recorded version event + matching SHA-256 = controlled evidence. Hash mismatch without a corresponding authorized version event = integrity incident.</span></div></div></>
}
function Audit(){const [items,setItems]=useState([]),[error,setError]=useState("");useEffect(()=>{api.audit().then(setItems).catch(e=>setError(e.message))},[]);return <><PageTitle eyebrow="CHAIN OF CUSTODY" title="Audit trail" desc="Protected audit visibility for authorized audit personnel."/>
 {error?<div className="error banner">{error}</div>:<section className="panel"><div className="table-head"><span>EVENT</span><span>ACTOR</span><span>RESULT</span><span>TIMESTAMP</span><span></span></div>{items.map(a=><div className="table-row" key={a.id}><div><b>{a.action.replaceAll("_"," ")}</b><span>{a.target_type} · {a.target_id}</span></div><span>#{a.actor_id??"SYSTEM"}</span><span className={["SUCCESS","VERIFIED"].includes(a.result)?"result-good":"result-neutral"}>{a.result}</span><span>{new Date(a.created_at).toLocaleString()}</span><ChevronRight/></div>)}</section>}</>}

export default function App(){
 const [user,setUser]=useState(null),[page,setPage]=useState("overview"),[selected,setSelected]=useState(null),[checking,setChecking]=useState(true);
 const [theme,setTheme]=useState(()=>localStorage.getItem("kairo_theme")||"light");
 useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem("kairo_theme",theme)},[theme]);
 useEffect(()=>{
   const unauthorized=()=>{localStorage.removeItem("kairo_token");setUser(null);setSelected(null);setPage("overview")};
   window.addEventListener("kairo:unauthorized",unauthorized);
   if(localStorage.getItem("kairo_token")){
     api.me().then(setUser).catch(()=>localStorage.removeItem("kairo_token")).finally(()=>setChecking(false));
   } else setChecking(false);
   return()=>window.removeEventListener("kairo:unauthorized",unauthorized);
 },[]);
 async function completeLogin(){
   try{setUser(await api.me())}catch(e){localStorage.removeItem("kairo_token");throw e}
 }
 function logout(){
   localStorage.removeItem("kairo_token");
   setUser(null);setPage("overview");setSelected(null);
 }
 if(checking)return <div className="splash"><Logo/><span>Establishing secure session…</span></div>;
 if(!user)return <Login onLogin={completeLogin}/>;
 const content=selected?<CaseDetail id={selected} onBack={()=>setSelected(null)}/>:page==="overview"?<Overview user={user} setPage={setPage}/>:page==="cases"?<Cases setSelected={setSelected} onCreate={()=>setPage("cases")}/>:page==="search"?<SearchPage setSelected={setSelected}/>:page==="integrity"?<Integrity/>:page==="trust"?<TrustLedger/>:page==="security"?<Security user={user}/>:page==="incidents"?<Incidents/>:page==="sharing"?<Sharing/>:page==="signatures"?<Signatures/>:page==="governance"?<Governance/>:page==="forensics"?<ForensicExport/>:user.role==="AUDITOR"?<Audit/>:<Overview user={user} setPage={setPage}/>;
 return <Shell user={user} page={selected?"case":page} setPage={p=>{setSelected(null);setPage(p)}} onLogout={logout} theme={theme} onToggleTheme={()=>setTheme(t=>t==="light"?"dark":"light")}>{content}</Shell>
}

function DocumentPicker({value,onChange}){
 const [items,setItems]=useState([]); useEffect(()=>{api.search("",{limit:100}).then(setItems).catch(()=>{})},[]);
 return <select className="select" value={value||""} onChange={e=>onChange(e.target.value)}><option value="">Select evidence document…</option>{items.map(x=><option key={x.document_id} value={x.document_id}>{x.document_number} · {x.title}</option>)}</select>
}

function Sharing(){
 const [doc,setDoc]=useState(""),[collabs,setCollabs]=useState([]),[shares,setShares]=useState([]),[incoming,setIncoming]=useState([]),[permission,setPermission]=useState("VIEW"),[hours,setHours]=useState("48"),[email,setEmail]=useState(""),[msg,setMsg]=useState(""),[busy,setBusy]=useState(false);
 async function load(){try{const [c,s,i]=await Promise.all([api.collaborators(),api.outgoingShares(),api.incomingShares()]);setCollabs(c);setShares(s);setIncoming(i)}catch(e){setMsg(e.message)}}
 useEffect(()=>{load()},[]);
 async function create(){if(!doc||!email)return setMsg("Select a document and authorized collaborator.");setBusy(true);setMsg("");try{const expires=new Date(Date.now()+Number(hours)*3600000).toISOString();const r=await api.share(Number(doc),{email,permission,expires_at:expires});setMsg(`Share #${r.id} created for ${r.shared_with}. Expires ${new Date(r.expires_at).toLocaleString()}.`);setEmail("");await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 async function revoke(id){try{await api.revokeShare(id);await load()}catch(e){setMsg(e.message)}}
 return <><PageTitle eyebrow="CONTROLLED COLLABORATION" title="Secure sharing" desc="Share evidence only with an authenticated KAIRO collaborator, with a defined permission, expiry and revocation trail." action={<button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button>}/>{msg&&<div className="notice banner">{msg}</div>}
 <section className="panel"><PanelHead title="Create controlled share"/><div className="form-grid"><label>Evidence<DocumentPicker value={doc} onChange={setDoc}/></label><label>Authorized collaborator<select value={email} onChange={e=>setEmail(e.target.value)}><option value="">Select collaborator…</option>{collabs.map(c=><option key={c.id} value={c.email}>{c.full_name} · {c.role} · {c.email}</option>)}</select></label><label>Permission<select value={permission} onChange={e=>setPermission(e.target.value)}><option>VIEW</option><option>DOWNLOAD</option></select></label><label>Expiry<select value={hours} onChange={e=>setHours(e.target.value)}><option value="24">24 hours</option><option value="48">48 hours</option><option value="168">7 days</option></select></label></div><button className="primary" disabled={busy} onClick={create}>{busy?"Creating…":"Create controlled share"}<ArrowRight size={15}/></button></section>
 <section className="panel"><PanelHead title="Outgoing shares" action={<span className="panel-meta">Access is revocable</span>}/>{shares.length?shares.map(s=><div className="table-row" key={s.id}><div><b>#{s.id} · {s.shared_with_email}</b><span>Document #{s.document_id} · {s.permission}</span></div><span>{s.revoked_at?"REVOKED":new Date(s.expires_at).toLocaleString()}</span>{!s.revoked_at&&<button className="text-btn" onClick={()=>revoke(s.id)}>Revoke</button>}</div>):<Empty>No shares created yet.</Empty>}</section><section className="panel"><PanelHead title="Incoming shares" action={<span className="panel-meta">Authorized to your account</span>}/>{incoming.length?incoming.map(s=><div className="table-row" key={s.id}><div><b>#{s.id} · Document #{s.document_id}</b><span>From {s.shared_by_email} · {s.permission}</span></div><span>{s.revoked_at?"REVOKED":new Date(s.expires_at).toLocaleString()}</span>{!s.revoked_at&&<button className="text-btn" onClick={async()=>{try{const r=await api.downloadShared(s.id);const u=URL.createObjectURL(r);const a=document.createElement("a");a.href=u;a.download=`shared-document-${s.document_id}`;a.click();URL.revokeObjectURL(u)}catch(e){setMsg(e.message)}}}>Retrieve</button>}</div>):<Empty>No incoming shares.</Empty>}</section>
 <div className="trust-strip"><LockKeyhole/><div><b>No public links</b><span>KAIRO binds the share to an existing account. Expiry, revocation and every share operation are recorded in the security trail.</span></div></div></>
}

function Signatures(){
 const [doc,setDoc]=useState(""),[items,setItems]=useState([]),[msg,setMsg]=useState(""),[busy,setBusy]=useState(false),[verify,setVerify]=useState({});
 async function load(){if(!doc)return setItems([]);try{setItems(await api.signatures(Number(doc)));setMsg("")}catch(e){setMsg(`Unable to load signatures: ${e.message}`)}} useEffect(()=>{load()},[doc]);
 async function sign(){if(!doc)return setMsg("Select evidence first.");setBusy(true);setMsg("");try{const before=items.length;const r=await api.sign(Number(doc));setMsg(r.existing?`This version is already signed by ${r.signer_email}. No duplicate signature was created.`:`Version ${r.version} signed by ${r.signer_email} using ${r.algorithm}.`);await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 async function verifyOne(id){try{const r=await api.verifySignature(Number(doc),id);setVerify(v=>({...v,[id]:r}));}catch(e){setMsg(`Verification failed: ${e.message}`)}}
 return <><PageTitle eyebrow="DIGITAL SIGNATURES" title="Evidence signing" desc="Bind an authorized KAIRO identity to the exact SHA-256 fingerprint of an evidence version. The prototype uses RSA-PSS; the document bytes remain off-chain."/><section className="panel"><div className="toolbar"><DocumentPicker value={doc} onChange={setDoc}/><button className="primary" disabled={busy||!doc} onClick={sign}>{busy?"Signing…":"Sign current version"}<KeyRound size={15}/></button></div>{msg&&<div className="notice banner">{msg}</div>}</section><section className="panel"><PanelHead title="Signature records"/>{items.length?items.map(s=><div className="signature-row" key={s.id}><div><b>Signature #{s.id}</b><span>Version {s.version} · {s.signer_email} · {s.algorithm}</span><code>{s.signed_hash}</code></div><button className="secondary" onClick={()=>verifyOne(s.id)}>Verify signature</button>{verify[s.id]&&<span className={verify[s.id].verified?"result-good":"result-bad"}>{verify[s.id].verified?"✓ VERIFIED":"✕ FAILED"}</span>}</div>):<Empty>{doc?"No signatures for this document yet.":"Select a document to inspect signatures."}</Empty>}</section><div className="trust-strip"><KeyRound/><div><b>Hash vs signature</b><span>SHA-256 proves whether bytes match. The signature adds an authenticated signing identity over that exact fingerprint. This prototype is a cryptographic signature control, not a claim of a legally qualified e-signature service.</span></div></div></>
}

function ForensicExport(){
 const [doc,setDoc]=useState(""),[includeBytes,setIncludeBytes]=useState(false),[busy,setBusy]=useState(false),[msg,setMsg]=useState("");
 async function exportPackage(){if(!doc)return setMsg("Select evidence first.");setBusy(true);setMsg("");try{const r=await api.forensicExport(Number(doc),includeBytes);const u=URL.createObjectURL(r.blob);const a=document.createElement("a");a.href=u;a.download=r.filename;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);setMsg(includeBytes?"Forensic package exported with verified evidence bytes.":"Forensic metadata package exported.")}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 return <><PageTitle eyebrow="FORENSIC PACKAGE" title="Forensic export" desc="Generate a portable, integrity-oriented evidence package containing case metadata, versions, custody, signatures, governance, audit history and optional verified evidence bytes."/><section className="panel"><PanelHead title="Evidence package"/><DocumentPicker value={doc} onChange={setDoc}/><div className="export-options"><label className="check-row"><input type="checkbox" checked={includeBytes} onChange={e=>setIncludeBytes(e.target.checked)}/><span><b>Include evidence bytes</b><small>Each version is SHA-256 verified before it enters the package.</small></span></label><button className="primary" disabled={busy||!doc} onClick={exportPackage}>{busy?"Building package…":"Export forensic package"}<FileArchive size={16}/></button></div>{msg&&<div className="notice banner">{msg}</div>}</section><div className="grid-2"><section className="panel security-card"><div className="eyebrow">PACKAGE CONTENT</div><h2>Proof travels with the evidence.</h2><p>Manifest, case metadata, version fingerprints, custody record, signatures, governance state and relevant audit events are bundled into one portable ZIP.</p></section><section className="panel security-card"><div className="eyebrow">SAFE EXPORT</div><h2>Integrity checked before bytes leave.</h2><p>If any requested version fails its registered SHA-256, KAIRO refuses to build the byte-inclusive package.</p></section></div></>
}

function Governance(){
 const [doc,setDoc]=useState(""),[g,setG]=useState(null),[summary,setSummary]=useState(null),[days,setDays]=useState("365"),[reason,setReason]=useState("Investigation retention requirement"),[holdReason,setHoldReason]=useState("Legal hold for active investigation"),[msg,setMsg]=useState(""),[busy,setBusy]=useState(false);
 async function load(){try{const s=await api.governanceSummary();setSummary(s);if(doc)setG(await api.governance(Number(doc)));}catch(e){setMsg(e.message)}} useEffect(()=>{load()},[doc]);
 async function retention(){setBusy(true);try{const d=new Date(Date.now()+Number(days)*86400000).toISOString();await api.retention(Number(doc),{retain_until:d,reason});setMsg(`Retention set until ${new Date(d).toLocaleDateString()}.`);await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 async function hold(active){setBusy(true);try{await api.legalHold(Number(doc),{active,reason:holdReason});setMsg(active?"Legal hold placed.":"Legal hold released.");await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 return <><PageTitle eyebrow="GOVERNANCE & COMPLIANCE" title="Retention and legal hold" desc="Operational controls for keeping evidence available for the required period and preventing release/expiry while a legal hold is active."/><div className="stats"><Stat Icon={LockKeyhole} label="Active holds" value={summary?.active_legal_holds??"—"} detail="protected documents"/><Stat Icon={Clock3} label="Retention policies" value={summary?.retention_policies??"—"} detail="configured"/><Stat Icon={KeyRound} label="Signatures" value={summary?.signatures??"—"} detail="cryptographic approvals"/><Stat Icon={ExternalLink} label="Active shares" value={summary?.active_shares??"—"} detail="time-bound access"/></div>{msg&&<div className="notice banner">{msg}</div>}<section className="panel"><PanelHead title="Document governance"/><DocumentPicker value={doc} onChange={setDoc}/>{doc&&<div className="governance-grid"><div className="governance-card"><div className="eyebrow">RETENTION</div><h3>{g?.retention?`Retain until ${new Date(g.retention.retain_until).toLocaleDateString()}`:"No retention policy"}</h3><p>{g?.retention?.reason||"Set a retention period for this evidence."}</p><div className="inline-form"><select value={days} onChange={e=>setDays(e.target.value)}><option value="90">90 days</option><option value="365">1 year</option><option value="1095">3 years</option><option value="2555">7 years</option></select><button className="primary" disabled={busy} onClick={retention}>Set retention</button></div></div><div className="governance-card"><div className="eyebrow">LEGAL HOLD</div><h3>{g?.legal_hold?.active?"ACTIVE — protected":"Not active"}</h3><p>{g?.legal_hold?.reason||"A legal hold prevents the evidence from being treated as eligible for normal disposal."}</p><input value={holdReason} onChange={e=>setHoldReason(e.target.value)} placeholder="Hold reason"/><div className="actions"><button className="primary" disabled={busy} onClick={()=>hold(true)}>Place hold</button>{g?.legal_hold?.active&&<button className="secondary" disabled={busy} onClick={()=>hold(false)}>Release hold</button>}</div></div></div>}</section><div className="trust-strip"><ShieldCheck/><div><b>Governance is enforced as state, not a label</b><span>Retention and legal-hold actions are stored as auditable records and can be connected to later deletion/export controls.</span></div></div></>
}
