"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Users, FileText, Play, ArrowLeft } from "lucide-react";
import { getProject } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import PersonasTab from "./PersonasTab";
import BriefingsTab from "./BriefingsTab";
import SimulationsTab from "./SimulationsTab";

const tabs = [
  { id: "personas", label: "Personas", icon: Users },
  { id: "briefings", label: "Briefings", icon: FileText },
  { id: "simulations", label: "Simulations", icon: Play },
] as const;

type Tab = typeof tabs[number]["id"];

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("personas");

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  if (isLoading) return <div className="px-8 py-8"><div className="h-6 w-48 bg-zinc-100 rounded animate-pulse" /></div>;
  if (!project) return <div className="px-8 py-8 text-sm text-zinc-500">Project not found.</div>;

  return (
    <div className="px-8 py-8">
      <button
        onClick={() => router.push("/projects")}
        className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 mb-5 transition-colors"
      >
        <ArrowLeft size={13} /> Back to Projects
      </button>

      <PageHeader title={project.name} description={project.description ?? undefined} />

      {/* Tabs */}
      <div className="flex gap-0 border-b border-zinc-200 mb-7">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 -mb-px transition-colors",
              activeTab === id
                ? "border-zinc-900 text-zinc-900 font-medium"
                : "border-transparent text-zinc-500 hover:text-zinc-700"
            )}
          >
            <Icon size={14} strokeWidth={1.8} />
            {label}
          </button>
        ))}
      </div>

      {activeTab === "personas" && <PersonasTab projectId={projectId} />}
      {activeTab === "briefings" && <BriefingsTab projectId={projectId} />}
      {activeTab === "simulations" && <SimulationsTab projectId={projectId} />}
    </div>
  );
}
