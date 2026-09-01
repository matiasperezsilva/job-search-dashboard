"use client";

import { createClient, SupabaseClient, Session } from "@supabase/supabase-js";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api } from "../lib/api";
import type { DashboardData, Job, ProfileData, View } from "../lib/types";
import {
  HomeIcon, SearchIcon, BriefcaseIcon, CheckIcon, FileIcon, LogoutIcon,
  ExternalIcon, SparkIcon, UploadIcon, ArrowRightIcon, RefreshIcon,
} from "./icons";

const SOURCES = ["GetOnBoard", "Computrabajo", "ChileTrabajos", "Laborum", "Trabajando.com", "BNE"];

export default function AppClient({ supabaseUrl, supabaseKey }: { supabaseUrl: string; supabaseKey: string }) {
  const supabase = useMemo<SupabaseClient | null>(() => {
    if (!supabaseUrl || !supabaseKey) return null;
    return createClient(supabaseUrl, supabaseKey);
  }, [supabaseUrl, supabaseKey]);
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [view, setView] = useState<View>("dashboard");

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, [supabase]);

  if (!supabase) return <SetupError />;
  if (!ready) return <FullLoader label="Preparando tu espacio…" />;
  if (!session) return <AuthView supabase={supabase} />;

  return (
    <div className="app-shell">
      <Sidebar view={view} setView={setView} email={session.user.email || ""} onLogout={() => supabase.auth.signOut()} />
      <main className="main-area">
        <Topbar email={session.user.email || ""} />
        <div className="page-wrap">
          {view === "dashboard" && <Dashboard token={session.access_token} go={setView} />}
          {view === "search" && <SearchPage token={session.access_token} go={setView} />}
          {view === "jobs" && <JobsPage token={session.access_token} />}
          {view === "applications" && <ApplicationsPage token={session.access_token} />}
          {view === "profile" && <ProfilePage token={session.access_token} />}
        </div>
      </main>
    </div>
  );
}

function SetupError() {
  return <div className="center-screen"><div className="auth-card"><h2>Configuración incompleta</h2><p>Faltan SUPABASE_URL o SUPABASE_PUBLISHABLE_KEY en Render.</p></div></div>;
}
function FullLoader({ label }: { label: string }) {
  return <div className="center-screen"><div className="loader"/><span className="muted">{label}</span></div>;
}

function AuthView({ supabase }: { supabase: SupabaseClient }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setLoading(true); setMessage("");
    try {
      if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMessage("Cuenta creada. Revisa tu correo si Supabase solicita confirmación.");
      }
    } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudo completar la acción."); }
    finally { setLoading(false); }
  };

  return (
    <div className="auth-layout">
      <section className="auth-brand-panel">
        <div className="brand-mark large">JS</div>
        <div className="auth-brand-copy">
          <span className="eyebrow">JOB SEARCH DASHBOARD</span>
          <h1>Encuentra oportunidades que sí calzan contigo.</h1>
          <p>Tu CV se convierte en un perfil de búsqueda inteligente. Encuentra vacantes, prioriza el calce y gestiona cada postulación desde un solo lugar.</p>
        </div>
        <div className="feature-row"><span>01</span><p><b>Perfil automático</b><br/>Extraemos áreas, tecnologías y roles desde tu currículum.</p></div>
        <div className="feature-row"><span>02</span><p><b>Menos ruido</b><br/>Filtramos cargos ajenos a software, páginas SEO y resultados irrelevantes.</p></div>
        <div className="feature-row"><span>03</span><p><b>Seguimiento completo</b><br/>Vacantes, postulaciones y cartas en un mismo flujo.</p></div>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <div className="mobile-logo"><div className="brand-mark">JS</div><b>Job Search</b></div>
          <span className="eyebrow dark">BIENVENIDO</span>
          <h2>{mode === "login" ? "Inicia sesión" : "Crea tu cuenta"}</h2>
          <p className="muted">{mode === "login" ? "Continúa con tu búsqueda laboral." : "Empieza a construir tu espacio de oportunidades."}</p>
          <div className="auth-tabs">
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Iniciar sesión</button>
            <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>Crear cuenta</button>
          </div>
          <form onSubmit={submit} className="form-stack">
            <label>Correo electrónico<input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="tu@email.com" required/></label>
            <label>Contraseña<input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" minLength={6} required/></label>
            <button className="btn primary xl" disabled={loading}>{loading ? "Procesando…" : mode === "login" ? "Entrar al dashboard" : "Crear mi cuenta"}<ArrowRightIcon size={18}/></button>
          </form>
          {message && <div className="notice">{message}</div>}
          <p className="auth-foot">Tus datos se almacenan de forma privada en Supabase y están separados por usuario.</p>
        </div>
      </section>
    </div>
  );
}

