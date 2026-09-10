import {useEffect,useState,Component} from "react";
import {
 ShieldCheck,LockKeyhole,ArrowRight,Activity,Database,FileCheck2,Fingerprint,
 Search,LogOut,Menu,X,ChevronRight,RefreshCw,CircleCheck,AlertTriangle,
 Eye,UploadCloud,History,ShieldAlert,UserRound,KeyRound,Server,Plus,
 ExternalLink,Clock3,Blocks,Link2,CheckCircle2,FileArchive,ScanText,BrainCircuit,FileLock2,RotateCcw,FileWarning
} from "lucide-react";
import {api} from "./api";

const roleLabel=r=>(r||"").replaceAll("_"," ");
function Logo(){return <div className="brand"><img className="brand-logo" src="/kairo-logo.png" alt="" aria-hidden="true"/><span>KAIRO</span></div>}

function Login({onLogin}){
 const [email,setEmail]=useState(""),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
 async function submit(e){e.preventDefault();setBusy(true);setError("");try{const r=await api.login(email,password);localStorage.setItem("kairo_token",r.access_token);onLogin()}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <main className="login-page">
 <nav className="topbar"><Logo/><div className="top-status"><span className="status-dot"/>SECURE ENVIRONMENT</div></nav>
 <section className="login-grid"><div className="hero-copy"><div className="eyebrow"><ShieldCheck size={14}/> DIGITAL EVIDENCE REGISTER</div>
 <h1>Trust,<br/><em>engineered.</em></h1><p>Secure digital document and evidence management for legal and investigative workflows, with controlled access, integrity verification and traceable history.</p>
 <div className="proof-row"><div><b>01 / INTEGRITY</b><span>SHA-256 evidence fingerprint</span></div><div><b>02 / IDENTITY</b><span>Authenticated session</span></div><div><b>03 / ACCESS</b><span>Role-based authorization</span></div></div></div>
 <form className="login-card" onSubmit={submit}><div className="card-kicker">AUTHORIZED ACCESS</div><h2>Enter KAIRO</h2><p className="muted">Authenticate to access the evidence workspace.</p>
 <label>User ID<input autoComplete="username" placeholder="Enter your User ID" value={email} onChange={e=>setEmail(e.target.value)} /></label><label>Password<input autoComplete="current-password" type="password" value={password} onChange={e=>setPassword(e.target.value)} /></label>
 {error&&<div className="error"><AlertTriangle size={16}/>{error}</div>}<button className="primary full" disabled={busy}>{busy?"Authenticating…":"Authenticate"}<ArrowRight size={17}/></button>
 <div className="login-foot"><LockKeyhole size={14}/> Signed session · least-privilege access</div></form></section>
 <footer><span>KAIRO</span><span>Trust, engineered.</span><span>Secure Digital Document & Evidence Management System</span></footer>
 </main>
}

function TrustContext({user,onClose,mode="trust"}){
 useEffect(()=>{const onKey=e=>{if(e.key==="Escape")onClose()};window.addEventListener("keydown",onKey);return()=>window.removeEventListener("keydown",onKey)},[onClose]);
 return <div className="context-backdrop" role="presentation" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><section className="context-modal" role="dialog" aria-modal="true" aria-labelledby="trust-title">
  <div className="context-head"><div><div className="eyebrow">{mode==="identity"?"IDENTITY CONTEXT":"SESSION SECURITY"}</div><h2 id="trust-title">{mode==="identity"?"Signed identity":"Trust context"}</h2></div><button className="icon-btn" onClick={onClose} aria-label="Close trust context"><X size={17}/></button></div>
  <div className="context-status"><span className="context-status-dot"/>{mode==="identity"?"IDENTITY VERIFIED":"AUTHENTICATED"}</div>
  <div className="context-grid"><div><span>IDENTITY</span><b>{user.full_name}</b></div><div><span>ROLE</span><b>{roleLabel(user.role)}</b></div><div><span>SESSION</span><b>Authenticated</b></div><div><span>AUTHORIZATION</span><b>Role-based policy active</b></div></div>
  <p className="context-note">{mode==="identity"?"This identity is bound to the authenticated session. Role and case access are enforced by the KAIRO API.":"Protected actions are evaluated by the KAIRO API. The interface does not define your access."}</p>
 </section></div>
}

function Shell({user,page,setPage,onLogout,children}){
 const [open,setOpen]=useState(false),[context,setContext]=useState(null);
 const has=p=>(user?.permissions||[]).includes("*")||(user?.permissions||[]).includes(p);
 const rolePages={
  POLICE:new Set(["overview","cases","search","integrity","sharing"]),
  INVESTIGATOR:new Set(["overview","cases","search","integrity","sharing","intelligence","governance"]),
  FORENSIC:new Set(["overview","cases","search","integrity","intelligence","signatures","forensics","trust","incidents","governance"]),
  LEGAL:new Set(["overview","search","integrity"]),
  AUDITOR:new Set(["overview","cases","search","audit","incidents","trust"]),
  ADMIN:new Set(["overview","admin","cases","search"])
 };
 const visible=rolePages[user.role]||rolePages.POLICE;
 const nav=[
  ["overview","Overview",Activity,true],
  ["cases","Investigations",Search,has("case.read")],
  ["search","Evidence",Search,has("evidence.read")],
  ["integrity","Verification",Fingerprint,has("evidence.verify")],
  ["sharing","Secure sharing",ExternalLink,has("evidence.share")],
  ["intelligence","Intelligence",BrainCircuit,has("evidence.read")],
  ["governance","Governance",LockKeyhole,has("evidence.create")||has("audit.read")],
  ["signatures","Signatures",KeyRound,has("forensic.write")],
  ["forensics","Forensic export",FileArchive,has("forensic.write")||has("report.create")],
  ["trust","Trust ledger",Blocks,has("trust.read")],
  ["incidents","Incidents",AlertTriangle,has("incident.read")],
  ["audit","Audit trail",History,has("audit.read")],
  ["admin","Administration",Server,has("admin.users")],
 ].filter(x=>x[3]&&visible.has(x[0]));
 return <div className="app-shell"><aside className={open?"sidebar open":"sidebar"}>
  <div className="side-head"><Logo/><button className="icon-btn mobile" onClick={()=>setOpen(false)} aria-label="Close navigation"><X/></button></div>
  <div className="side-context"><span>SECURE OPERATIONS</span><b>{roleLabel(user.role)}</b><small>Authorised workspace</small></div>
  <div className="nav-scroll">{nav.map(([id,l,I])=><button key={id} className={"nav-item "+(page===id?"active":"")} onClick={()=>{setPage(id);setOpen(false)}} aria-current={page===id?"page":undefined}><I size={18}/><span>{l}</span><ChevronRight size={14}/></button>)}</div>
  <div className="side-bottom"><button className="secure-box" onClick={()=>setContext("trust")} aria-label="Open trust context"><span className="secure-dot"/><div><b>Trust context</b><span>Authenticated · policy enforced</span></div><ChevronRight size={14}/></button><button className="nav-item logout" onClick={onLogout}><LogOut size={18}/><span>Sign out</span></button></div>
 </aside>
 <div className="main"><header className="appbar"><button className="icon-btn mobile" onClick={()=>setOpen(true)} aria-label="Open navigation"><Menu/></button><div className="crumb"><span>KAIRO</span><i>/</i><b>{page}</b></div>
  <div className="header-actions"><button className="identity identity-button" onClick={()=>setContext("identity")} aria-label="Open identity context"><div className="avatar" aria-hidden="true">{(user.full_name||"KAIRO").split(/\s+/).filter(Boolean).map(x=>x[0]).join("").slice(0,2).toUpperCase()}</div><div><b>{user.full_name}</b><span>{roleLabel(user.role)}</span></div></button></div>
 </header><div className="content">{children}</div></div>
 {context&&<TrustContext user={user} mode={context} onClose={()=>setContext(null)}/>}
 </div>
}
function PageTitle({eyebrow,title,desc,action}){return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{desc}</p></div>{action&&<div>{action}</div>}</div>}
function PanelHead({title,action}){return <div className="panel-head"><h3>{title}</h3>{action}</div>}
function Stat({Icon,label,value,detail}){return <div className="stat"><div className="stat-icon"><Icon size={18}/></div><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></div>}
function Empty({children="No records available."}){return <div className="empty">{children}</div>}

function Overview({user,setPage}){
 const [data,setData]=useState(null),[cases,setCases]=useState([]),[err,setErr]=useState("");
 async function load(){try{setErr("");const [d,c]=await Promise.all([api.dashboard(),api.cases()]);setData(d);setCases(c)}catch(e){setErr(e.message)}}
 useEffect(()=>{load()},[]);
 return <><PageTitle eyebrow="SECURITY OPERATIONS" title="Evidence command center" desc={`Authenticated workspace for controlled investigations, evidence and verification.`} action={<button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button>}/>
 {err&&<div className="error banner">{err}</div>}<div className="stats">
 <Stat Icon={Database} label="Active cases" value={data?.cases??"—"} detail="investigation registry"/>
 <Stat Icon={FileCheck2} label="Protected documents" value={data?.documents??"—"} detail="object storage"/>
 <Stat Icon={Fingerprint} label="Tracked versions" value={data?.versions??"—"} detail="content lineage"/>
 <Stat Icon={Activity} label="Recorded events" value={data?.audit_events??"—"} detail="audit activity"/>
 </div>
 <div className="grid-2"><section className="panel"><PanelHead title="Active investigations" action={<button className="text-btn" onClick={()=>setPage("cases")}>View all <ArrowRight size={14}/></button>}/>
 {cases.length?cases.slice(0,4).map(c=><div className="case-row" key={c.id}><div className="case-icon"><Search size={17}/></div><div className="case-main"><b>{c.case_number}</b><span>{c.title}</span></div><span className="pill high">{c.priority}</span><ChevronRight size={16}/></div>):<Empty/>}</section>
 <section className="panel"><PanelHead title="Protection posture"/><div className="posture"><div className="posture-icon"><ShieldCheck/></div><div><b>Least privilege active</b><span>Your role is enforced by the API. Protected actions are denied server-side and can be audited.</span></div></div>
 <div className="mini-grid"><div><span>IDENTITY</span><b>JWT signed</b></div><div><span>STORAGE</span><b>Versioned object store</b></div><div><span>INTEGRITY</span><b>SHA-256</b></div><div><span>AUTHZ</span><b>RBAC</b></div></div></section></div>
 <div className="trust-strip"><ShieldCheck/><div><b>Evidence has a record, not just a location.</b><span>Capture → version → fingerprint → verify → audit. Selected trust proofs can be anchored independently without moving sensitive document bytes onto the ledger.</span></div></div></>
}

function SearchPage({setSelected}){
 const [q,setQ]=useState(""),[type,setType]=useState(""),[classification,setClassification]=useState(""),[caseId,setCaseId]=useState(""),[items,setItems]=useState([]),[loading,setLoading]=useState(false),[searched,setSearched]=useState(false),[error,setError]=useState(""),[cases,setCases]=useState([]),[downloading,setDownloading]=useState(null);
 useEffect(()=>{api.cases().then(setCases).catch(()=>{})},[]);
 useEffect(()=>{run()},[]);
 async function run(e){e?.preventDefault();setLoading(true);setError("");try{setItems(await api.search(q,{caseId,documentType:type,classification}));setSearched(true)}catch(e){setError(e.message)}finally{setLoading(false)}}
 async function download(item){setDownloading(`${item.document_id}:${item.current_version}`);try{const r=await api.downloadVersion(item.document_id,item.current_version);const url=URL.createObjectURL(r.blob);const a=document.createElement("a");a.href=url;a.download=r.filename;a.click();URL.revokeObjectURL(url)}catch(e){setError(e.message)}finally{setDownloading(null)}}
 return <><PageTitle eyebrow="EVIDENCE RETRIEVAL" title="Search & retrieval" desc="Find protected evidence by case, document number, title, filename, type or classification without exposing document bytes in the search index." action={<button className="secondary" onClick={()=>run()}><RefreshCw size={15}/>Refresh search</button>}/>
 <form className="panel search-panel" onSubmit={run}><div className="search-input-wrap"><Search size={18}/><input autoFocus value={q} onChange={e=>setQ(e.target.value)} placeholder="Search case number, document, filename, type or station…"/></div><div className="search-filters"><select value={caseId} onChange={e=>setCaseId(e.target.value)}><option value="">All cases</option>{cases.map(c=><option key={c.id} value={c.id}>{c.case_number}</option>)}</select><select value={type} onChange={e=>setType(e.target.value)}><option value="">All document types</option><option>FIR</option><option>EVIDENCE</option><option>FORENSIC_REPORT</option><option>WITNESS_STATEMENT</option><option>CHARGE_SHEET</option></select><select value={classification} onChange={e=>setClassification(e.target.value)}><option value="">All classifications</option><option>RESTRICTED</option><option>CONFIDENTIAL</option><option>HIGHLY_RESTRICTED</option></select><button className="primary" disabled={loading}>{loading?"Searching…":"Search evidence"}<ArrowRight size={15}/></button></div></form>
 {error&&<div className="error banner">{error}</div>}
 {searched&&<div className="search-summary"><span>{items.length} result{items.length!==1?"s":""}</span><span>Metadata-only search · protected by document:read</span></div>}
 <section className="panel search-results">{!searched?<Empty>Enter a search term or choose filters to find evidence.</Empty>:loading?<Empty>Searching protected evidence index…</Empty>:items.length?items.map(item=><div className="search-result" key={item.document_id}><div className="doc-icon"><FileCheck2/></div><div className="search-result-main"><div><b>{item.document_number} · {item.title}</b><span>{item.case_number} · {item.case_title}</span></div><div className="result-meta"><span>{item.document_type}</span><span>{item.classification}</span><span>Version {item.current_version}</span><span>{item.filename||"No filename"}</span></div><code>{item.sha256||"No fingerprint"}</code></div><div className="result-actions"><button className="secondary" onClick={()=>setSelected(item.case_id)}><Eye size={15}/>Open case</button><button className="secondary" onClick={()=>download(item)} disabled={downloading===`${item.document_id}:${item.current_version}`}>{downloading===`${item.document_id}:${item.current_version}`?"Retrieving…":"Retrieve current"}<ExternalLink size={14}/></button></div></div>):<Empty>No protected evidence matched your search.</Empty>}</section>
 <div className="trust-strip"><Search/><div><b>Retrieval is still security-controlled.</b><span>Search returns metadata only. Actual evidence bytes are retrieved through an authorized endpoint, integrity-checked before release, and the retrieval is recorded as a custody/audit event.</span></div></div></>
}

function Cases({setSelected,onCreate,user}){
 const [items,setItems]=useState([]),[loading,setLoading]=useState(true);
 async function load(){setLoading(true);try{setItems(await api.cases())}finally{setLoading(false)}}
 useEffect(()=>{load()},[]);
 return <><PageTitle eyebrow="INVESTIGATION REGISTRY" title="Cases" desc="The operational entry point for case files and evidence collections." action={<div className="actions"><button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button>{user.role!=="AUDITOR"&&<button className="primary" onClick={onCreate}><Plus size={15}/>New investigation</button>}</div>}/>
 <section className="panel"><div className="table-head"><span>CASE</span><span>STATUS</span><span>PRIORITY</span><span>STATION</span><span></span></div>
 {loading?<Empty>Loading registry…</Empty>:items.map(c=><button className="table-row" key={c.id} onClick={()=>setSelected(c.id)}><div><b>{c.case_number}</b><span>{c.title}</span></div><span className="pill success">{c.status.replaceAll("_"," ")}</span><span className="pill high">{c.priority}</span><span>{c.station}</span><ChevronRight/></button>)}</section></>
}

function CaseDetail({id,onBack,user}){
 const [data,setData]=useState(null),[docs,setDocs]=useState([]),[members,setMembers]=useState([]),[selected,setSelected]=useState(null),[versions,setVersions]=useState([]),[anchors,setAnchors]=useState([]),[custody,setCustody]=useState(null),[verify,setVerify]=useState(null),[showUpload,setShowUpload]=useState(false),[memberEmail,setMemberEmail]=useState(""),[memberBusy,setMemberBusy]=useState(false),[memberMsg,setMemberMsg]=useState("");
 async function load(){const [c,d,m]=await Promise.all([api.case(id),api.documents(id),api.caseMembers(id)]);setData(c);setDocs(d);setMembers(m)}
 useEffect(()=>{load()},[id]);
 async function addMember(){if(!memberEmail.trim())return;setMemberBusy(true);setMemberMsg("");try{await api.addCaseMember(id,{email:memberEmail.trim()});setMemberEmail("");setMemberMsg("Case access granted.");setMembers(await api.caseMembers(id))}catch(e){setMemberMsg(e.message)}finally{setMemberBusy(false)}}
 async function removeMember(memberId){setMemberBusy(true);setMemberMsg("");try{await api.removeCaseMember(id,memberId);setMemberMsg("Case access removed.");setMembers(await api.caseMembers(id))}catch(e){setMemberMsg(e.message)}finally{setMemberBusy(false)}}
 async function inspect(d){setSelected(d);setVerify(null);const [v,t,c]=await Promise.all([api.versions(d.id),api.documentTrust(d.id),api.custody(d.id)]);setVersions(v);setAnchors(t.anchors||[]);setCustody(c)}
 async function verifyDoc(){setVerify({busy:true});try{setVerify(await api.verify(selected.id))}catch(e){setVerify({error:e.message})}}
 if(!data)return <div className="loading">Loading investigation…</div>;
 return <><button className="back-btn" onClick={onBack}>← Cases</button><PageTitle eyebrow={data.case_number} title={data.title} desc={data.description} action={["POLICE","INVESTIGATOR"].includes(user.role)&&<button className="primary" onClick={()=>setShowUpload(true)}><UploadCloud size={16}/>Add evidence</button>}/>
 <div className="case-banner"><div><span>LOCATION</span><b>{data.station}</b></div><div><span>STATUS</span><b>{data.status.replaceAll("_"," ")}</b></div><div><span>PRIORITY</span><b>{data.priority}</b></div><div><span>CASE ID</span><b>#{data.id}</b></div></div>
 <section className="panel case-access"><PanelHead title="Case access" action={<span className="panel-meta">Server-enforced membership</span>}/><div className="member-list">{members.map(m=><div className="member-row" key={m.id}><div><b>{m.full_name}</b><span>{m.email} · {roleLabel(m.role)} · {m.membership_role}</span></div>{m.user_id!==user?.id&&user?.role==="INVESTIGATOR"&&<button className="text-btn" onClick={()=>removeMember(m.id)} disabled={memberBusy}>Remove</button>}</div>)}</div>{user?.role==="INVESTIGATOR"&&<div className="inline-form"><input value={memberEmail} onChange={e=>setMemberEmail(e.target.value)} placeholder="Authorized user email"/><button className="primary" onClick={addMember} disabled={memberBusy}>{memberBusy?"Updating…":"Grant case access"}</button></div>}{memberMsg&&<div className="notice">{memberMsg}</div>}</section>
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
   if(file.size>25*1024*1024)return setError("File exceeds the 50 MB upload limit.");
   setBusy(true);
   try{await api.upload(caseId,file,{title:title.trim(),document_type:type,classification});onDone()}
   catch(err){setError(err.message||"Evidence upload failed.")}
   finally{setBusy(false)}
 };
 return <div className="modal-backdrop"><form className="modal-card evidence-upload" onSubmit={submit}>
  <div className="modal-head"><div><div className="eyebrow">EVIDENCE INGESTION</div><h2>Secure new evidence</h2><p className="muted">Case #{caseId} · content is fingerprinted before registration.</p></div><button type="button" className="icon-btn" onClick={onClose}><X/></button></div>
  <label>Document title<input value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g. Forensic analysis report"/></label>
  <div className="form-grid">
   <label>Document type<select value={type} onChange={e=>setType(e.target.value)}><option>FIR</option><option>EVIDENCE</option><option>FORENSIC_REPORT</option><option>WITNESS_STATEMENT</option><option>CHARGE_SHEET</option></select></label>
   <label>Classification<select value={classification} onChange={e=>setClassification(e.target.value)}><option>RESTRICTED</option><option>CONFIDENTIAL</option><option>HIGHLY_RESTRICTED</option></select></label>
  </div>
  <label className="dropzone"><UploadCloud size={26}/><b>{file?file.name:"Choose evidence file"}</b><span>{file?`${(file.size/1024/1024).toFixed(2)} MB · ready to secure`:"PDF, DOCX, images or other case material · max 50 MB"}</span><input type="file" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
  {error&&<div className="error"><AlertTriangle size={15}/>{error}</div>}
  <div className="modal-actions"><button type="button" className="secondary" onClick={onClose} disabled={busy}>Cancel</button><button className="primary" disabled={busy}>{busy?"Securing evidence…":"Secure document"}<ArrowRight size={16}/></button></div>
 </form></div>
}

