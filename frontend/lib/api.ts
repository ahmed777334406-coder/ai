export const API_BASE = process.env.NODE_ENV === "production" ? "/api/v1" : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1");
export const API_ORIGIN = (process.env.NODE_ENV === "production" ? "" : process.env.NEXT_PUBLIC_API_ORIGIN) || API_BASE.replace(/\/api\/v1\/?$/, "");
export function getToken() { if (typeof window === "undefined") return null; return sessionStorage.getItem("smartfind_token"); }
export function setSession(token: string, user: unknown) { localStorage.removeItem("smartfind_token"); localStorage.removeItem("smartfind_user"); sessionStorage.setItem("smartfind_token", token); sessionStorage.setItem("smartfind_user", JSON.stringify(user)); }
export function clearSession() { localStorage.removeItem("smartfind_token"); localStorage.removeItem("smartfind_user"); sessionStorage.removeItem("smartfind_token"); sessionStorage.removeItem("smartfind_user"); visitorSession = null; }
let visitorSession: Promise<unknown> | null = null;
async function ensureVisitor() {
  if (!visitorSession) visitorSession = fetch(`${API_BASE}/auth/session`, {
    method: "POST", credentials: "include", headers: {"X-SmartFind-Request": "1"}
  }).then(async response => {
  if (!response.ok) throw new Error("Could not start visitor session");
    return response.json();
  }).catch(error => { visitorSession = null; throw error; });
  return visitorSession;
}
export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  if (!getToken() && path !== "/auth/session") await ensureVisitor();
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  headers.set("X-SmartFind-Request", "1");
  const token = getToken(); if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, credentials: "include", headers, cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== "/auth/login") {
    visitorSession = null;
    if (token) clearSession();
    throw new Error("Session expired. Reload to start a new visitor session. Previous private history cannot be recovered without the original session. / 会话已过期，请刷新页面。新会话无法访问原会话的私人记录。");
  }
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? body.detail.map((e: {msg: string}) => e.msg).join("; ") : body.message || `Request failed (${response.status})`);
  return body as T;
}
