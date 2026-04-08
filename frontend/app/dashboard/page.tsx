"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, FolderOpen, Trash2 } from "lucide-react";
import { getProjects, createProject, deleteProject } from "@/lib/api";
import PageHeader from "@/components/layout/PageHeader";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Input from "@/components/ui/Input";
import Textarea from "@/components/ui/Textarea";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [confirmPending, setConfirmPending] = useState<{ message: string; action: () => void } | null>(null);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: getProjects,
  });

  const mutation = useMutation({
    mutationFn: () => createProject({ name, description: description || undefined }),
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setOpen(false);
      setName("");
      setDescription("");
      router.push(`/projects/${project.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: ["projects"] });
      const previous = qc.getQueryData(["projects"]);
      qc.setQueryData(["projects"], (old: typeof projects) =>
        old ? old.filter((p) => p.id !== id) : []
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      qc.setQueryData(["projects"], context?.previous);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  const hasProjects = !isLoading && !!projects?.length;

  return (
    <div className="px-8 py-8">
      <PageHeader
        title="Dashboard"
        description="Your active simulation projects"
        action={
          hasProjects ? (
            <Button onClick={() => setOpen(true)}>
              <Plus size={14} /> Create Project
            </Button>
          ) : undefined
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
            <Button onClick={() => setOpen(true)}>
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
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-medium text-zinc-900 truncate">{p.name}</h3>
                  {p.description && (
                    <p className="text-xs text-zinc-400 mt-0.5 line-clamp-2">{p.description}</p>
                  )}
                  <p className="text-xs text-zinc-300 mt-3">{formatDate(p.created_at)}</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmPending({ message: `Delete "${p.name}"? This cannot be undone.`, action: () => deleteMutation.mutate(p.id) });
                  }}
                  className="p-1.5 rounded-md text-zinc-300 hover:text-red-500 hover:bg-red-50 transition-colors shrink-0"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={confirmPending !== null}
        message={confirmPending?.message ?? ""}
        onConfirm={() => confirmPending?.action()}
        onClose={() => setConfirmPending(null)}
      />
      <Modal open={open} onClose={() => setOpen(false)} title="New Project">
        <div className="space-y-4">
          <Input
            label="Project name"
            placeholder="e.g. Q2 Product Launch — Philippines"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Textarea
            label="Description (optional)"
            placeholder="What are you trying to learn from this simulation?"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              onClick={() => mutation.mutate()}
              disabled={!name.trim() || mutation.isPending}
            >
              {mutation.isPending ? "Creating…" : "Create Project"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
