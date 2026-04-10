"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, X } from "lucide-react";
import { getAdminInvites, createAdminInvite, revokeAdminInvite, type Invite } from "@/lib/api";

function StatusBadge({ status }: { status: Invite["status"] }) {
  const styles = {
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    used: "bg-green-50 text-green-700 border-green-200",
    expired: "bg-zinc-100 text-zinc-400 border-zinc-200",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${styles[status]}`}>
      {status}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="text-zinc-400 hover:text-zinc-700 transition-colors"
      title="Copy invite link"
    >
      {copied ? <Check size={13} className="text-green-600" /> : <Copy size={13} />}
    </button>
  );
}


export default function AdminInvitesPage() {
  const [email, setEmail] = useState("");
  const [sendError, setSendError] = useState("");
  const [sendSuccess, setSendSuccess] = useState("");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-invites"],
    queryFn: getAdminInvites,
  });

  const sendMut = useMutation({
    mutationFn: () => createAdminInvite(email.trim()),
    onSuccess: (invite) => {
      qc.invalidateQueries({ queryKey: ["admin-invites"] });
      setSendSuccess(`Invite sent to ${invite.email}`);
      setSendError("");
      setEmail("");
      setTimeout(() => setSendSuccess(""), 4000);
    },
    onError: (err: Error) => {
      setSendError(err.message);
      setSendSuccess("");
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    setSendError("");
    setSendSuccess("");
    if (!email.trim()) return;
    sendMut.mutate();
  };

  const items = data?.items ?? [];
  const pending = items.filter((i) => i.status === "pending").length;
  const used = items.filter((i) => i.status === "used").length;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-900">Invites</h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          {data?.total ?? 0} total · {pending} pending · {used} used
        </p>
      </div>

      {/* Send invite */}
      <div className="bg-white border border-zinc-200 rounded-xl p-5 mb-8">
        <h2 className="text-sm font-medium text-zinc-800 mb-3">Send an invite</h2>
        <form onSubmit={handleSend} className="flex items-center gap-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@company.com"
            className="flex-1 text-sm border border-zinc-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-400"
          />
          <button
            type="submit"
            disabled={sendMut.isPending || !email.trim()}
            className="px-4 py-2 bg-zinc-900 text-white text-sm rounded-lg hover:bg-zinc-700 transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            {sendMut.isPending ? "Sending…" : "Send invite"}
          </button>
        </form>
        {sendError && (
          <p className="mt-2 text-xs text-red-600">{sendError}</p>
        )}
        {sendSuccess && (
          <p className="mt-2 text-xs text-green-600">{sendSuccess}</p>
        )}
      </div>

      {/* Invite list */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-5 h-5 border-2 border-zinc-300 border-t-zinc-700 rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <p className="text-center text-sm text-zinc-400 py-16">No invites yet.</p>
      ) : (
        <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-100 bg-zinc-50">
                <th className="text-left py-2.5 px-4 text-xs font-medium text-zinc-500">Email</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-zinc-500">Status</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-zinc-500">Sent</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-zinc-500">Expires</th>
                <th className="py-2.5 px-4" />
              </tr>
            </thead>
            <tbody className="px-4">
              {items.map((invite) => (
                <tr key={invite.id} className="border-b border-zinc-100 last:border-0">
                  <td className="py-3 px-4 text-sm text-zinc-800">{invite.email}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={invite.status} />
                  </td>
                  <td className="py-3 px-4 text-xs text-zinc-500">
                    {new Date(invite.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </td>
                  <td className="py-3 px-4 text-xs text-zinc-500">
                    {new Date(invite.expires_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </td>
                  <td className="py-3 px-4">
                    {invite.status === "pending" && (
                      <div className="flex items-center gap-2">
                        <CopyButton text={invite.invite_url} />
                        <RevokeButton invite={invite} />
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RevokeButton({ invite }: { invite: Invite }) {
  const qc = useQueryClient();
  const revokeMut = useMutation({
    mutationFn: () => revokeAdminInvite(invite.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-invites"] }),
  });
  return (
    <button
      onClick={() => {
        if (confirm(`Revoke invite for ${invite.email}?`)) revokeMut.mutate();
      }}
      disabled={revokeMut.isPending}
      className="text-zinc-400 hover:text-red-500 transition-colors"
      title="Revoke invite"
    >
      <X size={13} />
    </button>
  );
}
