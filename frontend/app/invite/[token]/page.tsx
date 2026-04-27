"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { validateCompanyInvite, acceptCompanyInvite } from "@/lib/auth";
import type { CompanyInviteValidation } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";
import Spinner from "@/components/ui/Spinner";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

type PageState = "loading" | "valid" | "invalid" | "success";

export default function AcceptInvitePage() {
  const { token } = useParams<{ token: string }>();
  const { refresh } = useAuth();
  const router = useRouter();

  const [pageState, setPageState] = useState<PageState>("loading");
  const [invite, setInvite] = useState<CompanyInviteValidation | null>(null);
  const [form, setForm] = useState({ full_name: "", password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) { setPageState("invalid"); return; }
    validateCompanyInvite(token)
      .then((res) => {
        if (res.valid) { setInvite(res); setPageState("valid"); }
        else setPageState("invalid");
      })
      .catch(() => setPageState("invalid"));
  }, [token]);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    try {
      await acceptCompanyInvite(token, {
        full_name: form.full_name.trim() || undefined,
        password: form.password,
      });
      await refresh();
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Loading ──────────────────────────────────────────────────────────────

  if (pageState === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <Spinner className="h-6 w-6 text-zinc-400" />
      </div>
    );
  }

  // ── Invalid / expired ────────────────────────────────────────────────────

  if (pageState === "invalid") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <p className="text-sm font-semibold text-zinc-900">Invite not found</p>
          <p className="text-sm text-zinc-500">
            This invite link is invalid or has expired. Ask your team admin to send a new one.
          </p>
        </div>
      </div>
    );
  }

  // ── Form ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-widest mb-3">Boses</p>
          <h1 className="text-2xl font-semibold text-zinc-900">
            Join {invite?.company_name ?? "the workspace"}
          </h1>
          {invite?.inviter_name && (
            <p className="text-sm text-zinc-500 mt-2">
              {invite.inviter_name} has invited you to collaborate on Boses.
            </p>
          )}
        </div>

        <div className="bg-white border border-zinc-200 rounded-xl p-6 shadow-sm">
          {/* Pre-filled email (read-only) */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-zinc-700 mb-1.5">Email</label>
            <div className="px-3 py-2 text-sm text-zinc-500 bg-zinc-50 border border-zinc-200 rounded-lg">
              {invite?.email}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                Full name <span className="text-zinc-400 font-normal">(optional)</span>
              </label>
              <Input
                placeholder="Jane Smith"
                value={form.full_name}
                onChange={set("full_name")}
                autoComplete="name"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">Password</label>
              <Input
                type="password"
                placeholder="At least 8 characters"
                value={form.password}
                onChange={set("password")}
                autoComplete="new-password"
                required
                minLength={8}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">Confirm password</label>
              <Input
                type="password"
                placeholder="Repeat your password"
                value={form.confirm_password}
                onChange={set("confirm_password")}
                autoComplete="new-password"
                required
              />
            </div>

            {error && (
              <p className="text-xs text-red-600">{error}</p>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={submitting || !form.password}
            >
              {submitting ? <Spinner /> : "Create account & join workspace"}
            </Button>
          </form>
        </div>

        <p className="text-center text-xs text-zinc-400 mt-4">
          Already have an account?{" "}
          <a href="/login" className="text-zinc-600 hover:underline">Sign in</a>
        </p>
      </div>
    </div>
  );
}
