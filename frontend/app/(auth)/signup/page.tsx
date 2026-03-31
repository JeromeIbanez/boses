"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signup } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";

export default function SignupPage() {
  const { refresh } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    company_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await signup(form);
      await refresh();
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  };

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
            onChange={set("email")}
            className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400"
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
