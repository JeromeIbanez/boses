"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle, Copy, Check, Trash2, Plus, Key } from "lucide-react";
import { getCompanySettings, updateCompanySettings, listApiKeys, createApiKey, revokeApiKey } from "@/lib/api";
import type { APIKey } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// API Keys sub-component
// ---------------------------------------------------------------------------

function APIKeysSection() {
  const queryClient = useQueryClient();
  const [newKeyName, setNewKeyName] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: listApiKeys,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => createApiKey(name),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setRevealedKey(data.key);
      setNewKeyName("");
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
                if (e.key === "Enter" && newKeyName.trim()) createMutation.mutate(newKeyName.trim());
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={() => newKeyName.trim() && createMutation.mutate(newKeyName.trim())}
              disabled={!newKeyName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? <Spinner /> : "Generate key"}
            </Button>
            <Button variant="secondary" onClick={() => { setShowForm(false); setNewKeyName(""); }}>
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
          {keys.map((key: APIKey) => (
            <div key={key.id} className="flex items-center gap-3 py-2 border-b border-zinc-100 last:border-0">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-800 truncate">{key.name}</p>
                <p className="text-xs text-zinc-400 font-mono">{key.key_prefix}…</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-zinc-400">
                  {key.last_used_at ? `Last used ${formatDate(key.last_used_at)}` : "Never used"}
                </p>
                <p className="text-xs text-zinc-300">Created {formatDate(key.created_at)}</p>
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
          ))}
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
// Main settings page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [slackUrl, setSlackUrl] = useState<string>("");
  const [saved, setSaved] = useState(false);

  const { data: company, isLoading } = useQuery({
    queryKey: ["company-settings"],
    queryFn: getCompanySettings,
  });

  useEffect(() => {
    if (company) setSlackUrl(company.slack_webhook_url ?? "");
  }, [company]);

  const { mutate: save, isPending: isSaving, error } = useMutation({
    mutationFn: () =>
      updateCompanySettings({ slack_webhook_url: slackUrl.trim() || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  if (isLoading) {
    return (
      <div className="px-8 py-8 flex items-center gap-2 text-zinc-400">
        <Spinner /> Loading…
      </div>
    );
  }

  return (
    <div className="px-8 py-8 max-w-2xl">
      <PageHeader title="Settings" description="Manage your workspace configuration." />

      <div className="mt-8 space-y-8">
        {/* Company */}
        <section className="bg-white border border-zinc-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-zinc-900 mb-4">Workspace</h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-zinc-500 mb-1">Company name</p>
              <p className="text-sm text-zinc-800 font-medium">{company?.name}</p>
            </div>
            <div>
              <p className="text-xs text-zinc-500 mb-1">Slug</p>
              <p className="text-sm text-zinc-500 font-mono">{company?.slug}</p>
            </div>
          </div>
        </section>

        {/* API Keys */}
        <APIKeysSection />

        {/* Slack */}
        <section className="bg-white border border-zinc-200 rounded-xl p-6">
          <div className="flex items-start gap-3 mb-5">
            <div className="w-8 h-8 rounded-lg border border-zinc-200 bg-zinc-50 flex items-center justify-center shrink-0 overflow-hidden">
              <img
                src="/integrations/slack.svg"
                alt="Slack"
                className="w-5 h-5 object-contain"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-900">Slack</h2>
              <p className="text-xs text-zinc-500 mt-0.5">
                Get notified in Slack when a simulation finishes.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                Incoming Webhook URL
              </label>
              <Input
                placeholder="https://hooks.slack.com/services/..."
                value={slackUrl}
                onChange={(e) => {
                  setSlackUrl(e.target.value);
                  setSaved(false);
                }}
              />
              <p className="text-xs text-zinc-400 mt-1.5">
                Create a webhook at{" "}
                <a
                  href="https://api.slack.com/messaging/webhooks"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-violet-600 hover:underline"
                >
                  api.slack.com/messaging/webhooks
                </a>
                , then paste the URL here.
              </p>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-xs text-red-600">
                <AlertCircle size={13} />
                {(error as Error).message}
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <Button
                variant="primary"
                onClick={() => save()}
                disabled={isSaving}
              >
                {isSaving ? <Spinner /> : "Save"}
              </Button>
              {saved && (
                <span className="flex items-center gap-1.5 text-xs text-green-600">
                  <CheckCircle2 size={13} />
                  Saved
                </span>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
