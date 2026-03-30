"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "@/lib/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email);
    } finally {
      setSent(true);
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-semibold text-zinc-900">Boses</h1>
        <p className="text-sm text-zinc-500 mt-1">Reset your password</p>
      </div>

      <div className="bg-white border border-zinc-200 rounded-xl p-6 shadow-sm">
        {sent ? (
          <div className="text-center space-y-2">
            <p className="text-sm text-zinc-700 font-medium">Check your email</p>
            <p className="text-xs text-zinc-400">If that address is registered, you'll receive a reset link shortly.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">Email address</label>
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400"
                placeholder="you@company.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-zinc-900 text-white text-sm font-medium py-2 rounded-lg hover:bg-zinc-700 transition-colors disabled:opacity-50"
            >
              {loading ? "Sending…" : "Send reset link"}
            </button>
          </form>
        )}
      </div>

      <p className="text-center text-xs text-zinc-400 mt-4">
        <Link href="/login" className="text-zinc-700 font-medium hover:underline">Back to sign in</Link>
      </p>
    </div>
  );
}
