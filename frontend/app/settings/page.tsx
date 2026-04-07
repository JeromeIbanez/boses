"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { getCompanySettings, updateCompanySettings } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [slackUrl, setSlackUrl] = useState<string>("");
  const [saved, setSaved] = useState(false);

  const { data: company, isLoading } = useQuery({
    queryKey: ["company-settings"],
    queryFn: getCompanySettings,
    onSuccess: (data: { slack_webhook_url: string | null }) => {
      setSlackUrl(data.slack_webhook_url ?? "");
    },
  } as Parameters<typeof useQuery>[0]);

  const { mutate: save, isLoading: isSaving, error } = useMutation({
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
        <Spinner size="sm" /> Loading…
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
                {isSaving ? <Spinner size="sm" /> : "Save"}
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
