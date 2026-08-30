import csv
import io
import os
from pathlib import Path

import streamlit as st

from jobsearch.services.profile_service import cargar_perfil, texto_cv
from jobsearch.services.letters import (
    ConfigAPI,
    coincidencias_cv_oferta,
    config_api_desde_entorno,
    generar_borrador_local,
    generar_carta_inteligente,
)
from jobsearch.services.repository import (
    guardar_carta,
    guardar_estado,
    listar_ofertas,
    obtener_carta,
)

st.title("💼 Ofertas")
c1, c2 = st.columns(2)
min_score = c1.slider("Puntaje mínimo", 0, 100, 40, 5)
fuente = c2.text_input("Filtrar por fuente")
rows = listar_ofertas(min_score, fuente or None)
st.caption(f"{len(rows)} resultados")

if rows:
    display = [
        {k: r[k] for k in ["puntaje", "area", "titulo", "empresa", "fuente", "modalidad", "estado", "link"]}
        for r in rows
    ]
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={"link": st.column_config.LinkColumn("Enlace")},
    )

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=display[0].keys())
    writer.writeheader()
    writer.writerows(display)
    st.download_button("Descargar CSV", out.getvalue(), "ofertas.csv", "text/csv")

    st.divider()
    opciones = {f"{r['puntaje']} · {r['titulo']} — {r['empresa']}": r for r in rows}
    elegido = opciones[st.selectbox("Seleccionar oferta", list(opciones))]

    tab_estado, tab_carta = st.tabs(["Seguimiento", "Carta de presentación"])

    with tab_estado:
        estado = st.selectbox(
            "Estado",
            ["Guardada", "Postulada", "Entrevista", "Rechazada", "Oferta recibida"],
            index=0,
        )
        notas = st.text_area("Notas", value=elegido.get("notas", ""), key=f"notas_{elegido['id']}")
        if st.button("Guardar estado", key=f"estado_{elegido['id']}"):
            guardar_estado(elegido["id"], estado, notas)
            st.success("Estado actualizado.")

    with tab_carta:
        perfil = cargar_perfil()
        coincidencias = coincidencias_cv_oferta(perfil, elegido)
        st.write("**Coincidencias CV ↔ oferta:**", ", ".join(coincidencias) or "No se detectaron coincidencias explícitas")

        descripcion = elegido.get("descripcion", "") or ""
        if descripcion:
            with st.expander("Ver descripción utilizada para generar la carta"):
                st.write(descripcion)
        else:
            st.warning("Esta oferta no tiene una descripción guardada. La personalización será más limitada.")

        modo = st.radio(
            "Modo de generación",
            ["Local (sin API)", "Inteligente (API opcional)"],
            horizontal=True,
            key=f"modo_{elegido['id']}",
        )

        config_entorno = config_api_desde_entorno()
        config_api = None

        if modo.startswith("Inteligente"):
            st.caption(
                "La carta se genera con el texto del CV y la descripción de la oferta. "
                "La API key no se almacena en la base de datos."
            )
            with st.expander("Configuración de API", expanded=config_entorno is None):
                base_default = config_entorno.base_url if config_entorno else os.getenv("LETTER_API_BASE_URL", "")
                model_default = config_entorno.model if config_entorno else os.getenv("LETTER_API_MODEL", "")
                api_default = config_entorno.api_key if config_entorno else ""

                base_url = st.text_input(
                    "URL base",
                    value=base_default,
                    placeholder="https://tu-proveedor.example.com",
                    key=f"api_base_{elegido['id']}",
                )
                model = st.text_input(
                    "Modelo",
                    value=model_default,
                    placeholder="nombre-del-modelo",
                    key=f"api_model_{elegido['id']}",
                )
                api_key = st.text_input(
                    "API key",
                    value=api_default,
                    type="password",
                    key=f"api_key_{elegido['id']}",
                )
                if base_url and model and api_key:
                    config_api = ConfigAPI(base_url=base_url, api_key=api_key, model=model)

        carta_guardada = obtener_carta(elegido["id"])
        state_key = f"carta_{elegido['id']}"
        if state_key not in st.session_state:
            st.session_state[state_key] = carta_guardada["contenido"] if carta_guardada else ""

        generar_label = "Generar borrador local" if modo.startswith("Local") else "Generar carta inteligente"
        if st.button(generar_label, type="primary", key=f"generar_{elegido['id']}_{modo}"):
            try:
                if modo.startswith("Local"):
                    st.session_state[state_key] = generar_borrador_local(elegido, perfil)
                else:
                    if config_api is None:
                        raise ValueError("Completa URL base, modelo y API key antes de generar la carta.")
                    cv_texto = texto_cv()
                    if not cv_texto:
                        raise ValueError("Activa primero un currículum desde la sección Currículum.")
                    with st.spinner("Generando carta personalizada..."):
                        st.session_state[state_key] = generar_carta_inteligente(
                            elegido, perfil, cv_texto, config_api
                        )
                st.success("Carta generada. Puedes editarla antes de guardarla o descargarla.")
            except Exception as exc:
                st.error(f"No se pudo generar la carta: {exc}")

        carta_editada = st.text_area(
            "Carta editable",
            key=state_key,
            height=360,
            placeholder="Genera una carta o escribe tu propio borrador aquí.",
        )

        b1, b2 = st.columns(2)
        if b1.button("Guardar borrador", key=f"guardar_carta_{elegido['id']}", disabled=not carta_editada.strip()):
            modo_db = "inteligente" if modo.startswith("Inteligente") else "local"
            guardar_carta(elegido["id"], carta_editada, modo_db)
            st.success("Borrador guardado en tu cuenta.")

        nombre_seguro = "_".join(
            parte for parte in [elegido.get("empresa", "empresa"), elegido.get("titulo", "cargo")] if parte
        )
        nombre_seguro = "".join(c if c.isalnum() or c in "_- " else "" for c in nombre_seguro).strip().replace(" ", "_")
        b2.download_button(
            "Descargar carta",
            carta_editada,
            file_name=f"carta_{nombre_seguro or 'presentacion'}.txt",
            mime="text/plain",
            disabled=not carta_editada.strip(),
            key=f"descargar_carta_{elegido['id']}",
        )
else:
    st.info("No hay ofertas para los filtros seleccionados.")