function Sidebar({ view, setView, email, onLogout }: { view: View; setView: (v: View)=>void; email:string; onLogout:()=>void }) {
  const items: {id:View; label:string; icon:ReactNode; group?:string}[] = [
    {id:"dashboard",label:"Resumen",icon:<HomeIcon/>,group:"GENERAL"},
    {id:"search",label:"Buscar ofertas",icon:<SearchIcon/>,group:"DESCUBRIR"},
    {id:"jobs",label:"Oportunidades",icon:<BriefcaseIcon/>},
    {id:"applications",label:"Postulaciones",icon:<CheckIcon/>,group:"SEGUIMIENTO"},
    {id:"profile",label:"Mi currículum",icon:<FileIcon/>,group:"PERFIL"},
  ];
  return <aside className="sidebar">
    <div className="sidebar-brand"><div className="brand-mark">JS</div><div><b>Job Search</b><span>Career workspace</span></div></div>
    <nav>{items.map((item,i)=><div key={item.id}>{item.group && <div className="nav-group">{item.group}</div>}<button className={`nav-item ${view===item.id?"active":""}`} onClick={()=>setView(item.id)}>{item.icon}<span>{item.label}</span></button></div>)}</nav>
    <div className="sidebar-user"><div className="avatar">{email.slice(0,2).toUpperCase()}</div><div className="user-copy"><b>{email.split("@")[0]}</b><span>{email}</span></div><button className="icon-btn" title="Cerrar sesión" onClick={onLogout}><LogoutIcon/></button></div>
  </aside>;
}

function Topbar({ email }: { email:string }) {
  return <header className="topbar"><div><span className="topbar-title">Workspace personal</span><span className="topbar-sub">Prioriza mejor. Postula con contexto.</span></div><div className="topbar-user"><span className="status-dot"/> Sesión activa <b>{email}</b></div></header>;
}

function PageHeader({ eyebrow, title, text, action }: { eyebrow:string; title:string; text:string; action?:ReactNode }) {
  return <div className="page-header"><div><span className="eyebrow dark">{eyebrow}</span><h1>{title}</h1><p>{text}</p></div>{action}</div>;
}

