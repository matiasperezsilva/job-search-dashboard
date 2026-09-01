"use client";

import { createClient, SupabaseClient, Session } from "@supabase/supabase-js";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api } from "../lib/api";
import type { DashboardData, Job, ProfileData, SearchRun, View } from "../lib/types";
import {
  HomeIcon, SearchIcon, BriefcaseIcon, CheckIcon, FileIcon, LogoutIcon,
  ExternalIcon, SparkIcon, UploadIcon, ArrowRightIcon, RefreshIcon,
} from "./icons";

const SOURCES = ["GetOnBoard", "Computrabajo", "ChileTrabajos", "Laborum", "Trabajando.com", "BNE", "LinkedIn"];

export default function AppClient({ supabaseUrl, supabaseKey, forceRecovery = false }: { supabaseUrl: string; supabaseKey: string; forceRecovery?: boolean }) {
  const supabase = useMemo<SupabaseClient | null>(() => {
    if (!supabaseUrl || !supabaseKey) return null;
    return createClient(supabaseUrl, supabaseKey);
  }, [supabaseUrl, supabaseKey]);
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [view, setView] = useState<View>("dashboard");
  const [recovery, setRecovery] = useState(forceRecovery);

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    if (typeof window !== "undefined" && (forceRecovery || window.location.pathname === "/account/update-password" || window.location.hash.includes("type=recovery"))) setRecovery(true);
    const { data } = supabase.auth.onAuthStateChange((event, next) => { if (event === "PASSWORD_RECOVERY") setRecovery(true); setSession(next); });
    return () => data.subscription.unsubscribe();
  }, [supabase, forceRecovery]);

  if (!supabase) return <SetupError />;
  if (!ready) return <FullLoader label="Preparando tu espacio…" />;
  if (!session) return <AuthView supabase={supabase} />;
  if (recovery) return <UpdatePasswordView supabase={supabase} onDone={async()=>{setRecovery(false); await supabase.auth.signOut(); if(typeof window!=="undefined") window.location.assign("/");}} />;

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
          {view === "profile" && <ProfilePage token={session.access_token} supabase={supabase} />}
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

function authErrorMessage(message: string) {
  const m = message.toLowerCase();
  if (m.includes("rate limit") || m.includes("too many")) return "Se han realizado demasiados envíos de correo en poco tiempo. Espera unos minutos y vuelve a intentarlo.";
  if (m.includes("invalid login credentials")) return "Correo o contraseña incorrectos.";
  if (m.includes("email not confirmed")) return "Debes confirmar tu correo antes de iniciar sesión.";
  if (m.includes("password should be")) return "La contraseña no cumple los requisitos mínimos de seguridad.";
  return message || "No se pudo completar la acción.";
}

function AuthView({ supabase }: { supabase: SupabaseClient }) {
  const [mode, setMode] = useState<"login" | "signup" | "reset">("login");
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
      } else if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password, options:{ emailRedirectTo: typeof window!=="undefined" ? window.location.origin : undefined } });
        if (error) throw error;
        setMessage("Cuenta creada. Revisa tu correo para confirmar la dirección si está habilitada la verificación.");
      } else {
        const redirectTo = `${window.location.origin}/account/update-password`;
        const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
        if (error) throw error;
        setMessage("Te enviamos un enlace para crear una nueva contraseña. Revisa tu correo.");
      }
    } catch (err) { setMessage(authErrorMessage(err instanceof Error ? err.message : "No se pudo completar la acción.")); }
    finally { setLoading(false); }
  };

  return (
    <div className="auth-layout">
      <section className="auth-brand-panel">
        <div className="brand-mark large">JS</div>
        <div className="auth-brand-copy"><span className="eyebrow">JOB SEARCH DASHBOARD</span><h1>Encuentra oportunidades que sí calzan contigo.</h1><p>Tu CV se convierte en un perfil de búsqueda inteligente. Encuentra vacantes, prioriza el calce y gestiona cada postulación desde un solo lugar.</p></div>
        <div className="feature-row"><span>01</span><p><b>Perfil automático</b><br/>Extraemos áreas, competencias y roles desde tu currículum, sin limitarlo a una industria.</p></div>
        <div className="feature-row"><span>02</span><p><b>Menos ruido</b><br/>Filtramos cargos ajenos a software, páginas SEO y resultados irrelevantes.</p></div>
        <div className="feature-row"><span>03</span><p><b>Seguimiento completo</b><br/>Vacantes, postulaciones y cartas en un mismo flujo.</p></div>
      </section>
      <section className="auth-form-panel"><div className="auth-form-wrap">
        <div className="mobile-logo"><div className="brand-mark">JS</div><b>Job Search</b></div>
        <span className="eyebrow dark">{mode === "reset" ? "RECUPERAR ACCESO" : "BIENVENIDO"}</span>
        <h2>{mode === "login" ? "Inicia sesión" : mode === "signup" ? "Crea tu cuenta" : "Recupera tu contraseña"}</h2>
        <p className="muted">{mode === "login" ? "Continúa con tu búsqueda laboral." : mode === "signup" ? "Empieza a construir tu espacio de oportunidades." : "Te enviaremos un enlace seguro para definir una nueva contraseña."}</p>
        {mode !== "reset" && <div className="auth-tabs"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Iniciar sesión</button><button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>Crear cuenta</button></div>}
        <form onSubmit={submit} className="form-stack">
          <label>Correo electrónico<input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="tu@email.com" required/></label>
          {mode !== "reset" && <label>Contraseña<input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" minLength={8} required/></label>}
          <button className="btn primary xl" disabled={loading}>{loading ? "Procesando…" : mode === "login" ? "Entrar al dashboard" : mode === "signup" ? "Crear mi cuenta" : "Enviar enlace de recuperación"}<ArrowRightIcon size={18}/></button>
        </form>
        {mode === "login" && <button className="text-link" onClick={()=>{setMode("reset");setMessage("")}}>¿Olvidaste tu contraseña?</button>}
        {mode === "reset" && <button className="text-link" onClick={()=>{setMode("login");setMessage("")}}>← Volver al inicio de sesión</button>}
        {message && <div className="notice">{message}</div>}
        <p className="auth-foot">Tus datos se almacenan de forma privada en Supabase y están separados por usuario.</p>
      </div></section>
    </div>
  );
}