function Integrity(){
 const [doc,setDoc]=useState(""),[selected,setSelected]=useState(null),[result,setResult]=useState(null);
 async function verify(){if(!selected)return;setResult({busy:true});try{setResult(await api.verify(Number(selected.document_id ?? selected.id ?? doc))) }catch(e){setResult({error:e.message})}}
 useEffect(()=>{
   if(!doc){setSelected(null);setResult(null);return}
   api.search("",{limit:100}).then(found=>{setSelected(found.find(x=>Number(x.document_id)===Number(doc))||{id:Number(doc),document_number:`KAIRO-DOC-${String(doc).padStart(5,"0")}`});setResult(null)}).catch(e=>setResult({error:e.message}));
 },[doc]);
 return <><PageTitle eyebrow="CRYPTOGRAPHIC ASSURANCE" title="Integrity" desc="Read the evidence bytes from object storage and independently compare them with the fingerprint recorded at ingestion."/>
 <div className="integrity-hero"><div className="shield-ring"><Fingerprint size={42}/></div><div><div className="eyebrow">VERIFICATION ENGINE</div><h2>Evidence can prove itself.</h2><p>KAIRO does not trust a filename, timestamp or UI state. It recalculates the content fingerprint.</p></div></div>
 <section className="panel"><PanelHead title="Select evidence"/><div className="toolbar"><DocumentPicker value={doc} onChange={v=>{setDoc(v);setSelected(null);setResult(null)}}/></div></section>
 {doc&&<section className="panel inspect"><PanelHead title="Verification result" action={<button className="icon-btn" onClick={()=>{setDoc("");setSelected(null);setResult(null)}}><X/></button>}/><div className="toolbar"><div className="selected-evidence"><Fingerprint size={15}/><span>{selected?.document_number||`Document #${doc}`}</span></div></div>
 {selected&&<div className="inspect-grid"><div><span>DOCUMENT</span><b>{selected.document_number}</b></div><div><span>VERSION</span><b>{selected.current_version??"—"}</b></div><div><span>RECORDED</span><b>SHA-256</b></div><div><span>STORAGE</span><b>MINIO</b></div></div>}
 {selected&&<button className="primary verify-button" onClick={verify} disabled={result?.busy}><Fingerprint size={16}/>{result?.busy?"Reading + hashing…":"Run verification"}</button>}
 {result&&!result.error&&!result.busy&&<div className={result.verified?"verify-good":"verify-bad"}>{result.verified?<CircleCheck/>:<AlertTriangle/>}<div><b>{result.result}</b><span>{result.verified?"The current object matches the recorded fingerprint.":"The object differs from the recorded fingerprint — an integrity incident is present."}</span><code>expected {result.expected_sha256}<br/>observed&nbsp; {result.observed_sha256}</code></div></div>}{result?.error&&<div className="error">{result.error}</div>}</section>}
 </>}

