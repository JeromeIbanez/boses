"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle, Copy, Check, Trash2, Plus, Key, Users, Mail, X, Lock, Bell, ArrowRight } from "lucide-react";
import { getCompanySettings, updateCompanySettings, updateNotificationPrefs, listApiKeys, createApiKey, revokeApiKey, getTeam, inviteMember, cancelInvite, removeMember, changePassword, deleteAccount } from "@/lib/api";
import type { APIKey, TeamMember, PendingInvite } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Team sub-component
// ---------------------------------------------------------------------------

function TeamSection({ currentUserRole }: { currentUserRole: string }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [showForm, setShowForm] = useState(false);
  const isOwner = currentUserRole === "owner" || currentUserRole === "admin";

  const { data, isLoading } = useQuery({
    queryKey: ["team"],
    queryFn: getTeam,
  });

  const inviteMutation = useMutation({
    mutationFn: (email: string) => inviteMember(email),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team"] });
      setEmail("");
      setShowForm(false);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelInvite(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team"] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => removeMember(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team"] }),
  });

  const roleLabel = (role: string) =>
    ({ owner: "Owner", admin: "Admin", member: "Member" }[role] ?? role);

  return (
    <section className="bg-white border border-zinc-200 rounded-xl p-6">
      <div className="flex items-start gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg border border-zinc-200 bg-zinc-50 flex items-center justify-center shrink-0">
          <Users size={15} className="text-zinc-500" />
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-zinc-900">Team</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Manage who has access to your workspace.
          </p>
        </div>
        {isOwner && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-1.5 text-xs font-medium text-zinc-700 border border-zinc-200 rounded-lg px-2.5 py-1.5 hover:bg-zinc-50 transition-colors"
          >
            <Plus size={12} /> Invite
          </button>
        )}
      </div>

      {/* Invite form */}
      {showForm && (
        <div className="mb-4 p-4 bg-zinc-50 rounded-lg border border-zinc-200 space-y-3">
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">Email address</label>
          <Input
            type="email"
            placeholder="colleague@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && email.trim()) inviteMutation.mutate(email.trim());
            }}
          />
          {inviteMutation.error && (
            <p className="text-xs text-red-600">
              {(inviteMutation.error as Error).message}
              {(inviteMutation.error as Error).message.includes("Upgrade") && (
                <Link href="/settings/billing" className="ml-1 underline font-medium">
                  Manage billing →
                </Link>
              )}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={() => email.trim() && inviteMutation.mutate(email.trim())}
              disabled={!email.trim() || inviteMutation.isPending}
            >
              {inviteMutation.isPending ? <Spinner /> : "Send invite"}
            </Button>
            <Button variant="secondary" onClick={() => { setShowForm(false); setEmail(""); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-zinc-400 py-2"><Spinner className="h-3 w-3" /> Loading…</div>
      ) : (
        <div className="space-y-1">
          {/* Active members */}
          {(data?.members ?? []).map((m: TeamMember) => (
            <div key={m.id} className="flex items-center gap-3 py-2 border-b border-zinc-100 last:border-0">
              <div className="w-7 h-7 rounded-full bg-zinc-100 flex items-center justify-center shrink-0">
                <span className="text-xs font-medium text-zinc-500">
                  {(m.full_name ?? m.email)[0].toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-800 truncate">{m.full_name ?? m.email}</p>
                {m.full_name && <p className="text-xs text-zinc-400 truncate">{m.email}</p>}
              </div>
              <span className="text-xs text-zinc-400 shrink-0">{roleLabel(m.role)}</span>
              {isOwner && m.role !== "owner" && (
                <button
                  onClick={() => removeMutation.mutate(m.id)}
                  disabled={removeMutation.isPending}
                  className="p-1.5 text-zinc-300 hover:text-red-500 transition-colors"
                  title="Remove member"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          ))}

          {/* Pending invites */}
          {(data?.pending_invites ?? []).map((inv: PendingInvite) => (
            <div key={inv.id} className="flex items-center gap-3 py-2 border-b border-zinc-100 last:border-0">
              <div className="w-7 h-7 rounded-full bg-zinc-50 border border-dashed border-zinc-200 flex items-center justify-center shrink-0">
                <Mail size={11} className="text-zinc-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-600 truncate">{inv.email}</p>
                <p className="text-xs text-zinc-400">Invite pending</p>
              </div>
              <span className="text-xs text-zinc-400 shrink-0">{roleLabel(inv.role)}</span>
              {isOwner && (
                <button
                  onClick={() => cancelMutation.mutate(inv.id)}
                  disabled={cancelMutation.isPending}
                  className="p-1.5 text-zinc-300 hover:text-red-500 transition-colors"
                  title="Cancel invite"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Change password sub-component
// ---------------------------------------------------------------------------

function ChangePasswordSection() {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () => changePassword(form.current, form.next),
    onSuccess: () => {
      setForm({ current: "", next: "", confirm: "" });
      setError("");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.next !== form.confirm) { setError("New passwords don't match."); return; }
    mutate();
  };

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [field]: e.target.value });
    setSaved(false);
  };

  return (
    <section className="bg-white border border-zinc-200 rounded-xl p-6">
      <div className="flex items-start gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg border border-zinc-200 bg-zinc-50 flex items-center justify-center shrink-0">
          <Lock size={15} className="text-zinc-500" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-zinc-900">Password</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Change your login password.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 max-w-sm">
        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">Current password</label>
          <Input type="password" value={form.current} onChange={set("current")} autoComplete="current-password" required />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">New password</label>
          <Input type="password" value={form.next} onChange={set("next")} autoComplete="new-password" required minLength={8} placeholder="At least 8 characters" />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">Confirm new password</label>
          <Input type="password" value={form.confirm} onChange={set("confirm")} autoComplete="new-password" required />
        </div>

        {error && (
          <div className="flex items-center gap-2 text-xs text-red-600">
            <AlertCircle size={13} /> {error}
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <Button type="submit" variant="primary" disabled={isPending || !form.current || !form.next || !form.confirm}>
            {isPending ? <Spinner /> : "Update password"}
          </Button>
          {saved && (
            <span className="flex items-center gap-1.5 text-xs text-green-600">
              <CheckCircle2 size={13} /> Password updated
            </span>
          )}
        </div>
      </form>
    </section>
  );
}

// ---------------------------------------------------------------------------
// API Keys sub-component
// ---------------------------------------------------------------------------

function APIKeysSection() {
  const queryClient = useQueryClient();
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyExpiry, setNewKeyExpiry] = useState("");  // ISO date string or ""
  const [showForm, setShowForm] = useState(false);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: listApiKeys,
  });

  const createMutation = useMutation({
    mutationFn: ({ name, expires_at }: { name: string; expires_at?: string | null }) =>
      createApiKey(name, expires_at),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setRevealedKey(data.key);
      setNewKeyName("");
      setNewKeyExpiry("");
      setShowForm(false);
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => revokeApiKey(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const copyKey = async (key: string) => {
    await navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="bg-white border border-zinc-200 rounded-xl p-6">
      <div className="flex items-start gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg border border-zinc-200 bg-zinc-50 flex items-center justify-center shrink-0">
          <Key size={15} className="text-zinc-500" />
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-zinc-900">API Keys</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Use API keys to access Boses from the MCP server or programmatic tools. Each key is scoped to your workspace.
          </p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className="flex items-center gap-1.5 text-xs font-medium text-zinc-700 border border-zinc-200 rounded-lg px-2.5 py-1.5 hover:bg-zinc-50 transition-colors"
        >
          <Plus size={12} /> New key
        </button>
      </div>

      {/* New key form */}
      {showForm && (
        <div className="mb-4 p-4 bg-zinc-50 rounded-lg border border-zinc-200 space-y-3">
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1.5">Key name</label>
            <Input
              placeholder='e.g. "Claude Desktop" or "MCP Server"'
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newKeyName.trim())
                  createMutation.mutate({ name: newKeyName.trim(), expires_at: newKeyExpiry || null });
              }}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1.5">
              Expiry date <span className="text-zinc-400 font-normal">(optional — leave blank for no expiry)</span>
            </label>
            <Input
              type="date"
              value={newKeyExpiry}
              onChange={(e) => setNewKeyExpiry(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={() =>
                newKeyName.trim() &&
                createMutation.mutate({ name: newKeyName.trim(), expires_at: newKeyExpiry || null })
              }
              disabled={!newKeyName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? <Spinner /> : "Generate key"}
            </Button>
            <Button variant="secondary" onClick={() => { setShowForm(false); setNewKeyName(""); setNewKeyExpiry(""); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Revealed key — show once */}
      {revealedKey && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg space-y-2">
          <div className="flex items-center gap-2">
            <AlertCircle size={13} className="text-amber-600 shrink-0" />
            <p className="text-xs font-medium text-amber-700">Store this key now — it won't be shown again.</p>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs font-mono bg-white border border-amber-200 rounded px-3 py-2 text-zinc-800 break-all">
              {revealedKey}
            </code>
            <button
              onClick={() => copyKey(revealedKey)}
              className="shrink-0 p-2 rounded-lg border border-amber-200 bg-white hover:bg-amber-50 transition-colors"
              title="Copy key"
            >
              {copied ? <Check size={13} className="text-green-600" /> : <Copy size={13} className="text-zinc-500" />}
            </button>
          </div>
          <button
            onClick={() => setRevealedKey(null)}
            className="text-xs text-amber-600 hover:text-amber-800 transition-colors"
          >
            I've saved it — dismiss
          </button>
        </div>
      )}

      {/* Keys list */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-xs text-zinc-400 py-2">
          <Spinner className="h-3 w-3" /> Loading…
        </div>
      ) : keys.length === 0 ? (
        <p className="text-xs text-zinc-400 py-2">No API keys yet.</p>
      ) : (
        <div className="space-y-2">
          {keys.map((key: APIKey) => {
            const isExpired = key.expires_at ? new Date(key.expires_at) <= new Date() : false;
            const expiringSoon = key.expires_at && !isExpired
              ? (new Date(key.expires_at).getTime() - Date.now()) < 7 * 24 * 60 * 60 * 1000
              : false;
            return (
            <div key={key.id} className="flex items-center gap-3 py-2 border-b border-zinc-100 last:border-0">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-zinc-800 truncate">{key.name}</p>
                  {isExpired && (
                    <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded bg-red-100 text-red-600">Expired</span>
                  )}
                  {expiringSoon && (
                    <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-600">Expiring soon</span>
                  )}
                </div>
                <p className="text-xs text-zinc-400 font-mono">{key.key_prefix}…</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-zinc-400">
                  {key.last_used_at ? `Last used ${formatDate(key.last_used_at)}` : "Never used"}
                </p>
                {key.expires_at ? (
                  <p className={`text-xs ${isExpired ? "text-red-400" : "text-zinc-300"}`}>
                    {isExpired ? "Expired" : "Expires"} {formatDate(key.expires_at)}
                  </p>
                ) : (
                  <p className="text-xs text-zinc-300">Created {formatDate(key.created_at)}</p>
                )}
              </div>
              <button
                onClick={() => revokeMutation.mutate(key.id)}
                disabled={revokeMutation.isPending}
                className="p-1.5 text-zinc-400 hover:text-red-500 transition-colors disabled:opacity-50"
                title="Revoke key"
              >
                <Trash2 size={13} />
              </button>
            </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-zinc-400 mt-4">
        Configure your MCP server at{" "}
        <code className="font-mono text-zinc-500">{"http://localhost:8001/sse"}</code>{" "}
        with the key above as the{" "}
        <code className="font-mono text-zinc-500">X-API-Key</code> header.
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Danger zone sub-component
// ---------------------------------------------------------------------------

function DangerZone() {
  const { logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () => deleteAccount(password),
    onSuccess: async () => {
      await logout();
      router.push("/login");
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    mutate();
  };

  return (
    <section className="bg-white border border-red-100 rounded-xl p-6">
      <h2 className="text-sm font-semibold text-red-600 mb-1">Danger zone</h2>
      <p className="text-xs text-zinc-500 mb-4">
        Permanently delete your account. This cannot be undone.
      </p>

      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="text-xs font-medium text-red-600 border border-red-200 rounded-lg px-3 py-1.5 hover:bg-red-50 transition-colors"
        >
          Delete my account
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3 max-w-sm">
          <p className="text-xs text-zinc-600">
            Enter your password to confirm. If you are the workspace owner, remove all other members first.
          </p>
          <Input
            type="password"
            placeholder="Your password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(""); }}
            autoComplete="current-password"
            required
          />
          {error && (
            <div className="flex items-center gap-2 text-xs text-red-600">
              <AlertCircle size={13} /> {error}
            </div>
          )}
          <div className="flex items-center gap-2">
            <Button
              type="submit"
              variant="primary"
              disabled={isPending || !password}
              className="!bg-red-600 hover:!bg-red-700"
            >
              {isPending ? <Spinner /> : "Permanently delete account"}
            </Button>
            <Button variant="secondary" type="button" onClick={() => { setOpen(false); setPassword(""); setError(""); }}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Workspace (name editable by owner/admin) sub-component
// ---------------------------------------------------------------------------

function WorkspaceSection({ currentUserRole }: { currentUserRole: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [saved, setSaved] = useState(false);
  const isOwner = currentUserRole === "owner" || currentUserRole === "admin";

  const { data: company, isLoading } = useQuery({
    queryKey: ["company-settings"],
    queryFn: getCompanySettings,
  });

  useEffect(() => {
    if (company) setName(company.name ?? "");
  }, [company]);

  const { mutate: save, isPending: isSaving, error } = useMutation({
    mutationFn: () => updateCompanySettings({ name: name.trim() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  if (isLoading) return null;

  return (
    <section className="bg-white border border-zinc-200 rounded-xl p-6">
      <h2 className="text-sm font-semibold text-zinc-900 mb-4">Workspace</h2>
      <div className="space-y-4 max-w-sm">
        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">Company name</label>
          {isOwner ? (
            <Input
              value={name}
              onChange={(e) => { setName(e.target.value); setSaved(false); }}
              placeholder="Your company name"
              maxLength={255}
            />
          ) : (
            <p className="text-sm text-zinc-800 font-medium">{company?.name}</p>
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">Slug</label>
          <p className="text-sm text-zinc-500 font-mono">{company?.slug}</p>
        </div>

        {isOwner && (
          <>
            {error && (
              <div className="flex items-center gap-2 text-xs text-red-600">
                <AlertCircle size={13} /> {(error as Error).message}
              </div>
            )}
            <div className="flex items-center gap-3">
              <Button
                variant="primary"
                onClick={() => name.trim() && save()}
                disabled={isSaving || !name.trim() || name.trim() === company?.name}
              >
                {isSaving ? <Spinner /> : "Save"}
              </Button>
              {saved && (
                <span className="flex items-center gap-1.5 text-xs text-green-600">
                  <CheckCircle2 size={13} /> Saved
                </span>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Notifications sub-component
// ---------------------------------------------------------------------------

function NotificationsSection() {
  const { user } = useAuth();
  const [enabled, setEnabled] = useState(true);
  const [saved, setSaved] = useState(false);

  // Initialise from user object when available
  useEffect(() => {
    if (user) setEnabled(user.email_notifications ?? true);
  }, [user]);

  const { mutate, isPending } = useMutation({
    mutationFn: (val: boolean) => updateNotificationPrefs(val),
    onSuccess: (_, val) => {
      setEnabled(val);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const toggle = () => {
    const next = !enabled;
    mutate(next);
  };

  return (
    <section className="bg-white border border-zinc-200 rounded-xl p-6">
      <div className="flex items-start gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg border border-zinc-200 bg-zinc-50 flex items-center justify-center shrink-0">
          <Bell size={15} className="text-zinc-500" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-zinc-900">Notifications</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Control how Boses contacts you.</p>
        </div>
      </div>

      <div className="flex items-center justify-between max-w-sm">
        <div>
          <p className="text-sm font-medium text-zinc-800">Simulation completion emails</p>
          <p className="text-xs text-zinc-400 mt-0.5">Receive an email when a simulation finishes or fails.</p>
        </div>
        <button
          onClick={toggle}
          disabled={isPending}
          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none ${
            enabled ? "bg-zinc-800" : "bg-zinc-200"
          } disabled:opacity-50`}
          aria-checked={enabled}
          role="switch"
        >
          <span
            className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
              enabled ? "translate-x-4" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {saved && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-green-600">
          <CheckCircle2 size={13} /> Saved
        </p>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main settings page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="px-8 py-8 max-w-2xl">
      <PageHeader title="Settings" description="Manage your workspace configuration." />

      <div className="mt-8 space-y-8">
        {/* Workspace */}
        <WorkspaceSection currentUserRole={user?.role ?? "member"} />

        {/* Team */}
        <TeamSection currentUserRole={user?.role ?? "member"} />

        {/* Notifications */}
        <NotificationsSection />

        {/* Change password */}
        <ChangePasswordSection />

        {/* API Keys */}
        <APIKeysSection />

        {/* Billing link */}
        <section className="bg-white border border-zinc-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-zinc-900 mb-1">Billing</h2>
          <p className="text-xs text-zinc-500 mb-4">Manage your plan, usage, and payment details.</p>
          <Link
            href="/settings/billing"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-violet-600 hover:text-violet-700 transition-colors"
          >
            Manage billing <ArrowRight size={12} />
          </Link>
        </section>

        {/* Integrations link */}
        <section className="bg-white border border-zinc-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-zinc-900 mb-1">Integrations</h2>
          <p className="text-xs text-zinc-500 mb-4">Connect Boses to Slack and other tools.</p>
          <Link
            href="/integrations"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-violet-600 hover:text-violet-700 transition-colors"
          >
            Manage integrations <ArrowRight size={12} />
          </Link>
        </section>

        {/* Danger zone */}
        <DangerZone />
      </div>
    </div>
  );
}