function UpdatePasswordView({supabase,onDone}:{supabase:SupabaseClient;onDone:()=>Promise<void>}){
  const [password,setPassword]=useState(""); const [confirm,setConfirm]=useState(""); const [loading,setLoading]=useState(false); const [message,setMessage]=useState("");
  const save=async(e:FormEvent)=>{e.preventDefault();setMessage(""); if(password!==confirm){setMessage("Las contraseñas no coinciden.");return;} if(password.length<8){setMessage("Usa al menos 8 caracteres.");return;} setLoading(true); try{const {error}=await supabase.auth.updateUser({password}); if(error) throw error; setMessage("Contraseña actualizada correctamente. Volverás al inicio de sesión."); setTimeout(()=>{void onDone()},900);}catch(err){setMessage(authErrorMessage(err instanceof Error?err.message:"No se pudo cambiar la contraseña."));}finally{setLoading(false)}};
  return <div className="center-screen recovery-screen"><div className="auth-card recovery-card"><div className="brand-mark">JS</div><span className="eyebrow dark">SEGURIDAD</span><h2>Crea una nueva contraseña</h2><p className="muted">Este enlace de recuperación ya validó tu identidad. Define una contraseña única para Job Search.</p><form className="form-stack" onSubmit={save}><label>Nueva contraseña<input type="password" value={password} onChange={e=>setPassword(e.target.value)} minLength={8} required/></label><label>Repetir contraseña<input type="password" value={confirm} onChange={e=>setConfirm(e.target.value)} minLength={8} required/></label><button className="btn primary xl" disabled={loading}>{loading?"Guardando…":"Actualizar contraseña"}</button></form>{message&&<div className="notice">{message}</div>}</div></div>
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
  const [profile,setProfile]=useState<ProfileData|null>(null); const [sources,setSources]=useState<string[]>(["Computrabajo","ChileTrabajos","Trabajando.com"]); const [mode,setMode]=useState("rapida");
  const [terms,setTerms]=useState(""); const [loading,setLoading]=useState(false); const [result,setResult]=useState<any>(null); const [run,setRun]=useState<SearchRun|null>(null); const [error,setError]=useState("");
  useEffect(()=>{api<ProfileData>("/profile",token).then(p=>{setProfile(p);setTerms((p.profile?.resumen?.terminos_busqueda||[]).join(", "));}).catch(e=>setError(e.message)); api<Partial<SearchRun>>("/search/active",token).then(active=>{if(active.id){setRun(active as SearchRun);setLoading(true);}}).catch(()=>{});},[token]);
  useEffect(()=>{if(!run?.id || !loading)return; let stopped=false; const poll=async()=>{try{const status=await api<SearchRun>(`/search/${run.id}`,token); if(stopped)return; setRun(status); if(status.status==="completed"){setResult(status.result||{});setLoading(false);} else if(status.status==="failed"){setError(status.error||"La búsqueda se interrumpió.");setLoading(false);}}catch(e){if(!stopped){setError(e instanceof Error?e.message:"No se pudo consultar el progreso.");setLoading(false);}}}; void poll(); const id=window.setInterval(()=>void poll(),2000); return()=>{stopped=true;window.clearInterval(id)}},[run?.id,loading,token]);
  const toggle=(s:string)=>setSources(v=>v.includes(s)?v.filter(x=>x!==s):[...v,s]);
  const startSearch=async()=>{setLoading(true);setError("");setResult(null);setRun(null);try{const r=await api<{run_id:string;status:string}>("/search",token,{method:"POST",body:JSON.stringify({sources,mode,terms:terms.split(",").map(x=>x.trim()).filter(Boolean)})});setRun({id:r.run_id,status:r.status as SearchRun["status"]});}catch(e){setError(e instanceof Error?e.message:"Error");setLoading(false);}};
  return <>
    <PageHeader eyebrow="DESCUBRIR" title="Encuentra oportunidades relevantes." text="Usamos tu perfil, experiencia y cargos objetivo para priorizar vacantes reales de distintas áreas profesionales."/>
    {!profile?.active && <div className="callout warning"><FileIcon/><div><b>Primero necesitamos tu currículum.</b><p>Sube un CV para generar términos y prioridades.</p></div><button className="btn dark" onClick={()=>go("profile")}>Ir a mi currículum</button></div>}
    <div className="search-layout">
      <section className="panel search-config"><div className="section-kicker">01 · Configuración</div><h3>Define cómo buscar</h3><div className="segmented"><button className={mode==="rapida"?"active":""} onClick={()=>setMode("rapida")}>Rápida <span>Recomendada</span></button><button className={mode==="exhaustiva"?"active":""} onClick={()=>setMode("exhaustiva")}>Exhaustiva <span>Más lenta</span></button></div><label className="field-label">Términos prioritarios<textarea value={terms} onChange={e=>setTerms(e.target.value)} rows={5}/><small>Usa cargos, no tecnologías aisladas. Ej: “qa software”, “cloud support”.</small></label></section>
      <section className="panel"><div className="section-title-row"><div><div className="section-kicker">02 · Fuentes</div><h3>Selecciona portales</h3></div><div className="source-presets"><button onClick={()=>setSources(["Computrabajo","ChileTrabajos","Trabajando.com"])}>Recomendadas</button><button onClick={()=>setSources(SOURCES)}>Todas</button></div></div><div className="source-grid">{SOURCES.map(s=><button key={s} className={`source-toggle ${sources.includes(s)?"selected":""}`} onClick={()=>toggle(s)}><span className="check-dot">{sources.includes(s)?"✓":""}</span><div><b>{s}</b><small>{s==="GetOnBoard"?"Especializado en tecnología · rápido":s==="LinkedIn"?"Búsqueda pública · puede limitar consultas":s==="Computrabajo"||s==="ChileTrabajos"||s==="Trabajando.com"?"HTML público · rápido":"Secundario · puede tardar"}</small></div></button>)}</div></section>
    </div>
    <div className="search-actions"><button className="btn primary xl" disabled={!profile?.active||loading||sources.length===0} onClick={startSearch}>{loading?<><span className="spinner"/>Búsqueda en curso…</>:<><SearchIcon/>Buscar oportunidades</>}</button><span className="muted">La búsqueda continúa en el servidor aunque una fuente tarde varios minutos.</span></div>
    {loading&&run&&<SearchProgress run={run}/>}
    {error&&<ErrorBox text={error}/>} {result&&<SearchResult result={result} onView={()=>go("jobs")}/>} 
  </>;
}

