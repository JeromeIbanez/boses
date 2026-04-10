const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Pydantic 422 returns detail as an array; other errors return it as a string. */
function extractDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    // e.g. { loc: ["body", "password"], msg: "String should have at least 8 characters" }
    const first = detail[0];
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : null;
    const msg: string = first?.msg ?? "Validation error";
    return field && field !== "body" ? `${field}: ${msg}` : msg;
  }
  return "Something went wrong. Please try again.";
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
      ...init,
    });
  } catch {
    throw new Error("Unable to connect. Please check your internet connection.");
  }

  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many attempts. Please wait a moment and try again.");
    }
    const body = await res.json().catch(() => ({}));
    throw new Error(extractDetail(body.detail));
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
  is_boses_staff: boolean;
  company: Company;
  created_at: string;
}

export interface AuthResponse {
  user: AuthUser;
}

export interface InviteTokenValidation {
  valid: boolean;
  email: string | null;
}

export const validateInviteToken = (token: string) =>
  authRequest<InviteTokenValidation>(`/auth/invite?token=${encodeURIComponent(token)}`);

export const signup = (body: {
  email: string;
  password: string;
  full_name?: string;
  company_name: string;
  invite_token: string;
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

export const refreshToken = () =>
  authRequest<AuthResponse>("/auth/refresh", { method: "POST" });
