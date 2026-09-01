import streamlit as st


def aplicar_tema():
    st.markdown(
        """
<style>
:root {
  --bg: #f4f7fb;
  --surface: rgba(255,255,255,.92);
  --surface-2: #ffffff;
  --text: #172033;
  --muted: #68758a;
  --primary: #5b5ce2;
  --primary-dark: #4748c8;
  --cyan: #16b8c8;
  --border: #e5eaf2;
  --shadow: 0 10px 35px rgba(24, 34, 54, .07);
}

.stApp { background: radial-gradient(circle at 10% 0%, #eef0ff 0, transparent 27%), var(--bg); }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1320px; padding-top: 2rem; padding-bottom: 3rem; }

h1, h2, h3 { color: var(--text); letter-spacing: -.025em; }
p, label, .stCaption { color: var(--muted); }

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #141a2c 0%, #1b2440 100%);
  border-right: 0;
}
[data-testid="stSidebar"] * { color: #eef2ff !important; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
  border-radius: 10px; margin: 4px 8px; padding: 8px 10px;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08); }

.hero-card {
  background: linear-gradient(135deg, #171d32 0%, #28345e 72%, #375b7d 100%);
  border-radius: 22px; padding: 34px 38px; color: white; box-shadow: 0 18px 50px rgba(28,39,75,.18);
  margin-bottom: 24px; position: relative; overflow: hidden;
}
.hero-card:after { content:""; position:absolute; width:280px; height:280px; border-radius:50%; right:-90px; top:-110px; background:rgba(91,92,226,.35); }
.hero-card h1 { color:white; margin:0; font-size:2.25rem; }
.hero-card p { color:#cbd5ea; max-width:720px; margin:8px 0 0; font-size:1.02rem; }
.eyebrow { color:#9da8ff; font-size:.75rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:8px; }

.metric-card, .panel-card, .job-card {
  background: var(--surface); border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow);
}
.metric-card { padding:20px 22px; min-height:112px; }
.metric-card .label { color:var(--muted); font-size:.83rem; font-weight:650; }
.metric-card .value { color:var(--text); font-size:1.85rem; font-weight:800; margin-top:8px; }
.metric-card .hint { color:#8995a8; font-size:.76rem; margin-top:2px; }
.panel-card { padding:22px; margin-bottom:14px; }
.section-title { color:var(--text); font-size:1.1rem; font-weight:800; margin-bottom:4px; }
.section-subtitle { color:var(--muted); font-size:.88rem; margin-bottom:14px; }
.badge { display:inline-block; border-radius:999px; padding:5px 9px; background:#eef0ff; color:#5253c8; font-size:.73rem; font-weight:750; margin:0 5px 5px 0; }
.badge-green { background:#e7f8f2; color:#17765b; }
.badge-blue { background:#e7f5f8; color:#157789; }
.badge-gray { background:#f0f2f6; color:#657185; }

.stButton > button, .stDownloadButton > button, .stLinkButton > a {
  border-radius:10px !important; font-weight:700 !important; min-height:42px;
  border:1px solid var(--border) !important;
}
.stButton > button[kind="primary"] { background:linear-gradient(135deg,var(--primary),#7576ef)!important; border:0!important; box-shadow:0 8px 20px rgba(91,92,226,.22); }
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {
  border-radius:10px !important; border-color:#dfe5ee !important; background:white !important;
}
[data-testid="stDataFrame"] { border-radius:14px; overflow:hidden; border:1px solid var(--border); box-shadow:var(--shadow); }
[data-testid="stFileUploaderDropzone"] { border-radius:14px; border:1.5px dashed #bfc8d9; background:#fbfcff; }
hr { border-color:var(--border) !important; }

.login-shell { max-width:840px; margin:7vh auto 0; }
.login-brand { text-align:center; margin-bottom:22px; }
.login-brand .logo { width:58px; height:58px; border-radius:16px; background:linear-gradient(135deg,#5b5ce2,#16b8c8); display:inline-flex; align-items:center; justify-content:center; color:white; font-weight:900; font-size:1.35rem; box-shadow:0 10px 30px rgba(91,92,226,.22); }
.login-brand h1 { margin:12px 0 5px; font-size:2rem; }
.login-brand p { margin:0 auto; max-width:560px; }

div[data-testid="stStatusWidget"] { border-radius:14px; border:1px solid var(--border); background:white; }
</style>
""",
        unsafe_allow_html=True,
    )


def hero(titulo: str, subtitulo: str, eyebrow: str = "JOB SEARCH DASHBOARD"):
    st.markdown(
        f'<div class="hero-card"><div class="eyebrow">{eyebrow}</div><h1>{titulo}</h1><p>{subtitulo}</p></div>',
        unsafe_allow_html=True,
    )


def metricas(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, hint = item
        col.markdown(
            f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div><div class="hint">{hint}</div></div>',
            unsafe_allow_html=True,
        )