function SearchProgress({run}:{run:SearchRun}){
  const p=run.progress||{}; const current=p.current_source||"Preparando"; const i=p.source_index||0; const total=p.source_total||0; const pct=total?Math.max(8,Math.min(96,(i/total)*100)):12; const states=p.source_states||{};
  return <section className="panel search-progress"><div className="progress-head"><div><span className="pulse-dot"/><div><b>{run.status==="queued"?"Búsqueda en cola":"Buscando oportunidades"}</b><p>{p.message||`Consultando ${current}…`}</p></div></div><span>{i}/{total||"—"} fuentes</span></div><div className="progress-track"><i style={{width:`${pct}%`}}/></div><div className="source-progress-list">{Object.entries(states).map(([name,state])=><div key={name} className={`source-progress-item ${state.status}`}><span className="source-state-dot"/><b>{name}</b><small>{state.status==="pending"?"Pendiente":state.status==="running"?"Procesando…":state.status==="completed"?`${state.cantidad||0} resultados · ${state.segundos||0}s`:"No disponible"}</small></div>)}</div><small>La búsqueda corre en segundo plano. Puedes cambiar de sección y volver sin perder el progreso.</small></section>
}


function SearchResult({result,onView}:{result:any;onView:()=>void}){
  return <section className="panel result-panel"><div className="result-top"><div><span className="success-icon">✓</span><div><h3>Búsqueda finalizada</h3><p>{result.found} vacantes relevantes · {result.new} nuevas guardadas</p></div></div><button className="btn dark" onClick={onView}>Ver oportunidades <ArrowRightIcon size={16}/></button></div><div className="stats-strip">{(result.stats||[]).map((s:any)=><div key={s.fuente}><b>{s.fuente}</b><span>{s.cantidad} resultados · {s.segundos}s</span></div>)}</div>{(result.errors||[]).length>0&&<div className="source-errors">{result.errors.map((e:any)=><span key={e.fuente}>{e.fuente}: {e.error}</span>)}</div>}</section>
}