function Intelligence({user}){
 const [doc,setDoc]=useState(""),[data,setData]=useState(null),[msg,setMsg]=useState(""),[busy,setBusy]=useState(false);
 async function load(id=doc){
  if(!id){setData(null);return}
  try{setMsg("");setData(await api.intelligence(Number(id)))}catch(e){setMsg(e.message)}
 }
 useEffect(()=>{load()},[doc]);
 async function act(fn,success){
  setBusy(true);setMsg("");
  try{const r=await fn();setMsg(success(r));await load()}
  catch(e){setMsg(e.message)}
  finally{setBusy(false)}
 }
 async function detectRedactions(){
  await act(()=>api.redact(Number(doc)),r=>r.message||`Redacted ${r.count} finding(s).`)
 }
 async function runTamperDemo(){
  if(!doc)return;
  if(!window.confirm("Run the controlled storage-tamper simulation against this evidence?"))return;
  await act(()=>api.tamperDemo(Number(doc)),r=>r.message||"Controlled tamper applied. Run Verification to detect the mismatch.");
 }
 async function sealCurrent(){
  if(!window.confirm("Seal the current evidence version? Further modification will be blocked."))return;
  await act(()=>api.seal(Number(doc),data.current_version),()=>"Evidence sealed. Further modification is blocked.")
 }
 async function restoreVersion(version){
  if(!window.confirm(`Restore version ${version} as a new current version?`))return;
  await act(()=>api.restore(Number(doc),version),r=>`Version ${r.version} created from historical version ${r.restored_from}.`)
 }
 async function downloadRedacted(){
  try{
   const b=await api.redacted(Number(doc));
   const u=URL.createObjectURL(b);
   const a=document.createElement("a");
   a.href=u;
   a.download=`${data.document_number}-redacted.txt`;
   a.click();
   setTimeout(()=>URL.revokeObjectURL(u),1000)
  }catch(e){setMsg(e.message)}
 }
 return <>
  <PageTitle eyebrow="DOCUMENT INTELLIGENCE" title="Intelligence console" desc="Extract searchable text, assist document classification, detect supported PII patterns and preserve a separate redacted copy — without modifying the original evidence bytes." action={<button className="secondary" onClick={()=>load()} disabled={!doc||busy}><RefreshCw size={15}/>Refresh</button>}/>
  {msg&&<div className="notice banner">{msg}</div>}
  <section className="panel">
   <PanelHead title="Select evidence"/>
   <div className="toolbar"><DocumentPicker value={doc} onChange={v=>{setDoc(v);setData(null)}}/></div>
  </section>
  {data&&<>
   <div className="stats">
    <Stat Icon={BrainCircuit} label="Classification" value={data.ai_classification||data.document_type} detail={`${Math.round((data.ai_confidence||0)*100)}% assisted confidence`}/>
    <Stat Icon={ScanText} label="Extraction" value={data.extraction_method} detail={`${(data.extracted_text||"").length.toLocaleString()} characters`}/>
    <Stat Icon={FileWarning} label="PII findings" value={data.redaction_count} detail="latest scan count"/>
    <Stat Icon={FileLock2} label="Evidence state" value={data.sealed?"SEALED":"MUTABLE"} detail={`Merkle ${data.merkle_root?.slice(0,12)}…`}/>
   </div>
   <section className="panel">
    <PanelHead title="Intelligence result" action={<span className="panel-meta">Original evidence is immutable</span>}/>
    <div className="inspect-grid">
     <div><span>DOCUMENT</span><b>{data.document_number}</b></div>
     <div><span>TYPE</span><b>{data.document_type}</b></div>
     <div><span>CLASSIFICATION</span><b>{data.classification}</b></div>
     <div><span>VERSION</span><b>v{data.current_version}</b></div>
    </div>
    <div className="grid-2">
     <div className="governance-card"><div className="eyebrow">EXTRACTED CONTENT</div><p className="extracted-preview">{data.extracted_text_preview||"No text could be extracted. Install the optional OCR/PDF dependencies and, for image OCR, the Tesseract engine."}</p></div>
     <div className="governance-card"><div className="eyebrow">TRUST SUMMARY</div><p>Merkle root: <code>{data.merkle_root}</code></p><p>Redactions: <b>{data.redaction_count}</b> finding(s). Sealed: <b>{data.sealed?"YES":"NO"}</b>.</p></div>
    </div>
   </section>
   <section className="panel">
    <PanelHead title="Evidence controls"/>
    <div className="actions">
     {["FORENSIC","ADMIN"].includes(user.role)&&<>
      <button className="secondary" disabled={busy} onClick={detectRedactions}><ScanText size={15}/>Detect &amp; redact</button>
      {data.redaction_count>0&&<button className="secondary" disabled={busy} onClick={downloadRedacted}>Download redacted copy</button>}
      {!data.sealed&&<button className="secondary" disabled={busy} onClick={sealCurrent}><FileLock2 size={15}/>Seal current version</button>}
      {!data.sealed&&<button className="secondary" disabled={busy} onClick={runTamperDemo}><FileWarning size={15}/>Tamper demo</button>}
     </>}
    </div>
   </section>
   <section className="panel">
    <PanelHead title="Immutable versions" action={<span className="panel-meta">Restore creates a new version</span>}/>
    {data.versions.map(v=><div className="version-row" key={v.version}>
     <History size={15}/>
     <div><b>Version {v.version}</b><span>{v.filename} · {new Date(v.created_at).toLocaleString()}</span></div>
     <code>{v.sha256.slice(0,18)}…</code>
     {v.version!==data.current_version&&!data.sealed&&<button className="secondary" disabled={busy} onClick={()=>restoreVersion(v.version)}><RotateCcw size={14}/>Restore</button>}
    </div>)}
   </section>
   <div className="trust-strip"><BrainCircuit/><div><b>Assistive, not authoritative</b><span>Classification and extraction are local deterministic/optional-OCR helpers for triage and search. Security, authorization, hashes, versioning and evidence custody remain enforced by KAIRO's server.</span></div></div>
  </>}
 </>
}

