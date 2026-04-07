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
    description: "Get notified in your Slack workspace when a simulation finishes.",
    status: "coming_soon",
    category: "Notifications",
    logo: "/integrations/slack.svg",
  },
  {
    name: "Zapier",
    description: "Connect Boses to 6,000+ apps. Trigger workflows when simulations complete.",
    status: "coming_soon",
    category: "Automation",
    logo: "/integrations/zapier.svg",
  },
  {
    name: "Notion",
    description: "Auto-export simulation results to a Notion database for team collaboration.",
    status: "coming_soon",
    category: "Productivity",
    logo: "/integrations/notion.svg",
  },
  {
    name: "Canva",
    description: "Push persona profiles and simulation insights into Canva presentation templates.",
    status: "coming_soon",
    category: "Design",
    logo: "/integrations/canva.svg",
  },
  {
    name: "Google Slides",
    description: "Export results directly to a Google Slides deck ready for client presentations.",
    status: "coming_soon",
    category: "Presentations",
    logo: "/integrations/google-slides.svg",
  },
];

const categoryOrder = ["Notifications", "Automation", "Productivity", "Design", "Presentations"];

function IntegrationCard({ integration }: { integration: Integration }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="w-10 h-10 rounded-lg border border-zinc-200 bg-zinc-50 flex items-center justify-center overflow-hidden shrink-0">
          <img
            src={integration.logo}
            alt={integration.name}
            className="w-6 h-6 object-contain"
            onError={(e) => {
              const target = e.currentTarget;
              target.style.display = "none";
              const parent = target.parentElement;
              if (parent) {
                parent.textContent = integration.name.charAt(0);
                parent.className =
                  "w-10 h-10 rounded-lg border border-zinc-200 bg-zinc-100 flex items-center justify-center text-sm font-semibold text-zinc-500 shrink-0";
              }
            }}
          />
        </div>
        <span
          className={
            integration.status === "available"
              ? "text-xs font-medium px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200"
              : "text-xs font-medium px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-500 border border-zinc-200"
          }
        >
          {integration.status === "available" ? "Available" : "Coming soon"}
        </span>
      </div>

      <div>
        <p className="text-sm font-semibold text-zinc-900">{integration.name}</p>
        <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{integration.description}</p>
      </div>

      {integration.status === "available" && integration.docsUrl ? (
        <a
          href={integration.docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto flex items-center gap-1.5 text-xs font-medium text-violet-600 hover:text-violet-700"
        >
          View docs <ExternalLink size={12} />
        </a>
      ) : (
        <p className="mt-auto text-xs text-zinc-400">Notify me when available</p>
      )}
    </div>
  );
}

export default function IntegrationsPage() {
  const grouped = categoryOrder.reduce<Record<string, Integration[]>>((acc, cat) => {
    const items = integrations.filter((i) => i.category === cat);
    if (items.length) acc[cat] = items;
    return acc;
  }, {});

  return (
    <div className="px-8 py-8 max-w-4xl">
      <PageHeader
        title="Integrations"
        description="Connect Boses to the tools your team already uses."
      />

      <div className="mt-8 space-y-10">
        {Object.entries(grouped).map(([category, items]) => (
          <section key={category}>
            <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-widest mb-4">
              {category}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {items.map((integration) => (
                <IntegrationCard key={integration.name} integration={integration} />
              ))}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-12 rounded-xl border border-zinc-200 bg-zinc-50 px-6 py-5">
        <p className="text-sm font-medium text-zinc-900">Don&apos;t see what you need?</p>
        <p className="text-xs text-zinc-500 mt-1">
          All integrations above are on our roadmap. You can also use our{" "}
          <a
            href="https://docs.temujintechnologies.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-violet-600 hover:underline"
          >
            REST API
          </a>{" "}
          to build your own integration or connect via Zapier when it launches.
        </p>
      </div>
    </div>
  );
}