function JobsPage({ token }: { token:string }) {
  const [jobs,setJobs]=useState<Job[]>([]);
  const [min,setMin]=useState(40);
  const [source,setSource]=useState("");
  const [q,setQ]=useState("");
  const [scope,setScope]=useState<"active"|"favorites"|"hidden">("active");
  const [sort,setSort]=useState<"score"|"recent"|"found">("score");
  const [includeOld,setIncludeOld]=useState(false);
  const [selected,setSelected]=useState<Job|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [reeval,setReeval]=useState(false);

  const load=()=>{
    setLoading(true);
    const effectiveMin=scope==="active"?min:0;
    const flags=scope==="favorites"?"&favorite_only=true":scope==="hidden"?"&only_hidden=true&include_hidden=true":"";
    api<{items:Job[]}>(`/jobs?min_score=${effectiveMin}&sort=${sort}&include_old=${includeOld}${flags}${source?`&source=${encodeURIComponent(source)}`:""}${q?`&q=${encodeURIComponent(q)}`:""}`,token)
      .then(r=>{setJobs(r.items);if(selected){setSelected(r.items.find(x=>x.id===selected.id)||null)}})
      .catch(e=>setError(e.message))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{const t=setTimeout(load,200);return()=>clearTimeout(t)},[token,min,source,q,scope,sort,includeOld]);

  const reevaluate=async()=>{setReeval(true);setError("");try{await api("/jobs/reevaluate",token,{method:"POST"});load();}catch(e){setError(e instanceof Error?e.message:"Error");}finally{setReeval(false)}};
  const updateFlags=async(job:Job, values:{favorite?:boolean;hidden?:boolean})=>{
    try{
      await api(`/jobs/${job.id}/flags`,token,{method:"PUT",body:JSON.stringify(values)});
      if(values.hidden===true&&selected?.id===job.id)setSelected(null);
      await load();
    }catch(e){setError(e instanceof Error?e.message:"No se pudo actualizar la oportunidad.")}
  };

  const sortLabel=sort==="recent"?"Más recientes primero":sort==="found"?"Encontradas recientemente":"Ordenadas por calce";
  return <>
    <PageHeader eyebrow="OPORTUNIDADES" title="Vacantes priorizadas para ti." text="Guarda favoritas, oculta ruido, evita duplicados entre portales y prioriza oportunidades recientes." action={<button className="btn ghost" onClick={reevaluate} disabled={reeval}><RefreshIcon size={16}/>{reeval?"Reevaluando…":"Reevaluar base"}</button>}/>
    <div className="opportunity-tabs">
      <button className={scope==="active"?"active":""} onClick={()=>setScope("active")}>Oportunidades</button>
      <button className={scope==="favorites"?"active":""} onClick={()=>setScope("favorites")}>★ Favoritas</button>
      <button className={scope==="hidden"?"active":""} onClick={()=>setScope("hidden")}>Ocultas</button>
    </div>
    <div className="filters opportunity-filters">
      {scope==="active"&&<label>Calce mínimo<select value={min} onChange={e=>setMin(Number(e.target.value))}>{[0,30,40,50,60,70,80,90].map(v=><option key={v} value={v}>{v}+</option>)}</select></label>}
      <label>Fuente<select value={source} onChange={e=>setSource(e.target.value)}><option value="">Todas</option>{SOURCES.map(s=><option key={s}>{s}</option>)}</select></label>
      <label>Orden<select value={sort} onChange={e=>setSort(e.target.value as "score"|"recent"|"found")}><option value="score">Mejor calce</option><option value="recent">Más recientes</option><option value="found">Recién encontradas</option></select></label><label className="toggle-filter"><input type="checkbox" checked={includeOld} onChange={e=>setIncludeOld(e.target.checked)}/><span>Incluir antiguas</span></label>
      <label className="search-field">Buscar<input value={q} onChange={e=>setQ(e.target.value)} placeholder="Cargo o empresa…"/></label>
    </div>
    {scope==="hidden"&&<div className="notice subtle curation-note">Las ofertas ocultas no vuelven al listado principal aunque aparezcan de nuevo en una búsqueda. Puedes restaurarlas cuando quieras.</div>}
    {error&&<ErrorBox text={error}/>} {loading?<SectionLoader/>:<div className="jobs-layout"><section><div className="list-head"><span>{jobs.length} {scope==="favorites"?"favoritas":scope==="hidden"?"ocultas":"oportunidades"}</span><small>{sortLabel}</small></div><div className="job-list">{jobs.map(job=><JobCard key={job.id} job={job} selected={selected?.id===job.id} onSelect={()=>setSelected(job)} onFavorite={()=>updateFlags(job,{favorite:!job.favorite})} onHide={()=>updateFlags(job,{hidden:!job.hidden})}/>) }{jobs.length===0&&<EmptyMini text={scope==="favorites"?"Aún no has marcado favoritas.":scope==="hidden"?"No tienes ofertas ocultas.":"No hay oportunidades con estos filtros."}/>}</div></section><aside className="job-detail">{selected?<JobDetail job={selected} token={token} onSaved={load} onFavorite={()=>updateFlags(selected,{favorite:!selected.favorite})} onHide={()=>updateFlags(selected,{hidden:!selected.hidden})}/>:<EmptyDetail/>}</aside></div>}
  </>;
}

