const OWNER = "alainra-cmd";
const REPO = "Triatlon-2027";
const WORKFLOW = "update-race-calendar.yml";
const ALLOWED_ORIGIN = "https://alainra-cmd.github.io";

function cors(origin) {
  const allowed = origin === ALLOWED_ORIGIN ? origin : ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin"
  };
}
function json(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors(origin), "Cache-Control": "no-store" }
  });
}
async function verifyTurnstile(token, ip, secret) {
  const body = new URLSearchParams({ secret, response: token });
  if (ip) body.set("remoteip", ip);
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body
  });
  const result = await response.json();
  return result.success === true;
}
async function github(path, env, options = {}) {
  return fetch("https://api.github.com/repos/" + OWNER + "/" + REPO + path, {
    ...options,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + env.GH_TOKEN,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "Triatlon2027-Manual-Calendar",
      ...(options.headers || {})
    }
  });
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (origin && origin !== ALLOWED_ORIGIN) return json({ error: "Origen no autorizado" }, 403, origin);
    if (!env.GH_TOKEN) return json({ error: "Falta configurar GH_TOKEN en el Worker" }, 503, origin);
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/run") {
      let body;
      try { body = await request.json(); } catch { return json({ error: "Solicitud no válida" }, 400, origin); }
      if (!body.turnstileToken || !env.TURNSTILE_SECRET) return json({ error: "Verificación de seguridad no configurada" }, 400, origin);
      const valid = await verifyTurnstile(body.turnstileToken, request.headers.get("CF-Connecting-IP"), env.TURNSTILE_SECRET);
      if (!valid) return json({ error: "No se pudo verificar la solicitud. Inténtalo de nuevo." }, 403, origin);
      const response = await github("/actions/workflows/" + WORKFLOW + "/dispatches", env, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ref: "main" })
      });
      if (!response.ok) return json({ error: "GitHub no ha aceptado la actualización", detail: await response.text() }, 502, origin);
      return json({ accepted: true, message: "Búsqueda iniciada. El calendario se actualizará al terminar." }, 202, origin);
    }

    if (request.method === "GET" && url.pathname === "/status") {
      const [runsResponse, feedResponse] = await Promise.all([
        github("/actions/workflows/" + WORKFLOW + "/runs?branch=main&per_page=1", env),
        fetch("https://raw.githubusercontent.com/" + OWNER + "/" + REPO + "/main/race-feed.json", { headers: { "Cache-Control": "no-cache" } })
      ]);
      if (!runsResponse.ok) return json({ error: "No se pudo consultar el estado de GitHub" }, 502, origin);
      const runs = await runsResponse.json();
      const run = runs.workflow_runs && runs.workflow_runs[0];
      let feed = null;
      if (feedResponse.ok) {
        try {
          const data = await feedResponse.json();
          feed = { generatedAt: data.generatedAt || null, eventCount: Array.isArray(data.events) ? data.events.length : 0, failedSources: Number(data.failedSources || 0) };
        } catch {}
      }
      return json({ run: run ? { id: run.id, status: run.status, conclusion: run.conclusion, updatedAt: run.updated_at, createdAt: run.created_at, htmlUrl: run.html_url } : null, feed }, 200, origin);
    }
    return json({ error: "Ruta no encontrada" }, 404, origin);
  }
};
