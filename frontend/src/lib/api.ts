import { type RegisterPayload, type LoginPayload, type AuthTokenResponse, type UserMe, type AnalyzeResponse, type JobMeta, type Analysis, type DocumentsList } from "./types";

const API_BASE = "http://localhost:8000";

function buildHeaders(token?: string): HeadersInit {
  const headers: HeadersInit = { "content-type": "application/json" };
  if (token) headers["authorization"] = `Bearer ${token}`;
  return headers;
}

async function handle<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

export async function apiRegister(payload: RegisterPayload): Promise<{ username: string; full_name?: string | null; role: string }>
{
  const res = await fetch(`${API_BASE}/v1/auth/register`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });
  return handle(res);
}

export async function apiLogin(payload: LoginPayload): Promise<AuthTokenResponse> {
  const form = new URLSearchParams();
  form.set("username", payload.username);
  form.set("password", payload.password);
  // FastAPI OAuth2PasswordRequestForm expects application/x-www-form-urlencoded
  const res = await fetch(`${API_BASE}/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  return handle(res);
}

export async function apiMe(token: string): Promise<UserMe> {
  const res = await fetch(`${API_BASE}/v1/auth/me`, {
    method: "GET",
    headers: buildHeaders(token),
  });
  return handle(res);
}

// ---- Documents API ----
export async function apiAnalyzeDocument(params: { file: File; query?: string; token: string }): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", params.file);
  if (params.query) form.append("query", params.query);
  const res = await fetch(`${API_BASE}/v1/documents/analyze`, {
    method: "POST",
    headers: { authorization: `Bearer ${params.token}` },
    body: form,
  });
  return handle(res);
}

export async function apiListDocuments(params: { token: string; skip?: number; limit?: number }): Promise<DocumentsList> {
  const { token, skip, limit } = params;
  const url = new URL(`${API_BASE}/v1/documents`);
  if (typeof skip === "number" && skip > 0) url.searchParams.set("skip", String(skip));
  if (typeof limit === "number" && limit > 0) url.searchParams.set("limit", String(limit));
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(token),
  });
  return handle(res);
}

export async function apiGetJob(jobId: string, token: string): Promise<JobMeta> {
  const res = await fetch(`${API_BASE}/v1/documents/jobs/${jobId}`, {
    method: "GET",
    headers: buildHeaders(token),
  });
  return handle(res);
}

export async function apiDeleteDocument(documentId: string, token: string): Promise<{ status: string; documentId: string }> {
  const res = await fetch(`${API_BASE}/v1/documents/${documentId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return handle(res);
}

// ---- Analyses API ----
export async function apiGetAnalysis(analysisId: string, token: string): Promise<Analysis> {
  const res = await fetch(`${API_BASE}/v1/analyses/${analysisId}`, {
    method: "GET",
    headers: buildHeaders(token),
  });
  return handle(res);
}