function JobCard({job,selected,onSelect,onFavorite,onHide}:{job:Job;selected:boolean;onSelect:()=>void;onFavorite:()=>void;onHide:()=>void}){
  return <article className={`job-card ${selected?"selected":""} ${job.hidden?"hidden-job":""}`} onClick={onSelect}>
    <div className="job-card-main"><div className="company-avatar">{(job.empresa||"?").slice(0,1).toUpperCase()}</div><div className="job-copy"><div className="job-title-line"><h3>{job.titulo}</h3>{job.favorite&&<span className="favorite-mark" title="Favorita">★</span>}</div><p>{job.empresa||"Empresa no informada"}</p><div className="job-meta-line"><span>{jobDateLabel(job)}</span>{job.duplicate_count&&job.duplicate_count>1&&<span className="duplicate-note">También encontrada en {job.duplicate_count-1} fuente{job.duplicate_count-1===1?"":"s"} más</span>}</div><div className="badges"><Badge text={job.area||"Sin clasificar"}/><Badge text={job.fuente||"Fuente"} tone="blue"/>{job.duplicate_sources&&job.duplicate_sources.length>1&&<Badge text={`${job.duplicate_sources.length} portales`} tone="gray"/>}{job.is_old&&<Badge text="Antigua" tone="gray"/>}{job.modalidad&&<Badge text={job.modalidad}/>}<Badge text={job.estado||"Sin gestionar"} tone="gray"/></div></div></div>
    <div className="job-card-side"><div className={`score ${job.puntaje>=70?"high":job.puntaje>=50?"mid":"low"}`}><b>{job.puntaje}</b><span>calce</span></div><div className="card-actions"><button className={`icon-action ${job.favorite?"active":""}`} title={job.favorite?"Quitar de favoritas":"Marcar favorita"} onClick={e=>{e.stopPropagation();onFavorite()}}>{job.favorite?"★":"☆"}</button><button className="icon-action" title={job.hidden?"Restaurar oportunidad":"Ocultar oportunidad"} onClick={e=>{e.stopPropagation();onHide()}}>{job.hidden?"↩":"×"}</button></div></div>
  </article>
}

function JobDetail({job,token,onSaved,onFavorite,onHide}:{job:Job;token:string;onSaved:()=>void;onFavorite:()=>void;onHide:()=>void}){
  const [tab,setTab]=useState<"info"|"tracking"|"letter">("info");
  return <div className="detail-card"><div className="detail-head"><span className="eyebrow dark">DETALLE</span><h2>{job.titulo}</h2><p>{job.empresa||"Empresa no informada"}</p><span className="detail-date">{jobDateLabel(job)}</span><div className="detail-actions">{job.link?<a className="btn primary" href={job.link} target="_blank" rel="noopener noreferrer"><ExternalIcon size={17}/>Ver oferta / Postular</a>:<button className="btn disabled" disabled>Enlace no disponible</button>}<button className={`btn ghost compact-btn ${job.favorite?"favorite-btn":""}`} onClick={onFavorite}>{job.favorite?"★ Favorita":"☆ Guardar favorita"}</button><button className="btn ghost compact-btn" onClick={onHide}>{job.hidden?"Restaurar":"Ocultar"}</button></div></div><div className="tabs"><button className={tab==="info"?"active":""} onClick={()=>setTab("info")}>Resumen</button><button className={tab==="tracking"?"active":""} onClick={()=>setTab("tracking")}>Seguimiento</button><button className={tab==="letter"?"active":""} onClick={()=>setTab("letter")}>Carta</button></div>{tab==="info"&&<div className="detail-body"><div className="detail-stat-grid"><SmallStat label="Calce" value={`${job.puntaje}/100`}/><SmallStat label="Área" value={job.area||"—"}/><SmallStat label="Fuente" value={job.duplicate_sources&&job.duplicate_sources.length>1?`${job.duplicate_sources.length} portales`:job.fuente||"—"}/></div>{job.duplicate_sources&&job.duplicate_sources.length>1&&<div className="notice subtle duplicate-detail">También detectada en: {job.duplicate_sources.join(", ")}. Mostramos una sola tarjeta para evitar ruido.</div>}<MatchBreakdownView job={job}/><h4>Por qué aparece aquí</h4><p>{job.razon||"Sin detalle de evaluación."}</p><h4>Descripción</h4><p className="description-text">{job.descripcion||"La fuente no entregó descripción completa."}</p></div>}{tab==="tracking"&&<Tracking job={job} token={token} onSaved={onSaved}/>} {tab==="letter"&&<Letter job={job} token={token}/>}</div>
}

function jobDateLabel(job:Job){
  const raw=job.published_at||job.first_seen;
  const prefix=job.published_at?"Publicada":"Encontrada";
  if(!raw)return "Fecha no disponible";
  const date=new Date(raw);
  if(Number.isNaN(date.getTime()))return "Fecha no disponible";
  const days=Math.max(0,Math.floor((Date.now()-date.getTime())/86400000));
  if(days===0)return `${prefix} hoy`;
  if(days===1)return `${prefix} hace 1 día`;
  if(days<30)return `${prefix} hace ${days} días`;
  return `${prefix} el ${new Intl.DateTimeFormat("es-CL",{day:"2-digit",month:"short",year:"numeric"}).format(date)}`;
}


