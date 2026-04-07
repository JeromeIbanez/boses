"use client";

import { ExternalLink } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";

interface Integration {
  name: string;
  description: string;
  status: "available" | "coming_soon";
  category: string;
  logo: string;
  docsUrl?: string;
}

const integrations: Integration[] = [
  {
    name: "Slack",
    description: "Get notified when a simulation finishes or fails.",
    status: "coming_soon",
    category: "Notifications",
    logo: "/integrations/slack.svg",
    docsUrl: "/settings",
  },
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

function IntegrationCard({ integration }: { integration: Integration }) {
  const isAvailable = integration.status === "available";

  return (
    <div className="bg-white border border-zinc-200 rounded-xl p-4 flex flex-col gap-3 hover:border-zinc-300 transition-colors">
      <div className="flex items-center gap-3">
        <LogoBox name={integration.name} logo={integration.logo} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-zinc-900 truncate">{integration.name}</span>
            <span
              className={
                isAvailable
                  ? "shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200"
                  : "shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-zinc-100 text-zinc-400 border border-zinc-200"
              }
            >
              {isAvailable ? "Available" : "Soon"}
            </span>
          </div>
          <span className="text-[11px] text-zinc-400">{integration.category}</span>
        </div>
      </div>

      <p className="text-xs text-zinc-500 leading-relaxed">{integration.description}</p>

      {isAvailable && integration.docsUrl && (
        <a
          href={integration.docsUrl}
          target={integration.docsUrl.startsWith("http") ? "_blank" : undefined}
          rel={integration.docsUrl.startsWith("http") ? "noopener noreferrer" : undefined}
          className="flex items-center gap-1 text-xs font-medium text-violet-600 hover:text-violet-700 mt-auto"
        >
          Configure <ExternalLink size={11} />
        </a>
      )}
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
