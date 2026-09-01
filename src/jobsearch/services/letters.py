from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib import error, parse, request


@dataclass
class ConfigAPI:
    base_url: str
    api_key: str
    model: str
    timeout: int = 60


@dataclass
class ConfigGemini:
    api_key: str
    model: str = "gemini-3.5-flash-lite"
    timeout: int = 60


def config_gemini_desde_entorno() -> ConfigGemini | None:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    return ConfigGemini(api_key=key, model=model)


def _sanitizar_cv_para_ia(texto: str) -> str:
    """Reduce datos de contacto antes de enviar el CV a un proveedor externo."""
    limpio = texto
    limpio = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", limpio)
    limpio = re.sub(r"https?://\S+|www\.\S+", "[enlace omitido]", limpio, flags=re.I)
    # Teléfonos con código de país o secuencias largas de dígitos, preservando años cortos.
    limpio = re.sub(r"(?<!\d)(?:\+?\d[\s().-]?){8,15}(?!\d)", "[teléfono omitido]", limpio)
    return limpio


def _extraer_contenido_gemini(data: dict) -> str:
    try:
        partes = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Gemini respondió con un formato inesperado.") from exc
    textos = [p.get("text", "") for p in partes if isinstance(p, dict) and isinstance(p.get("text"), str)]
    texto = "\n".join(t.strip() for t in textos if t.strip()).strip()
    if not texto:
        raise ValueError("Gemini no devolvió texto para la carta.")
    return texto


def generar_carta_gemini(
    oferta: dict,
    perfil: dict,
    cv_texto: str,
    config: ConfigGemini,
) -> str:
    if not cv_texto.strip():
        raise ValueError("No hay texto del currículum activo disponible.")
    if not config.api_key.strip():
        raise ValueError("Falta configurar GEMINI_API_KEY.")

    descripcion = str(oferta.get("descripcion", "") or "")[:12000]
    cv = _sanitizar_cv_para_ia(cv_texto)[:16000]
    coincidencias = coincidencias_cv_oferta(perfil, oferta)

    system = (
        "Eres un asistente de redacción laboral. Redacta cartas de presentación breves, naturales y profesionales en español. "
        "Usa exclusivamente antecedentes presentes en el currículum entregado. No inventes años de experiencia, cargos, empresas, "
        "estudios, certificaciones, idiomas, logros ni tecnologías. Si un requisito de la oferta no aparece en el CV, no afirmes que "
        "el candidato lo posee. Evita lenguaje exagerado, frases vacías y referencias a inteligencia artificial. Devuelve solo la carta."
    )
    user = f"""CURRÍCULUM DEL CANDIDATO (datos de contacto omitidos):
{cv}

OFERTA:
Cargo: {oferta.get('titulo', '')}
Empresa: {oferta.get('empresa', '')}
Modalidad: {oferta.get('modalidad', '')}
Descripción:
{descripcion}

Coincidencias detectadas automáticamente: {', '.join(coincidencias) or 'ninguna explícita'}

Redacta una carta de presentación de 180 a 260 palabras. Debe explicar el interés por el cargo y conectar la experiencia real del CV con la oferta sin inventar información. Evita repetir literalmente el CV."""

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{parse.quote(config.model, safe='-_.')}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 700},
    }
    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": config.api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=config.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace")[:700]
        if exc.code == 429:
            raise RuntimeError("Gemini alcanzó temporalmente su límite de uso. Intenta nuevamente en unos minutos.") from exc
        if exc.code in {401, 403}:
            raise RuntimeError("La API key de Gemini no es válida o no tiene acceso al modelo configurado.") from exc
        raise RuntimeError(f"Gemini devolvió HTTP {exc.code}: {detalle}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"No fue posible conectar con Gemini: {exc.reason}") from exc

    return _extraer_contenido_gemini(data)


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