function MatchBreakdownView({job}:{job:Job}){
  const breakdown=job.match_breakdown;
  const components=breakdown?.components||[];
  if(!components.length){
    return <section className="match-breakdown legacy"><div className="match-title-row"><div><span className="section-kicker">EXPLICABILIDAD</span><h4>Cómo calculamos este match</h4></div><span className="match-verdict">Pendiente de reevaluar</span></div><p className="muted">Esta oportunidad fue evaluada antes de incorporar el desglose. Usa “Reevaluar base” para generar la explicación completa.</p></section>;
  }
  return <section className="match-breakdown">
    <div className="match-title-row">
      <div><span className="section-kicker">MATCH EXPLICADO</span><h4>Cómo se construye el {job.puntaje}/100</h4></div>
      <span className={`match-verdict ${job.puntaje>=70?"high":job.puntaje>=50?"mid":"low"}`}>{breakdown?.verdict||"Evaluado"}</span>
    </div>
    <div className="match-components">
      {components.map((c,i)=>{
        const value=Number(c.value||0);
        const positive=value>0;
        const negative=value<0;
        const width=c.max?Math.min(100,Math.max(0,(Math.abs(value)/c.max)*100)):Math.min(100,Math.abs(value)*4);
        return <div className="match-component" key={`${c.label}-${i}`}>
          <div className="match-component-head"><span>{c.label}</span><b className={negative?"negative":positive?"positive":"neutral"}>{value>0?"+":""}{value}</b></div>
          {c.max&&<div className="match-bar"><span className={negative?"negative":positive?"positive":"neutral"} style={{width:`${width}%`}}/></div>}
          {c.detail&&<small>{c.detail}</small>}
        </div>
      })}
    </div>
    {(breakdown?.matched_roles?.length||breakdown?.matched_skills?.length)?<div className="match-evidence">
      {!!breakdown?.matched_roles?.length&&<div><span>Roles coincidentes</span><div className="chip-wrap">{breakdown.matched_roles.map(x=><Badge key={x} text={x} tone="blue"/>)}</div></div>}
      {!!breakdown?.matched_skills?.length&&<div><span>Competencias coincidentes</span><div className="chip-wrap">{breakdown.matched_skills.map(x=><Badge key={x} text={x}/>)}</div></div>}
    </div>:null}
    {typeof breakdown?.pre_clamp_score==="number"&&breakdown.pre_clamp_score!==job.puntaje&&<small className="muted">Puntaje previo a límites: {breakdown.pre_clamp_score}. El resultado final se expresa entre 0 y 100.</small>}
  </section>
}

function Tracking({job,token,onSaved}:{job:Job;token:string;onSaved:()=>void}){
  const [state,setState]=useState(job.estado||"Guardada");const [notes,setNotes]=useState(job.notas||"");const [saving,setSaving]=useState(false);const [msg,setMsg]=useState("");
  const save=async()=>{setSaving(true);try{await api(`/jobs/${job.id}/application`,token,{method:"PUT",body:JSON.stringify({state,notes})});setMsg("Seguimiento actualizado.");onSaved();}catch(e){setMsg(e instanceof Error?e.message:"Error")}finally{setSaving(false)}};
  return <div className="detail-body form-stack"><label>Estado<select value={state} onChange={e=>setState(e.target.value)}>{["Guardada","Postulada","Entrevista","Rechazada","Oferta recibida"].map(s=><option key={s}>{s}</option>)}</select></label><label>Notas<textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={6} placeholder="Fecha de postulación, contacto, entrevista, observaciones…"/></label><button className="btn primary" onClick={save} disabled={saving}>{saving?"Guardando…":"Guardar seguimiento"}</button>{msg&&<small className="muted">{msg}</small>}</div>
}

function Letter({job,token}:{job:Job;token:string}){
  const [content,setContent]=useState("");const [mode,setMode]=useState("local");const [loading,setLoading]=useState(false);const [msg,setMsg]=useState("");
  const [ai,setAi]=useState<{configured:boolean;provider?:string|null;model?:string|null}>({configured:false});
  useEffect(()=>{api<any>(`/jobs/${job.id}/letter`,token).then(r=>{setContent(r.contenido||"");setMode(r.modo||"local")}).catch(()=>{});api<any>(`/settings/ai`,token).then(setAi).catch(()=>{})},[job.id,token]);
  const generate=async()=>{setLoading(true);setMsg("");try{const r=await api<any>(`/jobs/${job.id}/letter/generate`,token,{method:"POST",body:JSON.stringify({mode})});setContent(r.content);setMsg(mode==="inteligente"?"Carta generada con Gemini.":"Borrador local generado.")}catch(e){setMsg(e instanceof Error?e.message:"Error")}finally{setLoading(false)}};
  const save=async()=>{await api(`/jobs/${job.id}/letter`,token,{method:"PUT",body:JSON.stringify({content,mode})});setMsg("Borrador guardado.")};
  return <div className="detail-body form-stack"><div className="segmented compact"><button className={mode==="local"?"active":""} onClick={()=>setMode("local")}>Local</button><button className={mode==="inteligente"?"active":""} onClick={()=>setMode("inteligente")}>Inteligente · Gemini</button></div>{mode==="inteligente"&&<div className={`ai-config-note ${ai.configured?"ready":"missing"}`}>{ai.configured?<>✓ Gemini listo · <b>{ai.model}</b></>:<>Falta configurar <b>GEMINI_API_KEY</b> en Render.</>}</div>}<button className="btn dark" onClick={generate} disabled={loading||(mode==="inteligente"&&!ai.configured)}><SparkIcon size={17}/>{loading?"Generando…":mode==="inteligente"?"Generar con Gemini":"Generar borrador local"}</button><label>Borrador<textarea rows={13} value={content} onChange={e=>setContent(e.target.value)} placeholder="Genera o escribe aquí tu carta…"/></label><div className="button-row"><button className="btn primary" onClick={save} disabled={!content.trim()}>Guardar borrador</button><button className="btn ghost" disabled={!content.trim()} onClick={()=>downloadText(content,`carta_${safeName(job.empresa||"empresa")}.txt`)}>Descargar</button></div>{msg&&<small className="muted">{msg}</small>}</div>
}

