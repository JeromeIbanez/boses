"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { signup, validateInviteToken } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";

type TokenState = "loading" | "valid" | "invalid";

function SignupForm() {
  const { refresh } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [tokenState, setTokenState] = useState<TokenState>("loading");
  const [inviteEmail, setInviteEmail] = useState("");

  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    company_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      setTokenState("invalid");
      return;
    }
    validateInviteToken(token)
      .then((res) => {
        if (res.valid && res.email) {
          setInviteEmail(res.email);
          setForm((f) => ({ ...f, email: res.email! }));
          setTokenState("valid");
        } else {
          setTokenState("invalid");
        }
      })
      .catch(() => setTokenState("invalid"));
  }, [token]);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signup({ ...form, invite_token: token });
      await refresh();
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  if (tokenState === "loading") {
    return (
      <div className="flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-zinc-300 border-t-zinc-700 rounded-full animate-spin" />
      </div>
    );
  }

  if (tokenState === "invalid") {
    return (
      <div className="w-full max-w-sm text-center">
        <h1 className="text-2xl font-semibold text-zinc-900 mb-2">Boses</h1>
        <div className="bg-white border border-zinc-200 rounded-xl p-8 shadow-sm space-y-3">
          <p className="text-sm font-medium text-zinc-800">Boses is invite-only</p>
          <p className="text-sm text-zinc-500">
            Access is by invitation. If you've had a call with us, check your email for your invite link.
          </p>
        </div>
        <p className="text-center text-xs text-zinc-400 mt-4">
          Already have an account?{" "}
          <Link href="/login" className="text-zinc-700 font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-semibold text-zinc-900">Boses</h1>
        <p className="text-sm text-zinc-500 mt-1">Create your account</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-zinc-200 rounded-xl p-6 space-y-4 shadow-sm">
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
        )}

        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1">Company name</label>
          <input
            type="text"
            required
            autoFocus
            value={form.company_name}
            onChange={set("company_name")}
            className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400"
            placeholder="Acme Corp"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1">Your name</label>
          <input
            type="text"
            value={form.full_name}
            onChange={set("full_name")}
            className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400"
            placeholder="Jane Santos"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1">Email</label>
          <input
            type="email"
            required
            value={form.email}
            readOnly={!!inviteEmail}
            onChange={set("email")}
            className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400 read-only:bg-zinc-50 read-only:text-zinc-500"
            placeholder="you@company.com"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1">Password</label>
          <input
            type="password"
            required
            value={form.password}
            onChange={set("password")}
            className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400"
            placeholder="Min. 8 characters"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-zinc-900 text-white text-sm font-medium py-2 rounded-lg hover:bg-zinc-700 transition-colors disabled:opacity-50"
        >
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="text-center text-xs text-zinc-400 mt-4">
        Already have an account?{" "}
        <Link href="/login" className="text-zinc-700 font-medium hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-zinc-300 border-t-zinc-700 rounded-full animate-spin" />
        </div>
      }
    >
      <SignupForm />
    </Suspense>
  );
}
