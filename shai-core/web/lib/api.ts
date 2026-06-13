// Tiny typed client for the SHAI Core API.
// When Clerk is loaded client-side, attach its session token as a bearer so the
// API's tenant seam can resolve the real user; otherwise send no auth header
// (the API falls back to the dev identity).
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function authHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const clerk = (window as unknown as { Clerk?: { session?: { getToken(): Promise<string | null> } } }).Clerk;
  try {
    const token = clerk?.session ? await clerk.session.getToken() : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", headers: await authHeaders() });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}