function ApplicationsPage({token}:{token:string}){
  const [jobs,setJobs]=useState<Job[]>([]); const [state,setState]=useState(""); const [loading,setLoading]=useState(true);
  useEffect(()=>{api<{items:Job[]}>(`/jobs?min_score=0&include_hidden=true${state?`&state=${encodeURIComponent(state)}`:""}`,token).then(r=>setJobs(r.items.filter(j=>j.estado&&j.estado!=="Sin gestionar"))).finally(()=>setLoading(false))},[token,state]);
  return <><PageHeader eyebrow="SEGUIMIENTO" title="Tus procesos, en orden." text="Conserva contexto de cada postulación y vuelve rápidamente a la publicación original."/><div className="filters one"><label>Estado<select value={state} onChange={e=>setState(e.target.value)}><option value="">Todos</option>{["Guardada","Postulada","Entrevista","Rechazada","Oferta recibida"].map(s=><option key={s}>{s}</option>)}</select></label></div>{loading?<SectionLoader/>:<div className="application-grid">{jobs.map(j=><article className="application-card" key={j.id}><div><Badge text={j.estado||""} tone="blue"/><h3>{j.titulo}</h3><p>{j.empresa||"Empresa no informada"}</p></div><p className="app-notes">{j.notas||"Sin notas todavía."}</p><div className="app-foot"><span>{j.fuente} · {j.puntaje} pts</span>{j.link&&<a href={j.link} target="_blank" rel="noopener noreferrer">Ver oferta <ExternalIcon size={14}/></a>}</div></article>)}{jobs.length===0&&<EmptyMini text="Aún no tienes procesos gestionados."/>}</div>}</>;
}

