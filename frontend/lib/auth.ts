const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  company: Company;
  created_at: string;
}

export interface AuthResponse {
  user: AuthUser;
}

export const signup = (body: {
  email: string;
  password: string;
  full_name?: string;
  company_name: string;
}) => authRequest<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify(body) });

export const login = (body: { email: string; password: string }) =>
  authRequest<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) });

export const logout = () =>
  authRequest<void>("/auth/logout", { method: "POST" });

export const getMe = () =>
  authRequest<AuthResponse>("/auth/me");

export const forgotPassword = (email: string) =>
  authRequest<void>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });

export const resetPassword = (token: string, new_password: string) =>
  authRequest<void>("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, new_password }) });
