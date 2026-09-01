export async function api<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData) && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`/api/backend${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new Error("No se pudo conectar con el servidor. Render puede estar reiniciándose; intenta nuevamente en unos segundos.");
  }
  const raw = await response.text();
  let data: any = {};
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = {}; }
  if (!response.ok) {
    const detail = data.detail || data.message;
    if (detail) throw new Error(detail);
    if (response.status === 502 || response.status === 503 || response.status === 504) {
      throw new Error(`El servidor no pudo responder (${response.status}). Puede estar reiniciándose o sin recursos.`);
    }
    throw new Error(`La solicitud falló (${response.status})${raw ? `: ${raw.slice(0, 180)}` : "."}`);
  }
  return data as T;
}