function ProfilePage({token,supabase}:{token:string;supabase:SupabaseClient}){
  const [profile,setProfile]=useState<ProfileData|null>(null);
  const [file,setFile]=useState<File|null>(null);
  const [uploading,setUploading]=useState(false);
  const [terms,setTerms]=useState("");
  const [msg,setMsg]=useState("");

  const [modalities,setModalities]=useState<string[]>([]);
  const [locations,setLocations]=useState("");
  const [salary,setSalary]=useState("");
  const [prefSaving,setPrefSaving]=useState(false);
  const [prefMsg,setPrefMsg]=useState("");

  const hydrate=(p:ProfileData)=>{
    setProfile(p);
    setTerms((p.profile?.resumen?.terminos_busqueda||[]).join(", "));
    const prefs=p.profile?.preferencias;
    setModalities(prefs?.modalidades||[]);
    setLocations((prefs?.ubicaciones||[]).join(", "));
    setSalary(prefs?.renta_minima?String(prefs.renta_minima):"");
  };
  const load=()=>api<ProfileData>("/profile",token).then(hydrate);
  useEffect(()=>{load()},[token]);

  const upload=async()=>{
    if(!file)return;
    setUploading(true);setMsg("");
    try{
      const fd=new FormData();fd.append("file",file);
      await api("/profile/upload",token,{method:"POST",body:fd});
      await load();
      setMsg("Currículum actualizado correctamente. Tus preferencias laborales se conservaron.");
    }catch(e){setMsg(e instanceof Error?e.message:"Error")}
    finally{setUploading(false)}
  };

  const saveTerms=async()=>{
    await api("/profile/terms",token,{method:"PUT",body:JSON.stringify({terms:terms.split(",").map(x=>x.trim()).filter(Boolean)})});
    setMsg("Términos actualizados.");
    load();
  };

  const toggleModality=(mode:string)=>setModalities(v=>v.includes(mode)?v.filter(x=>x!==mode):[...v,mode]);

  const savePreferences=async()=>{
    setPrefSaving(true);setPrefMsg("");
    try{
      const body={
        modalidades:modalities,
        ubicaciones:locations.split(",").map(x=>x.trim()).filter(Boolean),
        renta_minima:salary?Number(salary):null,
        moneda:"CLP",
      };
      await api("/profile/preferences",token,{method:"PUT",body:JSON.stringify(body)});
      await load();
      setPrefMsg("Preferencias guardadas. Usa “Reevaluar base” para aplicarlas a oportunidades antiguas.");
    }catch(e){setPrefMsg(e instanceof Error?e.message:"No se pudieron guardar las preferencias.")}
    finally{setPrefSaving(false)}
  };

  const [currentPassword,setCurrentPassword]=useState("");
  const [newPassword,setNewPassword]=useState("");
  const [securityMsg,setSecurityMsg]=useState("");
  const [securityLoading,setSecurityLoading]=useState(false);
  const changePassword=async()=>{
    setSecurityMsg("");
    if(newPassword.length<8){setSecurityMsg("La nueva contraseña debe tener al menos 8 caracteres.");return;}
    setSecurityLoading(true);
    try{
      const {error}=await supabase.auth.updateUser({password:newPassword,current_password:currentPassword});
      if(error)throw error;
      setSecurityMsg("Contraseña actualizada correctamente.");
      setCurrentPassword("");setNewPassword("");
    }catch(e){setSecurityMsg(authErrorMessage(e instanceof Error?e.message:"No se pudo actualizar la contraseña."));}
    finally{setSecurityLoading(false)}
  };

  const summary=profile?.profile?.resumen;
  return <>
    <PageHeader eyebrow="PERFIL" title="Tu perfil profesional define la búsqueda." text="Combina lo que acredita tu CV con los cargos y condiciones laborales que realmente quieres."/>
    <div className="profile-layout">
      <section className="panel">
        <div className="section-kicker">CURRÍCULUM</div>
        <h3>{profile?.active?"Actualizar archivo":"Sube tu primer CV"}</h3>
        <div className="upload-zone"><UploadIcon size={28}/><b>{file?file.name:"Arrastra o selecciona tu currículum"}</b><span>PDF, DOCX o TXT</span><input type="file" accept=".pdf,.docx,.txt" onChange={e=>setFile(e.target.files?.[0]||null)}/></div>
        <button className="btn primary full" onClick={upload} disabled={!file||uploading}>{uploading?"Procesando CV…":"Analizar y activar currículum"}</button>
        {msg&&<div className="notice subtle">{msg}</div>}
      </section>
      <section className="panel">
        <div className="section-kicker">PERFIL ACTIVO</div>
        <h3>{profile?.cv_name||"Sin currículum activo"}</h3>
        {profile?.active?<>
          <ProfileBlock title="Áreas detectadas" items={summary?.areas_detectadas||[]}/>
          <ProfileBlock title="Competencias detectadas" items={summary?.skills_detectadas||[]}/>
          {summary?.anos_experiencia!==undefined&&summary?.anos_experiencia!==null&&<div className="profile-experience"><span>Experiencia profesional estimada</span><b>{summary.anos_experiencia>0?`${summary.anos_experiencia} años`:"No determinada con seguridad"}</b><small>Se usa como señal de match cuando la oferta exige años explícitos.</small></div>}
          <label className="field-label">Cargos objetivo<textarea rows={5} value={terms} onChange={e=>setTerms(e.target.value)}/><small>Puedes editarlos libremente: son los cargos que se consultarán en los portales de empleo.</small></label>
          <button className="btn dark" onClick={saveTerms}>Guardar términos</button>
        </>:<EmptyMini text="Sube un CV para construir tu perfil."/>}
      </section>
    </div>

    {profile?.active&&<section className="panel preferences-panel">
      <div className="section-title-row"><div><div className="section-kicker">PREFERENCIAS LABORALES</div><h3>Qué condiciones hacen atractiva una oferta para ti</h3><p className="muted">Son señales de match, no filtros destructivos. Si una vacante no publica un dato, no pierde puntos por eso.</p></div></div>
      <div className="preferences-grid">
        <div className="preference-group">
          <span className="field-label compact-label">Modalidad aceptada</span>
          <div className="preference-options">
            {["remoto","híbrido","presencial"].map(mode=><button type="button" key={mode} className={`preference-pill ${modalities.includes(mode)?"selected":""}`} onClick={()=>toggleModality(mode)}>{modalities.includes(mode)?"✓ ":""}{mode[0].toUpperCase()+mode.slice(1)}</button>)}
          </div>
          <small>Selecciona una o varias. Si no marcas ninguna, la modalidad será neutral.</small>
        </div>
        <label className="field-label">Ubicaciones preferidas<input value={locations} onChange={e=>setLocations(e.target.value)} placeholder="Ej: Santiago, Providencia, Las Condes"/><small>Sepáralas por coma. Las ofertas remotas no se penalizan por ubicación.</small></label>
        <label className="field-label">Renta mínima mensual (CLP)<input type="number" min="0" step="50000" value={salary} onChange={e=>setSalary(e.target.value)} placeholder="Ej: 1200000"/><small>Solo influye cuando la oferta publica una renta comparable. Si no informa sueldo, el impacto es 0.</small></label>
      </div>
      <div className="preference-actions"><button className="btn primary" onClick={savePreferences} disabled={prefSaving}>{prefSaving?"Guardando…":"Guardar preferencias"}</button>{prefMsg&&<span className="muted">{prefMsg}</span>}</div>
    </section>}

    <section className="panel security-panel">
      <div className="section-kicker">SEGURIDAD</div>
      <div className="security-grid">
        <div><h3>Cambiar contraseña</h3><p className="muted">Usa una contraseña única para esta aplicación. No reutilices la de tu correo u otros servicios.</p></div>
        <div className="form-stack">
          <label>Contraseña actual<input type="password" value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)} autoComplete="current-password"/></label>
          <label>Nueva contraseña<input type="password" value={newPassword} onChange={e=>setNewPassword(e.target.value)} minLength={8} autoComplete="new-password"/></label>
          <button className="btn dark" disabled={securityLoading||!currentPassword||!newPassword} onClick={changePassword}>{securityLoading?"Actualizando…":"Cambiar contraseña"}</button>
          {securityMsg&&<div className="notice subtle">{securityMsg}</div>}
        </div>
      </div>
    </section>
  </>;
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
