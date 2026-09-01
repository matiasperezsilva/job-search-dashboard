import html
import streamlit as st


def aplicar_tema():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#f6f7fb;--surface:#fff;--surface2:#f9fafc;--ink:#101828;--muted:#667085;
  --line:#e6e9ef;--brand:#4f46e5;--brand2:#7c3aed;--blue:#2563eb;--green:#059669;
  --amber:#d97706;--red:#dc2626;--nav:#0b1220;--nav2:#111b2e;
  --shadow:0 1px 2px rgba(16,24,40,.04),0 8px 30px rgba(16,24,40,.06);
}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important}
.stApp{background:var(--bg);color:var(--ink)}
[data-testid="stHeader"]{background:transparent;height:0}
#MainMenu,footer,[data-testid="stDecoration"]{display:none!important}
.block-container{max-width:1240px;padding:2.2rem 2.5rem 4rem!important}
h1,h2,h3,h4{font-family:'Inter',sans-serif!important;color:var(--ink)!important;letter-spacing:-.025em}
p,label,.stCaption{color:var(--muted)}

/* sidebar */
[data-testid="stSidebar"]{background:linear-gradient(180deg,var(--nav),var(--nav2));border-right:1px solid rgba(255,255,255,.06)}
[data-testid="stSidebar"] *{color:#dbe5f5!important}
[data-testid="stSidebarNav"]{padding-top:.4rem}
[data-testid="stSidebarNav"] span{font-weight:600!important}
[data-testid="stSidebarNav"] a{border-radius:9px;margin:2px 10px;padding:9px 11px!important;transition:.16s ease}
[data-testid="stSidebarNav"] a:hover{background:rgba(255,255,255,.07)!important}
[data-testid="stSidebarNav"] a[aria-current="page"]{background:rgba(99,102,241,.18)!important;border:1px solid rgba(129,140,248,.18)}

/* headers */
.page-head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:2px 0 24px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.page-kicker{font-size:.72rem;font-weight:800;letter-spacing:.13em;color:var(--brand);text-transform:uppercase;margin-bottom:8px}
.page-title{font-size:2rem;font-weight:800;line-height:1.15;color:var(--ink);letter-spacing:-.04em}
.page-subtitle{font-size:.95rem;color:var(--muted);margin-top:7px;max-width:720px;line-height:1.55}

/* cards */
.metric-card,.surface-card,.job-card,.login-card{background:var(--surface);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
.metric-card{padding:18px 19px;min-height:112px}
.metric-label{font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#7c8799}
.metric-value{font-size:1.8rem;font-weight:800;color:var(--ink);margin:7px 0 2px;letter-spacing:-.04em}
.metric-hint{font-size:.76rem;color:#98a2b3}
.surface-card{padding:20px 22px;margin-bottom:16px}
.section-title{font-size:1rem;font-weight:750;color:var(--ink);margin-bottom:4px}
.section-subtitle{font-size:.84rem;color:var(--muted);margin-bottom:14px;line-height:1.5}

/* jobs */
.job-card{padding:18px 20px;margin:0 0 12px;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.job-card:hover{transform:translateY(-1px);border-color:#d8dcff;box-shadow:0 10px 32px rgba(16,24,40,.08)}
.job-top{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}
.job-title{font-size:1rem;font-weight:750;color:var(--ink);line-height:1.35}
.job-company{font-size:.82rem;color:var(--muted);margin-top:4px}
.job-score{min-width:48px;text-align:center;padding:6px 9px;border-radius:9px;font-weight:800;font-size:.82rem;background:#eef2ff;color:#4338ca}
.job-score.high{background:#ecfdf3;color:#067647}.job-score.low{background:#fff7ed;color:#b45309}
.job-meta{display:flex;gap:7px;flex-wrap:wrap;margin-top:13px}
.badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;background:#f2f4f7;color:#475467;font-size:.7rem;font-weight:650;border:1px solid #eaecf0}
.badge.purple{background:#f4f3ff;color:#5925dc;border-color:#e9e6ff}.badge.green{background:#ecfdf3;color:#067647;border-color:#d1fadf}.badge.blue{background:#eff8ff;color:#175cd3;border-color:#d1e9ff}

/* Streamlit controls */
.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:9px!important;min-height:40px!important;font-weight:650!important;border:1px solid #d0d5dd!important;background:#fff!important;color:#344054!important;box-shadow:0 1px 2px rgba(16,24,40,.04)!important}
.stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{border-color:#98a2b3!important;color:#101828!important}
.stButton>button[kind="primary"]{background:var(--brand)!important;color:white!important;border-color:var(--brand)!important;box-shadow:0 1px 2px rgba(16,24,40,.06),0 4px 12px rgba(79,70,229,.18)!important}
.stButton>button[kind="primary"]:hover{background:#4338ca!important;border-color:#4338ca!important}
.stTextInput input,.stTextArea textarea,[data-baseweb="select"]>div{border-radius:9px!important;border-color:#d0d5dd!important;background:#fff!important;color:#101828!important;box-shadow:none!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:#818cf8!important;box-shadow:0 0 0 3px rgba(99,102,241,.10)!important}
[data-testid="stFileUploaderDropzone"]{border:1.5px dashed #cbd5e1!important;border-radius:12px!important;background:#fbfcfe!important;padding:20px!important}
[data-testid="stAlert"]{border-radius:10px!important;border:1px solid var(--line)!important}
hr{border-color:var(--line)!important}

/* login */
.login-wrap{max-width:520px;margin:7vh auto 18px;text-align:center}
.login-logo{width:52px;height:52px;border-radius:13px;margin:0 auto 18px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#4f46e5,#2563eb);color:white;font-weight:800;font-size:1.1rem;box-shadow:0 12px 28px rgba(79,70,229,.22)}
.login-title{font-size:1.75rem;font-weight:800;color:#101828!important;letter-spacing:-.04em;margin:0}
.login-copy{font-size:.9rem;color:#667085!important;line-height:1.55;margin:8px auto 22px;max-width:460px}
[data-testid="stTabs"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 18px 18px;box-shadow:var(--shadow)}
[data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line)}
[data-baseweb="tab"]{font-weight:650!important;color:#667085!important}

/* search status */
.search-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0}
.search-stat{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}.search-stat b{display:block;color:var(--ink);font-size:1.15rem}.search-stat span{font-size:.72rem;color:var(--muted)}

@media(max-width:800px){.block-container{padding:1.4rem 1rem 3rem!important}.page-title{font-size:1.55rem}.page-head{align-items:flex-start}.job-top{gap:10px}}
</style>
""",
        unsafe_allow_html=True,
    )


def hero(titulo: str, subtitulo: str, eyebrow: str = "JOB SEARCH"):
    st.markdown(
        f'''<div class="page-head"><div><div class="page-kicker">{html.escape(eyebrow)}</div>
        <div class="page-title">{html.escape(titulo)}</div><div class="page-subtitle">{html.escape(subtitulo)}</div></div></div>''',
        unsafe_allow_html=True,
    )


def metricas(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, hint = item
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div><div class="metric-hint">{html.escape(str(hint))}</div></div>',
            unsafe_allow_html=True,
        )


def job_card(row):
    score = int(row.get("puntaje", 0) or 0)
    score_cls = "high" if score >= 70 else "low" if score < 50 else ""
    chips = []
    for value, cls in [
        (row.get("area"), "purple"), (row.get("fuente"), "blue"),
        (row.get("modalidad"), ""), (row.get("estado"), "green" if row.get("estado") in {"Postulada","Entrevista","Oferta recibida"} else "")
    ]:
        if value:
            chips.append(f'<span class="badge {cls}">{html.escape(str(value))}</span>')
    return f'''<div class="job-card"><div class="job-top"><div><div class="job-title">{html.escape(row.get("titulo") or "Sin título")}</div>
      <div class="job-company">{html.escape(row.get("empresa") or "Empresa no informada")}</div></div><div class="job-score {score_cls}">{score}</div></div>
      <div class="job-meta">{"".join(chips)}</div></div>'''
