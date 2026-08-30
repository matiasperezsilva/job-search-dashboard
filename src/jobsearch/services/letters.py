from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib import error, request


@dataclass
class ConfigAPI:
    base_url: str
    api_key: str
    model: str
    timeout: int = 60


def _texto(oferta: dict) -> str:
    return " ".join(
        str(oferta.get(campo, "") or "")
        for campo in ("titulo", "empresa", "descripcion", "modalidad")
    ).lower()


def coincidencias_cv_oferta(perfil: dict, oferta: dict, limite: int = 8) -> list[str]:
    texto = _texto(oferta)
    candidatas: list[str] = []

    resumen = perfil.get("resumen", {})
    candidatas.extend(resumen.get("skills_detectadas", []))

    for cfg in perfil.get("areas", {}).values():
        candidatas.extend(cfg.get("skills", []))

    vistas = set()
    coincidencias = []
    for skill in candidatas:
        normal = str(skill).strip()
        key = normal.lower()
        if not normal or key in vistas:
            continue
        vistas.add(key)
        if key in texto:
            coincidencias.append(normal)
        if len(coincidencias) >= limite:
            break
    return coincidencias


def generar_borrador_local(oferta: dict, perfil: dict) -> str:
    empresa = oferta.get("empresa") or "equipo de selección"
    titulo = oferta.get("titulo") or "la posición publicada"
    area = oferta.get("area") or "el área asociada al cargo"
    coincidencias = coincidencias_cv_oferta(perfil, oferta)

    if coincidencias:
        bloque_coincidencias = ", ".join(coincidencias[:5])
        experiencia = (
            f"Al revisar los requisitos de la vacante, identifico una relación directa con "
            f"conocimientos y herramientas presentes en mi perfil, entre ellas {bloque_coincidencias}."
        )
    else:
        experiencia = (
            "La posición se relaciona con áreas presentes en mi perfil profesional y con mi interés "
            "por continuar desarrollándome en este tipo de desafíos."
        )

    return f"""Estimados/as de {empresa},

Me gustaría postular a la posición de {titulo}. La oportunidad llamó mi atención por su relación con {area} y por los desafíos descritos en la publicación.

{experiencia} Me interesa aportar desde mi experiencia comprobable y seguir profundizando mis conocimientos dentro de las responsabilidades del cargo.

Agradezco su tiempo y quedo disponible para conversar sobre la posición y profundizar en mi experiencia profesional.

Saludos cordiales."""


def _limpiar_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base:
        raise ValueError("Debes indicar la URL base de la API.")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def config_api_desde_entorno() -> ConfigAPI | None:
    base = os.getenv("LETTER_API_BASE_URL", "").strip()
    key = os.getenv("LETTER_API_KEY", "").strip()
    model = os.getenv("LETTER_API_MODEL", "").strip()
    if not (base and key and model):
        return None
    return ConfigAPI(base_url=base, api_key=key, model=model)


def _extraer_contenido_chat(data: dict) -> str:
    try:
        contenido = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("La API respondió con un formato inesperado.") from exc

    if isinstance(contenido, str):
        return contenido.strip()
    if isinstance(contenido, list):
        partes = []
        for item in contenido:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                partes.append(item["text"])
        if partes:
            return "\n".join(partes).strip()
    raise ValueError("La API no devolvió texto para la carta.")


def generar_carta_inteligente(
    oferta: dict,
    perfil: dict,
    cv_texto: str,
    config: ConfigAPI,
) -> str:
    if not cv_texto.strip():
        raise ValueError("No hay texto del currículum activo disponible.")
    if not config.api_key.strip() or not config.model.strip():
        raise ValueError("Falta configurar la API y el modelo.")

    descripcion = str(oferta.get("descripcion", "") or "")[:12000]
    cv = cv_texto[:16000]
    coincidencias = coincidencias_cv_oferta(perfil, oferta)

    system = (
        "Eres un asistente de redacción laboral. Redacta cartas de presentación breves, naturales y profesionales en español. "
        "Regla crítica: usa exclusivamente antecedentes que aparezcan en el currículum entregado. No inventes años de experiencia, "
        "cargos, empresas, estudios, certificaciones, idiomas, logros ni tecnologías. Si un requisito de la oferta no aparece en el CV, "
        "no afirmes que el candidato lo posee. Evita lenguaje exagerado y no menciones que eres una IA. Devuelve solo la carta."
    )
    user = f"""CURRÍCULUM DEL CANDIDATO:\n{cv}\n\nOFERTA:\nCargo: {oferta.get('titulo', '')}\nEmpresa: {oferta.get('empresa', '')}\nModalidad: {oferta.get('modalidad', '')}\nDescripción:\n{descripcion}\n\nCoincidencias detectadas automáticamente: {', '.join(coincidencias) or 'ninguna explícita'}\n\nRedacta una carta de presentación de 180 a 260 palabras. Debe explicar el interés por el cargo y conectar la experiencia real del CV con la oferta sin inventar información."""

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    req = request.Request(
        _limpiar_url(config.base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=config.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"La API devolvió HTTP {exc.code}: {detalle}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"No fue posible conectar con la API: {exc.reason}") from exc

    return _extraer_contenido_chat(data)


# Compatibilidad con el nombre usado en versiones anteriores.
def generar_borrador(oferta: dict, evaluacion: dict | None = None) -> str:
    perfil_minimo = {"resumen": {"skills_detectadas": (evaluacion or {}).get("coincidencias", [])}}
    return generar_borrador_local(oferta, perfil_minimo)