function Dashboard({ token, go }: { token:string; go:(v:View)=>void }) {
  const [data,setData]=useState<DashboardData|null>(null); const [error,setError]=useState("");
  useEffect(()=>{api<DashboardData>("/dashboard",token).then(setData).catch(e=>setError(e.message));},[token]);
  if (!data && !error) return <SectionLoader/>;
  if (error) return <ErrorBox text={error}/>;
  const max = Math.max(...(data?.sources.map(s=>s.count)||[1]),1);
  return <>
    <PageHeader eyebrow="RESUMEN" title="Tu búsqueda, sin ruido." text="Visualiza el estado de tus oportunidades y enfócate en las vacantes con mejor calce." action={<button className="btn primary" onClick={()=>go("search")}><SearchIcon size={17}/>Nueva búsqueda</button>}/>
    <div className="metric-grid">
      <Metric label="Ofertas guardadas" value={data!.total} hint="Vacantes en tu base" tone="blue"/>
      <Metric label="Calce alto" value={data!.top} hint="Puntaje 70 o más" tone="violet"/>
      <Metric label="Postuladas" value={data!.postuladas} hint="Procesos iniciados" tone="cyan"/>
      <Metric label="Entrevistas" value={data!.entrevistas} hint="Procesos activos" tone="green"/>
    </div>
    <div className="dashboard-grid">
      <section className="panel"><div className="panel-head"><div><h3>Fuentes de oportunidades</h3><p>Distribución de tus vacantes guardadas.</p></div></div><div className="source-list">{data!.sources.length?data!.sources.map(s=><div className="source-row" key={s.name}><div className="source-meta"><b>{s.name}</b><span>{s.count}</span></div><div className="bar"><i style={{width:`${Math.max(8,(s.count/max)*100)}%`}}/></div></div>):<EmptyMini text="Aún no tienes ofertas guardadas."/>}</div></section>
      <section className="panel"><div className="panel-head"><div><h3>Próximos pasos</h3><p>Mantén tu búsqueda enfocada.</p></div></div><div className="quick-list"><Quick n="01" title="Mantén tu CV actualizado" text="El matching depende del perfil extraído." onClick={()=>go("profile")}/><Quick n="02" title="Busca en pocas fuentes" text="En Render Free, 1–2 portales por corrida." onClick={()=>go("search")}/><Quick n="03" title="Prioriza sobre 70" text="Revisa primero las oportunidades de mayor calce." onClick={()=>go("jobs")}/></div></section>
    </div>
    <section className="panel"><div className="panel-head"><div><h3>Oportunidades recientes</h3><p>Las mejores vacantes que tienes actualmente.</p></div><button className="btn ghost" onClick={()=>go("jobs")}>Ver todas <ArrowRightIcon size={16}/></button></div><div className="mini-jobs">{data!.recent.length?data!.recent.map(j=><MiniJob job={j} key={j.id}/>):<EmptyMini text="Ejecuta tu primera búsqueda para comenzar."/>}</div></section>
  </>;
}

function SearchPage({ token, go }: { token:string; go:(v:View)=>void }) {
  const [profile,setProfile]=useState<ProfileData|null>(null); const [sources,setSources]=useState<string[]>(["GetOnBoard"]); const [mode,setMode]=useState("rapida");
  const [terms,setTerms]=useState(""); const [loading,setLoading]=useState(false); const [result,setResult]=useState<any>(null); const [error,setError]=useState("");
  useEffect(()=>{api<ProfileData>("/profile",token).then(p=>{setProfile(p);setTerms((p.profile?.resumen?.terminos_busqueda||[]).join(", "));}).catch(e=>setError(e.message));},[token]);
  const toggle=(s:string)=>setSources(v=>v.includes(s)?v.filter(x=>x!==s):[...v,s]);
  const run=async()=>{setLoading(true);setError("");setResult(null);try{const r=await api<any>("/search",token,{method:"POST",body:JSON.stringify({sources,mode,terms:terms.split(",").map(x=>x.trim()).filter(Boolean)})});setResult(r);}catch(e){setError(e instanceof Error?e.message:"Error");}finally{setLoading(false);}};
  return <>
    <PageHeader eyebrow="DESCUBRIR" title="Encuentra oportunidades relevantes." text="Usamos roles derivados de tu CV y descartamos páginas de resultados, QA industrial y cargos fuera de contexto TI."/>
    {!profile?.active && <div className="callout warning"><FileIcon/><div><b>Primero necesitamos tu currículum.</b><p>Sube un CV para generar términos y prioridades.</p></div><button className="btn dark" onClick={()=>go("profile")}>Ir a mi currículum</button></div>}
    <div className="search-layout">
      <section className="panel search-config"><div className="section-kicker">01 · Configuración</div><h3>Define cómo buscar</h3><div className="segmented"><button className={mode==="rapida"?"active":""} onClick={()=>setMode("rapida")}>Rápida <span>Recomendada</span></button><button className={mode==="exhaustiva"?"active":""} onClick={()=>setMode("exhaustiva")}>Exhaustiva <span>Más lenta</span></button></div><label className="field-label">Términos prioritarios<textarea value={terms} onChange={e=>setTerms(e.target.value)} rows={5}/><small>Usa cargos, no tecnologías aisladas. Ej: “qa software”, “cloud support”.</small></label></section>
      <section className="panel"><div className="section-kicker">02 · Fuentes</div><h3>Selecciona portales</h3><div className="source-grid">{SOURCES.map(s=><button key={s} className={`source-toggle ${sources.includes(s)?"selected":""}`} onClick={()=>toggle(s)}><span className="check-dot">{sources.includes(s)?"✓":""}</span><div><b>{s}</b><small>{s==="GetOnBoard"?"Recomendado · especializado TI":s==="Computrabajo"?"Generalista · filtro estricto":"Fuente secundaria"}</small></div></button>)}</div></section>
    </div>
    <div className="search-actions"><button className="btn primary xl" disabled={!profile?.active||loading||sources.length===0} onClick={run}>{loading?<><span className="spinner"/>Buscando oportunidades…</>:<><SearchIcon/>Buscar oportunidades</>}</button><span className="muted">Las fuentes se consultan secuencialmente para cuidar los recursos de Render Free.</span></div>
    {error&&<ErrorBox text={error}/>} {result&&<SearchResult result={result} onView={()=>go("jobs")}/>} 
  </>;
}

