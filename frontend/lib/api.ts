export const API_BASE = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "/api/v1" : "http://localhost:8000/api/v1");
export const API_ORIGIN = process.env.NEXT_PUBLIC_API_ORIGIN || API_BASE.replace(/\/api\/v1\/?$/, "");
export function getToken() { if (typeof window === "undefined") return null; return localStorage.getItem("smartfind_token"); }
export function setSession(token: string, user: unknown) { localStorage.setItem("smartfind_token", token); localStorage.setItem("smartfind_user", JSON.stringify(user)); }
export function clearSession() { localStorage.removeItem("smartfind_token"); localStorage.removeItem("smartfind_user"); }
export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getToken(); if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? body.detail.map((e: {msg: string}) => e.msg).join("; ") : body.message || `Request failed (${response.status})`);
  return body as T;
}
