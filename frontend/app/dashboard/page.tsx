"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, FolderOpen } from "lucide-react";
import { getProjects } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: getProjects,
  });

  return (
    <div className="px-8 py-8">
      <PageHeader
        title="Dashboard"
        description="Your active simulation projects"
        action={
          <Button onClick={() => router.push("/projects")}>
            <Plus size={14} /> New Project
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-36 bg-zinc-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : !projects?.length ? (
        <EmptyState
          icon={FolderOpen}
          title="No projects yet"
          description="Create your first project to start running market simulations."
          action={
            <Button onClick={() => router.push("/projects")}>
              <Plus size={14} /> Create Project
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Card key={p.id} onClick={() => router.push(`/projects/${p.id}`)}>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                  <FolderOpen size={15} className="text-zinc-500" strokeWidth={1.5} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-zinc-900 truncate">{p.name}</h3>
                  {p.description && (
                    <p className="text-xs text-zinc-400 mt-0.5 line-clamp-2">{p.description}</p>
                  )}
                  <p className="text-xs text-zinc-300 mt-3">{formatDate(p.created_at)}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
