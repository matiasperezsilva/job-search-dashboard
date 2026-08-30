import json
import streamlit as st
from jobsearch.services.collector import recolectar, FUENTES
from jobsearch.services.repository import guardar_ofertas
from jobsearch.services.scoring import evaluar_oferta
from jobsearch.config import ROOT
from jobsearch.services.profile_service import cargar_perfil, cv_activo

st.title("🔎 Buscar ofertas")
perfil = cargar_perfil()
resumen = perfil.get("resumen", {})
terminos_cv = resumen.get("terminos_busqueda", [])

if not cv_activo():
    st.warning(
        "Aún no has cargado un currículum. Puedes probar la aplicación con el perfil de demostración, "
        "pero para búsquedas personalizadas primero ve a **Currículum**."
    )
else:
    st.success("Búsqueda personalizada con el currículum activo.")

st.write("La app usa términos derivados del CV para consultar los portales y después puntúa cada oferta contra ese mismo perfil.")

terminos_txt = st.text_area(
    "Términos que se usarán en esta búsqueda",
    ", ".join(terminos_cv),
    height=100,
    help="Puedes hacer ajustes temporales. No modifican el perfil guardado.",
)
terminos = list(dict.fromkeys(t.strip() for t in terminos_txt.split(",") if t.strip()))[:25]

fuentes_default = ["GetOnBoard", "Computrabajo", "ChileTrabajos", "Laborum", "Trabajando.com", "BNE"]
fuentes = st.multiselect("Fuentes", list(FUENTES), default=fuentes_default)

with st.expander("Inicio de sesión en portales (opcional)"):
    st.info(
        "La versión de portafolio no necesita tus credenciales. Las fuentes públicas funcionan sin login. "
        "LinkedIn queda como integración opcional y no intenta resolver CAPTCHA ni evadir controles de acceso."
    )

col1, col2 = st.columns(2)
if col1.button("Ejecutar búsqueda", type="primary", disabled=not fuentes or not terminos):
    with st.status("Buscando ofertas según tu CV...", expanded=True) as status:
        st.write("Términos:", ", ".join(terminos))
        ofertas, errores = recolectar(fuentes, terminos=terminos)
        nuevas = guardar_ofertas(ofertas, perfil, evaluar_oferta)
        st.write(f"{len(ofertas)} ofertas procesadas; {nuevas} nuevas guardadas.")
        for error in errores:
            st.warning(f"{error['fuente']}: {error['error']}")
        status.update(label="Búsqueda finalizada", state="complete")

if col2.button("Cargar datos de demostración"):
    path = ROOT / "data" / "ejemplo_ofertas.json"
    ofertas = json.loads(path.read_text(encoding="utf-8"))
    nuevas = guardar_ofertas(ofertas, perfil, evaluar_oferta)
    st.success(f"Datos de demostración cargados ({nuevas} nuevos).")