function SearchResult({result,onView}:{result:any;onView:()=>void}){
  return <section className="panel result-panel"><div className="result-top"><div><span className="success-icon">✓</span><div><h3>Búsqueda finalizada</h3><p>{result.found} vacantes relevantes · {result.new} nuevas guardadas</p></div></div><button className="btn dark" onClick={onView}>Ver oportunidades <ArrowRightIcon size={16}/></button></div><div className="stats-strip">{(result.stats||[]).map((s:any)=><div key={s.fuente}><b>{s.fuente}</b><span>{s.cantidad} resultados · {s.segundos}s</span></div>)}</div>{(result.errors||[]).length>0&&<div className="source-errors">{result.errors.map((e:any)=><span key={e.fuente}>{e.fuente}: {e.error}</span>)}</div>}</section>
}

function JobsPage({ token }: { token:string }) {
  const [jobs,setJobs]=useState<Job[]>([]); const [min,setMin]=useState(40); const [source,setSource]=useState(""); const [q,setQ]=useState(""); const [selected,setSelected]=useState<Job|null>(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(""); const [reeval,setReeval]=useState(false);
  const load=()=>{setLoading(true);api<{items:Job[]}>(`/jobs?min_score=${min}${source?`&source=${encodeURIComponent(source)}`:""}${q?`&q=${encodeURIComponent(q)}`:""}`,token).then(r=>{setJobs(r.items);if(selected){setSelected(r.items.find(x=>x.id===selected.id)||null)}}).catch(e=>setError(e.message)).finally(()=>setLoading(false));};
  useEffect(()=>{const t=setTimeout(load,200);return()=>clearTimeout(t)},[token,min,source,q]);
  const reevaluate=async()=>{setReeval(true);setError("");try{await api("/jobs/reevaluate",token,{method:"POST"});load();}catch(e){setError(e instanceof Error?e.message:"Error");}finally{setReeval(false);}};
  return <>
    <PageHeader eyebrow="OPORTUNIDADES" title="Vacantes priorizadas para ti." text="Cada tarjeta muestra el calce con tu CV. Abre la publicación original cuando quieras postular." action={<button className="btn ghost" onClick={reevaluate} disabled={reeval}><RefreshIcon size={16}/>{reeval?"Reevaluando…":"Reevaluar base"}</button>}/>
    <div className="filters"><label>Calce mínimo<select value={min} onChange={e=>setMin(Number(e.target.value))}>{[0,30,40,50,60,70,80,90].map(v=><option key={v} value={v}>{v}+</option>)}</select></label><label>Fuente<select value={source} onChange={e=>setSource(e.target.value)}><option value="">Todas</option>{SOURCES.map(s=><option key={s}>{s}</option>)}</select></label><label className="search-field">Buscar<input value={q} onChange={e=>setQ(e.target.value)} placeholder="Cargo o empresa…"/></label></div>
    {error&&<ErrorBox text={error}/>} {loading?<SectionLoader/>:<div className="jobs-layout"><section><div className="list-head"><span>{jobs.length} oportunidades</span><small>Ordenadas por calce</small></div><div className="job-list">{jobs.map(job=><JobCard key={job.id} job={job} selected={selected?.id===job.id} onSelect={()=>setSelected(job)}/>) }{jobs.length===0&&<EmptyMini text="No hay oportunidades con estos filtros."/>}</div></section><aside className="job-detail">{selected?<JobDetail job={selected} token={token} onSaved={load}/>:<EmptyDetail/>}</aside></div>}
  </>;
}

function JobCard({job,selected,onSelect}:{job:Job;selected:boolean;onSelect:()=>void}){
  return <article className={`job-card ${selected?"selected":""}`} onClick={onSelect}><div className="job-card-main"><div className="company-avatar">{(job.empresa||"?").slice(0,1).toUpperCase()}</div><div className="job-copy"><h3>{job.titulo}</h3><p>{job.empresa||"Empresa no informada"}</p><div className="badges"><Badge text={job.area||"Sin clasificar"}/><Badge text={job.fuente||"Fuente"} tone="blue"/>{job.modalidad&&<Badge text={job.modalidad}/>}<Badge text={job.estado||"Sin gestionar"} tone="gray"/></div></div></div><div className={`score ${job.puntaje>=70?"high":job.puntaje>=50?"mid":"low"}`}><b>{job.puntaje}</b><span>calce</span></div></article>
}

function JobDetail({job,token,onSaved}:{job:Job;token:string;onSaved:()=>void}){
  const [tab,setTab]=useState<"info"|"tracking"|"letter">("info");
  return <div className="detail-card"><div className="detail-head"><span className="eyebrow dark">DETALLE</span><h2>{job.titulo}</h2><p>{job.empresa||"Empresa no informada"}</p><div className="detail-actions">{job.link?<a className="btn primary" href={job.link} target="_blank" rel="noopener noreferrer"><ExternalIcon size={17}/>Ver oferta / Postular</a>:<button className="btn disabled" disabled>Enlace no disponible</button>}</div></div><div className="tabs"><button className={tab==="info"?"active":""} onClick={()=>setTab("info")}>Resumen</button><button className={tab==="tracking"?"active":""} onClick={()=>setTab("tracking")}>Seguimiento</button><button className={tab==="letter"?"active":""} onClick={()=>setTab("letter")}>Carta</button></div>{tab==="info"&&<div className="detail-body"><div className="detail-stat-grid"><SmallStat label="Calce" value={`${job.puntaje}/100`}/><SmallStat label="Área" value={job.area||"—"}/><SmallStat label="Fuente" value={job.fuente||"—"}/></div><h4>Por qué aparece aquí</h4><p>{job.razon||"Sin detalle de evaluación."}</p><h4>Descripción</h4><p className="description-text">{job.descripcion||"La fuente no entregó descripción completa."}</p></div>}{tab==="tracking"&&<Tracking job={job} token={token} onSaved={onSaved}/>} {tab==="letter"&&<Letter job={job} token={token}/>}</div>
}

function Tracking({job,token,onSaved}:{job:Job;token:string;onSaved:()=>void}){
  const [state,setState]=useState(job.estado||"Guardada");const [notes,setNotes]=useState(job.notas||"");const [saving,setSaving]=useState(false);const [msg,setMsg]=useState("");
  const save=async()=>{setSaving(true);try{await api(`/jobs/${job.id}/application`,token,{method:"PUT",body:JSON.stringify({state,notes})});setMsg("Seguimiento actualizado.");onSaved();}catch(e){setMsg(e instanceof Error?e.message:"Error")}finally{setSaving(false)}};
  return <div className="detail-body form-stack"><label>Estado<select value={state} onChange={e=>setState(e.target.value)}>{["Guardada","Postulada","Entrevista","Rechazada","Oferta recibida"].map(s=><option key={s}>{s}</option>)}</select></label><label>Notas<textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={6} placeholder="Fecha de postulación, contacto, entrevista, observaciones…"/></label><button className="btn primary" onClick={save} disabled={saving}>{saving?"Guardando…":"Guardar seguimiento"}</button>{msg&&<small className="muted">{msg}</small>}</div>
}

function Letter({job,token}:{job:Job;token:string}){
  const [content,setContent]=useState("");const [mode,setMode]=useState("local");const [loading,setLoading]=useState(false);const [msg,setMsg]=useState("");
  useEffect(()=>{api<any>(`/jobs/${job.id}/letter`,token).then(r=>{setContent(r.contenido||"");setMode(r.modo||"local")}).catch(()=>{})},[job.id,token]);
  const generate=async()=>{setLoading(true);setMsg("");try{const r=await api<any>(`/jobs/${job.id}/letter/generate`,token,{method:"POST",body:JSON.stringify({mode})});setContent(r.content)}catch(e){setMsg(e instanceof Error?e.message:"Error")}finally{setLoading(false)}};
  const save=async()=>{await api(`/jobs/${job.id}/letter`,token,{method:"PUT",body:JSON.stringify({content,mode})});setMsg("Borrador guardado.")};
  return <div className="detail-body form-stack"><div className="segmented compact"><button className={mode==="local"?"active":""} onClick={()=>setMode("local")}>Local</button><button className={mode==="inteligente"?"active":""} onClick={()=>setMode("inteligente")}>Inteligente</button></div><button className="btn dark" onClick={generate} disabled={loading}><SparkIcon size={17}/>{loading?"Generando…":"Generar carta"}</button><label>Borrador<textarea rows={13} value={content} onChange={e=>setContent(e.target.value)} placeholder="Genera o escribe aquí tu carta…"/></label><div className="button-row"><button className="btn primary" onClick={save} disabled={!content.trim()}>Guardar borrador</button><button className="btn ghost" disabled={!content.trim()} onClick={()=>downloadText(content,`carta_${safeName(job.empresa||"empresa")}.txt`)}>Descargar</button></div>{msg&&<small className="muted">{msg}</small>}</div>
}

function ApplicationsPage({token}:{token:string}){
  const [jobs,setJobs]=useState<Job[]>([]); const [state,setState]=useState(""); const [loading,setLoading]=useState(true);
  useEffect(()=>{api<{items:Job[]}>(`/jobs?min_score=0${state?`&state=${encodeURIComponent(state)}`:""}`,token).then(r=>setJobs(r.items.filter(j=>j.estado&&j.estado!=="Sin gestionar"))).finally(()=>setLoading(false))},[token,state]);
  return <><PageHeader eyebrow="SEGUIMIENTO" title="Tus procesos, en orden." text="Conserva contexto de cada postulación y vuelve rápidamente a la publicación original."/><div className="filters one"><label>Estado<select value={state} onChange={e=>setState(e.target.value)}><option value="">Todos</option>{["Guardada","Postulada","Entrevista","Rechazada","Oferta recibida"].map(s=><option key={s}>{s}</option>)}</select></label></div>{loading?<SectionLoader/>:<div className="application-grid">{jobs.map(j=><article className="application-card" key={j.id}><div><Badge text={j.estado||""} tone="blue"/><h3>{j.titulo}</h3><p>{j.empresa||"Empresa no informada"}</p></div><p className="app-notes">{j.notas||"Sin notas todavía."}</p><div className="app-foot"><span>{j.fuente} · {j.puntaje} pts</span>{j.link&&<a href={j.link} target="_blank" rel="noopener noreferrer">Ver oferta <ExternalIcon size={14}/></a>}</div></article>)}{jobs.length===0&&<EmptyMini text="Aún no tienes procesos gestionados."/>}</div>}</>;
}

function ProfilePage({token}:{token:string}){
  const [profile,setProfile]=useState<ProfileData|null>(null);const [file,setFile]=useState<File|null>(null);const [uploading,setUploading]=useState(false);const [terms,setTerms]=useState("");const [msg,setMsg]=useState("");
  const load=()=>api<ProfileData>("/profile",token).then(p=>{setProfile(p);setTerms((p.profile?.resumen?.terminos_busqueda||[]).join(", "))});
  useEffect(()=>{load()},[token]);
  const upload=async()=>{if(!file)return;setUploading(true);setMsg("");try{const fd=new FormData();fd.append("file",file);await api("/profile/upload",token,{method:"POST",body:fd});await load();setMsg("Currículum actualizado correctamente.")}catch(e){setMsg(e instanceof Error?e.message:"Error")}finally{setUploading(false)}};
  const saveTerms=async()=>{await api("/profile/terms",token,{method:"PUT",body:JSON.stringify({terms:terms.split(",").map(x=>x.trim()).filter(Boolean)})});setMsg("Términos actualizados.");load()};
  const summary=profile?.profile?.resumen;
  return <><PageHeader eyebrow="PERFIL" title="Tu currículum define la búsqueda." text="Sube tu CV, revisa lo que detectamos y ajusta los roles que quieres priorizar."/><div className="profile-layout"><section className="panel"><div className="section-kicker">CURRÍCULUM</div><h3>{profile?.active?"Actualizar archivo":"Sube tu primer CV"}</h3><div className="upload-zone"><UploadIcon size={28}/><b>{file?file.name:"Arrastra o selecciona tu currículum"}</b><span>PDF, DOCX o TXT</span><input type="file" accept=".pdf,.docx,.txt" onChange={e=>setFile(e.target.files?.[0]||null)}/></div><button className="btn primary full" onClick={upload} disabled={!file||uploading}>{uploading?"Procesando CV…":"Analizar y activar currículum"}</button>{msg&&<div className="notice subtle">{msg}</div>}</section><section className="panel"><div className="section-kicker">PERFIL ACTIVO</div><h3>{profile?.cv_name||"Sin currículum activo"}</h3>{profile?.active?<><ProfileBlock title="Áreas detectadas" items={summary?.areas_detectadas||[]}/><ProfileBlock title="Skills encontradas" items={summary?.skills_detectadas||[]}/><label className="field-label">Roles de búsqueda<textarea rows={5} value={terms} onChange={e=>setTerms(e.target.value)}/><small>Estos son los cargos que se consultarán en portales generalistas.</small></label><button className="btn dark" onClick={saveTerms}>Guardar términos</button></>:<EmptyMini text="Sube un CV para construir tu perfil."/>}</section></div></>;
}

function ProfileBlock({title,items}:{title:string;items:string[]}){return <div className="profile-block"><span>{title}</span><div className="chip-wrap">{items.length?items.map(x=><span className="chip" key={x}>{x}</span>):<small className="muted">Sin elementos detectados</small>}</div></div>}
function Metric({label,value,hint,tone}:{label:string;value:number;hint:string;tone:string}){return <div className="metric-card"><div className={`metric-icon ${tone}`}></div><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>}
function Quick({n,title,text,onClick}:{n:string;title:string;text:string;onClick:()=>void}){return <button className="quick-item" onClick={onClick}><span>{n}</span><div><b>{title}</b><p>{text}</p></div><ArrowRightIcon size={16}/></button>}
function MiniJob({job}:{job:Job}){return <div className="mini-job"><div><b>{job.titulo}</b><span>{job.empresa||"Empresa no informada"} · {job.fuente}</span></div><div className={`score tiny ${job.puntaje>=70?"high":"mid"}`}><b>{job.puntaje}</b></div></div>}
function Badge({text,tone="violet"}:{text:string;tone?:string}){return <span className={`badge ${tone}`}>{text}</span>}
function SmallStat({label,value}:{label:string;value:string}){return <div className="small-stat"><span>{label}</span><b>{value}</b></div>}
function ErrorBox({text}:{text:string}){return <div className="callout error"><div><b>No se pudo completar la acción</b><p>{text}</p></div></div>}
function SectionLoader(){return <div className="section-loader"><div className="loader"/><span>Cargando…</span></div>}
function EmptyMini({text}:{text:string}){return <div className="empty-mini"><div className="empty-dot">·</div><span>{text}</span></div>}
function EmptyDetail(){return <div className="empty-detail"><BriefcaseIcon size={34}/><h3>Selecciona una oportunidad</h3><p>Verás descripción, calce, seguimiento, carta y el enlace directo para postular.</p></div>}
function safeName(s:string){return s.toLowerCase().replace(/[^a-z0-9áéíóúñ]+/gi,"_").replace(/^_|_$/g,"")}
function downloadText(content:string,name:string){const blob=new Blob([content],{type:"text/plain;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
