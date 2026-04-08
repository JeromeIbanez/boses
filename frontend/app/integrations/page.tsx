"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, CheckCircle2, AlertCircle } from "lucide-react";
import { getCompanySettings, updateCompanySettings } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";

interface Integration {
  name: string;
  description: string;
  status: "coming_soon";
  category: string;
  logo: string;
}

const integrations: Integration[] = [
  {
    name: "Zapier",
    description: "Trigger workflows across 6,000+ apps on simulation events.",
    status: "coming_soon",
    category: "Automation",
    logo: "/integrations/zapier.svg",
  },
  {
    name: "Notion",
    description: "Auto-export simulation results to a Notion database.",
    status: "coming_soon",
    category: "Productivity",
    logo: "/integrations/notion.svg",
  },
  {
    name: "Canva",
    description: "Push persona profiles and insights into Canva templates.",
    status: "coming_soon",
    category: "Design",
    logo: "/integrations/canva.svg",
  },
  {
    name: "Google Slides",
    description: "Export results to a Slides deck ready for client presentations.",
    status: "coming_soon",
    category: "Presentations",
    logo: "/integrations/google-slides.svg",
  },
];

function LogoBox({ name, logo }: { name: string; logo: string }) {
  return (
    <div className="w-9 h-9 rounded-lg border border-zinc-200 bg-white flex items-center justify-center shrink-0 overflow-hidden">
      <img
        src={logo}
        alt={name}
        className="w-5 h-5 object-contain"
        onError={(e) => {
          const el = e.currentTarget;
          el.style.display = "none";
          const parent = el.parentElement;
          if (parent) {
            parent.textContent = name.charAt(0);
            parent.className =
              "w-9 h-9 rounded-lg border border-zinc-200 bg-zinc-100 flex items-center justify-center text-sm font-semibold text-zinc-500 shrink-0";
          }
        }}
      />
    </div>
  );
}

function SlackCard() {
  const queryClient = useQueryClient();
  const [slackUrl, setSlackUrl] = useState("");
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

  const isConnected = !!company?.slack_webhook_url;

  return (
    <div className="bg-white border border-zinc-200 rounded-xl p-4 flex flex-col gap-4 col-span-2 lg:col-span-3">
      <div className="flex items-center gap-3">
        <LogoBox name="Slack" logo="/integrations/slack.svg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-zinc-900">Slack</span>
            <span
              className={
                isConnected
                  ? "shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200"
                  : "shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-zinc-100 text-zinc-400 border border-zinc-200"
              }
            >
              {isConnected ? "Connected" : "Not connected"}
            </span>
          </div>
          <span className="text-[11px] text-zinc-400">Notifications</span>
        </div>
      </div>

      <p className="text-xs text-zinc-500 leading-relaxed">
        Get notified in Slack when a simulation finishes or fails.
      </p>

      {isLoading ? (
        <div className="flex items-center gap-2 text-zinc-400 text-xs">
          <Spinner /> Loading…
        </div>
      ) : (
        <div className="space-y-2">
          <label className="block text-xs font-medium text-zinc-700">
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
          <p className="text-xs text-zinc-400">
            Create a webhook at{" "}
            <a
              href="https://api.slack.com/messaging/webhooks"
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet-600 hover:underline inline-flex items-center gap-0.5"
            >
              api.slack.com/messaging/webhooks <ExternalLink size={10} />
            </a>
            , then paste the URL here.
          </p>

          {error && (
            <div className="flex items-center gap-2 text-xs text-red-600">
              <AlertCircle size={13} />
              {(error as Error).message}
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <Button variant="primary" onClick={() => save()} disabled={isSaving}>
              {isSaving ? <Spinner /> : "Save"}
            </Button>
            {saved && (
              <span className="flex items-center gap-1.5 text-xs text-green-600">
                <CheckCircle2 size={13} /> Saved
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function IntegrationCard({ integration }: { integration: Integration }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-xl p-4 flex flex-col gap-3 hover:border-zinc-300 transition-colors">
      <div className="flex items-center gap-3">
        <LogoBox name={integration.name} logo={integration.logo} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-zinc-900 truncate">{integration.name}</span>
            <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-zinc-100 text-zinc-400 border border-zinc-200">
              Soon
            </span>
          </div>
          <span className="text-[11px] text-zinc-400">{integration.category}</span>
        </div>
      </div>
      <p className="text-xs text-zinc-500 leading-relaxed">{integration.description}</p>
    </div>
  );
}

export default function IntegrationsPage() {
  return (
    <div className="px-8 py-8 max-w-3xl">
      <PageHeader
        title="Integrations"
        description="Connect Boses to the tools your team already uses."
      />

      <div className="mt-6 grid grid-cols-2 lg:grid-cols-3 gap-3">
        <SlackCard />
        {integrations.map((integration) => (
          <IntegrationCard key={integration.name} integration={integration} />
        ))}
      </div>

      <p className="mt-6 text-xs text-zinc-400">
        Missing an integration?{" "}
        <a
          href="https://docs.temujintechnologies.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-violet-600 hover:underline"
        >
          Use the REST API
        </a>{" "}
        to build your own.
      </p>
    </div>
  );
}
