// Minimal API client for auth endpoints
// DRY helpers and narrow surface aligned with current needs

const API_BASE = "http://localhost:8000";

export type RegisterPayload = {
  username: string;
  password: string;
  full_name?: string | null;
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
};

export type UserMe = {
  username: string;
  full_name?: string | null;
  role: string;
};

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