function TrustLedger({onProof}){
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 async function load(){try{setError("");const ledger=await api.trustLedger(80);setData(ledger)}catch(e){setError(e.message)}}
 async function verify(){setBusy(true);try{const r=await api.trustVerify();setData(d=>d?{...d,status:r}:d);await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
 useEffect(()=>{load()},[]);
 const status=data?.status;
 return <><PageTitle eyebrow="INDEPENDENT TRUST ANCHOR" title="Trust ledger" desc="Operational trust history for evidence events. Detailed live Fabric transaction monitoring is separated into a dedicated proof console." action={<div className="actions"><button className="secondary" onClick={onProof}>Open live blockchain proof</button><button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button></div>}/>
 {error&&<div className="error banner">{error}</div>}
 <div className="ledger-hero"><div className={"ledger-seal "+(status?.verified===false?"bad":"")}><Blocks size={34}/></div><div className="ledger-copy"><div className="eyebrow">KAIRO TRUST CHAIN</div><h2>{status?.verified===false?"LEDGER INTEGRITY FAILED":status?"LEDGER VERIFIED":"Loading trust state…"}</h2><p>{status?`${status.blocks} blocks linked by SHA-256 event hashes. Every block points to the previous block.`:"Building independent trust state."}</p></div><button className="primary" onClick={verify} disabled={busy||!data}>{busy?"Working…":"Verify ledger chain"}<CheckCircle2 size={16}/></button></div>
 <div className="stats ledger-stats"><Stat Icon={Blocks} label="Blocks" value={status?.blocks??"—"} detail="recorded trust events"/><Stat Icon={Link2} label="Latest index" value={status?.latest_block??"—"} detail="latest ledger block"/><Stat Icon={Fingerprint} label="Hashing" value="SHA-256" detail="event fingerprints"/><Stat Icon={ShieldCheck} label="Integrity" value={status?.verified===false?"FAILED":"VERIFIED"} detail="local trust chain"/></div>
 <section className="panel"><PanelHead title="Immutable trust sequence" action={<span className="panel-meta">Newest first</span>}/>{data?.blocks?.length?data.blocks.map(b=><div className="ledger-row" key={b.block_index}><div className="block-number">#{b.block_index}</div><div className="ledger-main"><b>{b.action.replaceAll("_"," ")}</b><span>{b.target_type} · {b.target_id} · {b.result}</span><code>tx {b.transaction_id.slice(0,20)}…</code></div><div className="hash-pair"><span>EVENT</span><code>{b.event_hash.slice(0,18)}…</code><span>PREVIOUS</span><code>{b.previous_hash.slice(0,18)}…</code></div><CheckCircle2 size={17}/></div>):<Empty>Loading trust ledger…</Empty>}</section>
 <div className="trust-strip"><Blocks/><div><b>Two trust layers</b><span>KAIRO's local chain detects audit-history changes; Hyperledger Fabric provides an independent permissioned ledger anchor for selected evidence proofs.</span></div></div></>
}

function Incidents({user,onValidation}){
 const [items,setItems]=useState([]),[loading,setLoading]=useState(true),[filter,setFilter]=useState("OPEN"),[busy,setBusy]=useState(null),[msg,setMsg]=useState("");
 async function load(){setLoading(true);setMsg("");try{setItems(await api.incidents(filter))}catch(e){setMsg(e.message)}finally{setLoading(false)}}
 useEffect(()=>{load()},[filter]);
 async function resolve(id){const resolution=window.prompt("Resolution / analyst action:","Evidence restored from controlled backup after incident investigation.");if(!resolution)return;setBusy(id);try{await api.resolveIncident(id,resolution);await load()}catch(e){setMsg(e.message)}finally{setBusy(null)}}
 return <><PageTitle eyebrow="INCIDENT RESPONSE" title="Security incidents" desc="KAIRO separates a legitimate authorized evidence change from a later modification that has no corresponding authorized custody event." action={<div className="actions"><button className="secondary" onClick={onValidation}><ShieldAlert size={15}/>Open validation console</button><select className="select" value={filter} onChange={e=>setFilter(e.target.value)}><option value="OPEN">Open incidents</option><option value="RESOLVED">Resolved incidents</option><option value="">All incidents</option></select><button className="secondary" onClick={load}><RefreshCw size={15}/>Refresh</button></div>}/>
 {msg&&<div className="error banner">{msg}</div>}
 {loading?<div className="loading">Loading incident register…</div>:items.length?items.map(i=><section className="panel incident-card" key={i.id}><div className="incident-top"><div><span className="eyebrow">INCIDENT #{i.id}</span><h3>{i.incident_type.replaceAll("_"," ")}</h3></div><span className={"pill "+(i.status==="OPEN"?"danger":"success")}>{i.status}</span></div><div className="incident-grid"><div><span>DOCUMENT</span><b>KAIRO-DOC-{String(i.document_id).padStart(5,"0")}</b></div><div><span>VERSION</span><b>V{i.version}</b></div><div><span>SEVERITY</span><b>{i.severity}</b></div><div><span>DETECTED BY</span><b>Authenticated KAIRO user #{i.detected_by??"—"}</b></div></div><p className="incident-explain">{i.explanation}</p><div className="hash-pair"><div><span>REGISTERED SHA-256</span><code>{i.expected_sha256}</code></div><div><span>OBSERVED SHA-256</span><code>{i.observed_sha256}</code></div></div>{i.status==="OPEN"&&<div className="incident-actions"><span><ShieldAlert size={15}/> Do not treat the detector as proof of attacker identity.</span>{user?.role!=="AUDITOR"&&<button className="primary" disabled={busy===i.id} onClick={()=>resolve(i.id)}>{busy===i.id?"Resolving…":"Record resolution"}</button>}</div>}{i.status==="RESOLVED"&&<div className="resolved-note">Resolution: {i.resolution}</div>}</section>):<div className="empty">No incidents in this view.</div>}
 </>
}

function Security({user,onBack}){
 const [doc,setDoc]=useState(""),[busy,setBusy]=useState(false),[msg,setMsg]=useState("");
 async function run(){
  if(!doc)return setMsg("Select a demo evidence document first.");
  if(!window.confirm("This demonstration modifies only the selected demo evidence object. Continue?"))return;
  setBusy(true);setMsg("");
  try{const r=await api.tamperDemo(Number(doc));setMsg(r.message||"Controlled integrity-validation mutation completed. Run Verification next.")}
  catch(e){setMsg(e.message)}finally{setBusy(false)}
 }
 return <><PageTitle eyebrow="DEMONSTRATION / VALIDATION" title="Integrity validation console" desc="A controlled demonstration surface for proving how KAIRO detects an unauthorized change. This is intentionally separate from the operational evidence workspace." action={<button className="secondary" onClick={onBack}>Back to incidents</button>}/>
 {msg&&<div className="notice banner">{msg}</div>}
 <section className="panel"><PanelHead title="Select demonstration evidence"/><div className="toolbar"><DocumentPicker value={doc} onChange={setDoc}/><button className="primary" disabled={busy||!doc} onClick={run}>{busy?"Running validation…":"Run controlled integrity test"}<ShieldAlert size={16}/></button></div></section>
 <div className="grid-2"><section className="panel security-card"><div className="security-icon"><UserRound/></div><div className="eyebrow">CONTROLLED TEST</div><h2>Authorized workflow remains the product.</h2><p>Your operational workspace creates versions only after authentication, RBAC and case-scope checks. This console exists only to validate the detector against a controlled demonstration object.</p><div className="security-flow"><span>IDENTITY</span><b>{roleLabel(user.role)}</b><ArrowRight/><span>RBAC</span><b>ENFORCED</b><ArrowRight/><span>CUSTODY</span><b>RECORDED</b></div></section>
 <section className="panel security-card"><div className="security-icon"><ShieldAlert/></div><div className="eyebrow">INTEGRITY TEST</div><h2>Stored bytes → hash mismatch → incident.</h2><p>The test changes the demo object's stored bytes without creating a new authorized version. Verification should then fail and the incident register should receive a traceable event.</p><div className="security-flow"><span>OBJECT STORE</span><b>CHANGE</b><ArrowRight/><span>SHA-256</span><b>MISMATCH</b><ArrowRight/><span>RESPONSE</span><b>INCIDENT</b></div></section></div>
 <div className="trust-strip"><ShieldCheck/><div><b>Scope boundary</b><span>This page is not an operational security dashboard and is not required for day-to-day evidence handling. It is a controlled proof surface for demonstrations, QA and investigator training.</span></div></div></>
}

function BlockchainProof({onBack}){
 const [status,setStatus]=useState(null),[doc,setDoc]=useState(""),[logs,setLogs]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
 const addLog=(text,type="info")=>setLogs(l=>[{id:Date.now()+Math.random(),time:new Date().toLocaleTimeString(),text,type},...l].slice(0,40));
 async function poll(initial=false){
  try{const s=await api.blockchainStatus();setStatus(s);if(initial)addLog(s.reachable?"Fabric gateway reachable — live transaction path available":"Fabric gateway offline — no blockchain transaction will be claimed",s.reachable?"ok":"warn")}catch(e){setError(e.message);if(initial)addLog("Unable to query Fabric gateway: "+e.message,"error")}
 }
 useEffect(()=>{poll(true);const t=setInterval(()=>poll(false),2000);return()=>clearInterval(t)},[]);
 async function anchor(){
  if(!doc)return setError("Select evidence first.");
  setBusy(true);setError("");addLog(`Creating trust proof for evidence ${doc}…`);
  try{const r=await api.blockchainAnchor(Number(doc));const anchor=r.anchor_id||r.anchor?.anchor_id;if(!anchor)throw new Error("Trust provider did not return an anchor identifier.");addLog(`Trust proof created: ${anchor}`,"ok");addLog(`Evidence hash anchored; document bytes remain off-chain`,"ok");await poll(false)}catch(e){setError(e.message);addLog("Anchor failed: "+e.message,"error")}finally{setBusy(false)}
 }
 return <><PageTitle eyebrow="PROOF CONSOLE / TRUST LAYER" title="Trust proof console" desc="A dedicated demonstration surface for observing the real permissioned-ledger transaction path. The operational product remains focused on cases, evidence and governance." action={<button className="secondary" onClick={onBack}>Back to trust ledger</button>}/>
 <section className="terminal-panel"><div className="terminal-head"><div><span className="terminal-dot"/>KAIRO TRUST GATEWAY</div><span>{status?.reachable?"LIVE":"OFFLINE"}</span></div><div className="terminal-screen">
   <div className="terminal-command">$ kairo fabric status --watch</div>
   <div className="terminal-line"><span>[{new Date().toLocaleTimeString()}]</span> provider: <b>{status?.provider?"LOCAL TRUST PROVIDER":"WAITING"}</b></div>
   <div className="terminal-line"><span>mode:</span> {status?.provider||"unavailable"}</div>
   <div className="terminal-line"><span>anchor:</span> cryptographic evidence proof</div>
   <div className="terminal-line"><span>deployment:</span> Hyperledger Fabric adapter boundary</div>
   {logs.map(l=><div className={`terminal-line terminal-${l.type}`} key={l.id}><span>[{l.time}]</span> {l.text}</div>)}
  </div></section>
 <section className="panel"><PanelHead title="Anchor a real evidence proof" action={<span className="panel-meta">Only provider-confirmed trust proofs are displayed</span>}/><div className="toolbar"><DocumentPicker value={doc} onChange={setDoc}/><button className="primary" disabled={!(!status?.provider)||busy||!doc} onClick={anchor}>{busy?"Submitting transaction…":"Create trust proof"}<Link2 size={15}/></button></div>{error&&<div className="error banner">{error}</div>}<div className="proof-grid"><div><span>ON-CHAIN</span><b>Document ID + version</b></div><div><span>ON-CHAIN</span><b>SHA-256 + custody digest</b></div><div><span>OFF-CHAIN</span><b>Original evidence bytes</b></div><div><span>PROOF</span><b>Fabric transaction ID</b></div></div></section>
 <div className="trust-strip"><Blocks/><div><b>Real blockchain boundary</b><span>KAIRO stores sensitive evidence off-chain. Fabric receives only the proof metadata required to independently attest that a specific evidence fingerprint and custody event were anchored. If Fabric is unavailable, KAIRO never fabricates a successful transaction.</span></div></div></>
}

function Audit(){
 const [items,setItems]=useState([]),[error,setError]=useState(""),[loading,setLoading]=useState(true),[selected,setSelected]=useState(null);
 async function load(){setLoading(true);setError("");try{setItems(await api.audit())}catch(e){setError(e.message)}finally{setLoading(false)}}
 useEffect(()=>{load()},[]);
 const isEvidence=a=>["DOCUMENT","DOCUMENT_VERSION","INCIDENT"].includes(a?.target_type)||String(a?.action||"").startsWith("DOCUMENT")||String(a?.action||"").includes("CUSTODY")||String(a?.action||"").includes("INTEGRITY");
 return <><PageTitle eyebrow="AUDIT & CHAIN OF CUSTODY" title="Audit trail" desc="A chronological record of protected actions, evidence lifecycle events and authorization decisions." action={<button className="secondary" onClick={load} disabled={loading}><RefreshCw size={15}/>{loading?"Refreshing…":"Refresh"}</button>}/>
 {error&&<div className="error banner">{error}</div>}
 <section className="panel audit-panel">
  <div className="table-head audit-head"><span>EVENT</span><span>ACTOR</span><span>RESULT</span><span>TIMESTAMP</span><span>DETAIL</span></div>
  {loading?<Empty>Loading protected audit trail…</Empty>:items.length?items.map(a=><button className="table-row audit-row" key={a.id} onClick={()=>setSelected(a)}>
   <div><b>{a.action.replaceAll("_"," ")}</b><span>{isEvidence(a)?"Evidence / custody event":"Security / governance event"} · {a.target_type} · {a.target_id}</span></div>
   <span>{a.actor_id==null?"SYSTEM":`#${a.actor_id}`}</span>
   <span className={["SUCCESS","VERIFIED"].includes(a.result)?"result-good":a.result==="DENIED"?"result-bad":"result-neutral"}>{a.result}</span>
   <span>{new Date(a.created_at).toLocaleString()}</span>
   <span className="audit-detail-link">View details <ChevronRight size={14}/></span>
  </button>):<Empty>No audit events recorded.</Empty>}
 </section>
 <div className="trust-strip audit-explain"><History/><div><b>What this trail proves</b><span>Each row identifies what happened, who performed it (or SYSTEM), what object it affected, the result, and when it happened. Evidence-related rows are explicitly marked as evidence / custody events.</span></div></div>
 {selected&&<div className="modal-backdrop" role="presentation" onMouseDown={e=>e.target===e.currentTarget&&setSelected(null)}><section className="modal-card audit-detail-modal" role="dialog" aria-modal="true" aria-labelledby="audit-detail-title">
   <div className="modal-head"><div><div className="eyebrow">AUDIT EVENT #{selected.id}</div><h2 id="audit-detail-title">{selected.action.replaceAll("_"," ")}</h2></div><button className="icon-btn" onClick={()=>setSelected(null)} aria-label="Close event details"><X size={17}/></button></div>
   <div className="audit-event-type">{isEvidence(selected)?"EVIDENCE / CUSTODY EVENT":"SECURITY / GOVERNANCE EVENT"}</div>
   <div className="context-grid audit-detail-grid"><div><span>ACTOR</span><b>{selected.actor_id==null?"SYSTEM":`User #${selected.actor_id}`}</b></div><div><span>RESULT</span><b>{selected.result}</b></div><div><span>TARGET</span><b>{selected.target_type}</b></div><div><span>TARGET ID</span><b>{selected.target_id}</b></div><div><span>RECORDED</span><b>{new Date(selected.created_at).toLocaleString()}</b></div><div><span>EVENT ID</span><b>#{selected.id}</b></div></div>
   <div className="audit-details"><span>EVENT DETAILS</span><code>{selected.details||"No additional details recorded for this event."}</code></div>
 </section></div>}
 </>}


function Admin(){
 const [users,setUsers]=useState([]),[msg,setMsg]=useState(""),[busy,setBusy]=useState(false);
 const [form,setForm]=useState({name:"",email:"",role:"POLICE",password:""});
 async function load(){try{setUsers(await api.adminUsers())}catch(e){setMsg(e.message)}}
 useEffect(()=>{load()},[]);
 async function create(e){e.preventDefault();setBusy(true);setMsg("");try{await api.adminCreateUser(form);setForm({name:"",email:"",role:"POLICE",password:""});setMsg("User created.");await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 async function toggle(u){try{await api.adminUserStatus(u.id,!u.active);await load()}catch(e){setMsg(e.message)}}
 return <><PageTitle eyebrow="SYSTEM ADMINISTRATION" title="Identity administration" desc="Create institutional identities and assign least-privilege roles. Evidence authority remains separate from platform administration."/>
 {msg&&<div className="notice banner">{msg}</div>}
 <section className="panel"><PanelHead title="Create user"/><form className="form-grid" onSubmit={create}>
  <label>Name<input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="Officer name"/></label>
  <label>Email<input required type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} placeholder="name@agency.gov"/></label>
  <label>Department role<select value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>{Object.keys({POLICE:1,INVESTIGATOR:1,FORENSIC:1,LEGAL:1,AUDITOR:1,ADMIN:1}).map(r=><option key={r}>{r}</option>)}</select></label>
  <label>Temporary password<input required minLength="10" type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="At least 10 characters"/></label>
  <div className="modal-actions"><button className="primary" disabled={busy}>{busy?"Creating…":"Create identity"}<Plus size={15}/></button></div>
 </form></section>
 <section className="panel"><PanelHead title="Registered identities"/>{users.map(u=><div className="table-row" key={u.id}><div><b>{u.name}</b><span>{u.email} · {u.role}</span></div><span>{u.active?"ACTIVE":"DISABLED"}</span><button className="text-btn" onClick={()=>toggle(u)}>{u.active?"Disable":"Enable"}</button></div>)}{!users.length&&<Empty>No identities found.</Empty>}</section>
 <div className="trust-strip"><Server/><div><b>Separation of duties</b><span>Administration manages identity and policy. Evidence modification remains governed by case membership and role-specific permissions.</span></div></div></>
}

class AppErrorBoundary extends Component {
 constructor(props){super(props);this.state={error:null}}
 static getDerivedStateFromError(error){return {error}}
 componentDidCatch(error,info){console.error("KAIRO UI error",error,info)}
 render(){if(this.state.error)return <main className="fatal-error"><div><div className="eyebrow">APPLICATION SAFETY STOP</div><h1>KAIRO needs attention.</h1><p>The interface stopped rendering instead of showing a broken or misleading screen. Refresh the application; if the problem persists, check the API and frontend logs.</p><button className="primary" onClick={()=>window.location.reload()}>Reload KAIRO</button></div></main>;return this.props.children}
}

function App(){
 const [user,setUser]=useState(null),[page,setPage]=useState(()=>localStorage.getItem("kairo_page")||"overview"),[selected,setSelected]=useState(null),[checking,setChecking]=useState(true),[showCaseCreate,setShowCaseCreate]=useState(false);
 useEffect(()=>{document.documentElement.dataset.theme="light"},[]);
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
 async function logout(){
   try{await api.logout()}catch{}
   localStorage.removeItem("kairo_token");
   localStorage.removeItem("kairo_page");
   setUser(null);setPage("overview");setSelected(null);
 }
 useEffect(()=>{ if(user) localStorage.setItem("kairo_page", page); },[user,page]);
 if(checking)return <div className="splash"><Logo/><span>Establishing secure session…</span></div>;
 if(!user)return <Login onLogin={completeLogin}/>;
 const can=p=>(user.permissions||[]).includes("*")||(user.permissions||[]).includes(p);
 const rolePages={POLICE:new Set(["overview","cases","search","integrity","sharing"]),INVESTIGATOR:new Set(["overview","cases","search","integrity","sharing","intelligence","governance"]),FORENSIC:new Set(["overview","cases","search","integrity","intelligence","signatures","forensics","trust","incidents","governance"]),LEGAL:new Set(["overview","search","integrity"]),AUDITOR:new Set(["overview","cases","search","audit","incidents","trust"]),ADMIN:new Set(["overview","admin","cases","search"])}; const visible=rolePages[user.role]||rolePages.POLICE; const allowedPage=visible.has(page)&& (page==="overview"||page==="cases"&&can("case.read")||page==="search"&&can("evidence.read")||page==="integrity"&&can("evidence.verify")||page==="sharing"&&can("evidence.share")||page==="forensics"&&(can("forensic.write")||can("report.create"))||page==="signatures"&&can("forensic.write")||page==="intelligence"&&can("evidence.read")||page==="governance"&&(can("evidence.create")||can("audit.read"))||page==="trust"&&can("trust.read")||page==="incidents"&&can("incident.read")||page==="audit"&&can("audit.read")||page==="admin"&&can("admin.users"));
 if(!allowedPage){setPage("overview");localStorage.setItem("kairo_page","overview");}
 const safePage=allowedPage?page:"overview";
 const content=selected?<CaseDetail id={selected} user={user} onBack={()=>setSelected(null)}/>:safePage==="overview"?<Overview user={user} setPage={setPage}/>:safePage==="cases"?<Cases setSelected={setSelected} user={user} onCreate={()=>setShowCaseCreate(true)}/>:safePage==="search"?<SearchPage setSelected={setSelected}/>:safePage==="integrity"?<Integrity/>:safePage==="sharing"?<Sharing/>:safePage==="forensics"?<ForensicExport/>:safePage==="signatures"?<Signatures/>:safePage==="intelligence"?<Intelligence user={user}/>:safePage==="governance"?<Governance user={user}/>:safePage==="trust"?<TrustLedger onProof={()=>setPage("trust-proof")}/>:safePage==="trust-proof"?<BlockchainProof onBack={()=>setPage("trust")}/>:safePage==="incidents"?<Incidents user={user} onValidation={()=>setPage("incidents")}/>:safePage==="audit"?<Audit/>:safePage==="admin"?<Admin/>:<Overview user={user} setPage={setPage}/>;
 return <Shell user={user} page={selected?"case":page} setPage={p=>{setSelected(null);setPage(p);localStorage.setItem("kairo_page",p)}} onLogout={logout}>{content}{showCaseCreate&&<CaseCreateModal onClose={()=>setShowCaseCreate(false)} onCreated={id=>{setShowCaseCreate(false);setSelected(id);setPage("cases")}}/>}</Shell>
}

function CaseCreateModal({onClose,onCreated}){
 const [form,setForm]=useState({case_number:"",title:"",description:"",priority:"HIGH",station:""}),[busy,setBusy]=useState(false),[error,setError]=useState("");
 function change(k,v){setForm(f=>({...f,[k]:v}))}
 async function submit(e){e.preventDefault();setBusy(true);setError("");try{const r=await api.createCase(form);onCreated(r.id)}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><form className="modal-card case-create" onSubmit={submit}><div className="modal-head"><div><div className="eyebrow">CASE REGISTRATION</div><h2>New investigation</h2><p>Create the controlled case container before evidence enters KAIRO.</p></div><button type="button" className="icon-btn" onClick={onClose}><X/></button></div><div className="form-grid two"><label>Case number<input required value={form.case_number} onChange={e=>change("case_number",e.target.value)} placeholder="CASE-2026-002"/></label><label>Priority<select value={form.priority} onChange={e=>change("priority",e.target.value)}><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label><label>Title<input required value={form.title} onChange={e=>change("title",e.target.value)} placeholder="Investigation title"/></label><label>Station / unit<input required value={form.station} onChange={e=>change("station",e.target.value)} placeholder="Investigating unit"/></label></div><label>Description<textarea value={form.description} onChange={e=>change("description",e.target.value)} placeholder="Brief operational description" rows="4"/></label>{error&&<div className="error">{error}</div>}<div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={busy}>{busy?"Registering…":"Create investigation"}<ArrowRight size={15}/></button></div></form></div>
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
 <section className="panel"><PanelHead title="Outgoing shares" action={<span className="panel-meta">Access is revocable</span>}/>{shares.length?shares.map(s=><div className="table-row" key={s.id}><div><b>#{s.id} · {s.shared_with_email}</b><span>Document #{s.document_id} · {s.permission}</span></div><span>{s.revoked_at?"REVOKED":new Date(s.expires_at).toLocaleString()}</span>{!s.revoked_at&&<button className="text-btn" onClick={()=>revoke(s.id)}>Revoke</button>}</div>):<Empty>No shares created yet.</Empty>}</section><section className="panel"><PanelHead title="Incoming shares" action={<span className="panel-meta">Authorized to your account</span>}/>{incoming.length?incoming.map(s=><div className="table-row" key={s.id}><div><b>#{s.id} · Document #{s.document_id}</b><span>From {s.shared_by_email} · {s.permission}</span></div><span>{s.revoked_at?"REVOKED":new Date(s.expires_at).toLocaleString()}</span>{!s.revoked_at&&(s.permission==="DOWNLOAD"?<button className="text-btn" onClick={async()=>{try{const r=await api.downloadShared(s.id);const u=URL.createObjectURL(r);const a=document.createElement("a");a.href=u;a.download=`shared-document-${s.document_id}`;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}catch(e){setMsg(e.message)}}}>Retrieve</button>:<button className="text-btn" onClick={async()=>{try{const r=await api.shareRecord(s.id);setMsg(`${r.document_number} · ${r.title} · Version ${r.current_version} · record view only.`)}catch(e){setMsg(e.message)}}}>View record</button>)}</div>):<Empty>No incoming shares.</Empty>}</section>
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

function Governance({user}){
 const [doc,setDoc]=useState(""),[g,setG]=useState(null),[summary,setSummary]=useState(null),[days,setDays]=useState("365"),[reason,setReason]=useState("Investigation retention requirement"),[holdReason,setHoldReason]=useState("Legal hold for active investigation"),[msg,setMsg]=useState(""),[busy,setBusy]=useState(false);
 async function load(){try{const s=await api.governanceSummary();setSummary(s);if(doc)setG(await api.governance(Number(doc)));}catch(e){setMsg(e.message)}} useEffect(()=>{load()},[doc]);
 async function retention(){setBusy(true);try{const d=new Date(Date.now()+Number(days)*86400000).toISOString();await api.retention(Number(doc),{retain_until:d,reason});setMsg(`Retention set until ${new Date(d).toLocaleDateString()}.`);await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 async function hold(active){setBusy(true);try{await api.legalHold(Number(doc),{active,reason:holdReason});setMsg(active?"Legal hold placed.":"Legal hold released.");await load()}catch(e){setMsg(e.message)}finally{setBusy(false)}}
 return <><PageTitle eyebrow="GOVERNANCE & COMPLIANCE" title="Retention and legal hold" desc="Operational controls for keeping evidence available for the required period and preventing release/expiry while a legal hold is active."/><div className="stats"><Stat Icon={LockKeyhole} label="Active holds" value={summary?.active_legal_holds??"—"} detail="protected documents"/><Stat Icon={Clock3} label="Retention policies" value={summary?.retention_policies??"—"} detail="configured"/><Stat Icon={KeyRound} label="Signatures" value={summary?.signatures??"—"} detail="cryptographic approvals"/><Stat Icon={ExternalLink} label="Active shares" value={summary?.active_shares??"—"} detail="time-bound access"/></div>{msg&&<div className="notice banner">{msg}</div>}<section className="panel"><PanelHead title="Document governance"/><DocumentPicker value={doc} onChange={setDoc}/>{doc&&<div className="governance-grid"><div className="governance-card"><div className="eyebrow">RETENTION</div><h3>{g?.retention?`Retain until ${new Date(g.retention.retain_until).toLocaleDateString()}`:"No retention policy"}</h3><p>{g?.retention?.reason||"Set a retention period for this evidence."}</p>{["ADMIN","INVESTIGATOR","FORENSIC"].includes(user?.role)&&<div className="inline-form"><select value={days} onChange={e=>setDays(e.target.value)}><option value="90">90 days</option><option value="365">1 year</option><option value="1095">3 years</option><option value="2555">7 years</option></select><button className="primary" disabled={busy} onClick={retention}>Set retention</button></div>}</div><div className="governance-card"><div className="eyebrow">LEGAL HOLD</div><h3>{g?.legal_hold?.active?"ACTIVE — protected":"Not active"}</h3><p>{g?.legal_hold?.reason||"A legal hold prevents the evidence from being treated as eligible for normal disposal."}</p>{["ADMIN","INVESTIGATOR","FORENSIC"].includes(user?.role)&&<><input value={holdReason} onChange={e=>setHoldReason(e.target.value)} placeholder="Hold reason"/><div className="actions"><button className="primary" disabled={busy} onClick={()=>hold(true)}>Place hold</button>{g?.legal_hold?.active&&<button className="secondary" disabled={busy} onClick={()=>hold(false)}>Release hold</button>}</div></>}</div></div>}</section><div className="trust-strip"><ShieldCheck/><div><b>Governance is enforced as state, not a label</b><span>Retention and legal-hold actions are stored as auditable records and can be connected to later deletion/export controls.</span></div></div></>
}

export default function KairoApplication(){return <AppErrorBoundary><App/></AppErrorBoundary>}
