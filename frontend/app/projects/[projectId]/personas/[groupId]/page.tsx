"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { getPersonaGroup, getPersonas, deletePersona, deleteAllPersonas } from "@/lib/api";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { Persona } from "@/types";

const API_ROOT = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
function avatarSrc(url: string | null | undefined) {
  if (!url) return null;
  return url.startsWith("http") ? url : API_ROOT + url;
}

function PersonaAvatar({ persona }: { persona: Persona }) {
  const [err, setErr] = useState(false);
  const src = !err ? avatarSrc(persona.avatar_url) : null;
  if (src) {
    return (
      <img
        src={src}
        alt={persona.full_name}
        onError={() => setErr(true)}
        className="w-9 h-9 rounded-full object-cover shrink-0"
      />
    );
  }
  return (
    <div className="w-9 h-9 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-medium shrink-0">
      {persona.full_name.charAt(0)}
    </div>
  );
}
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import LibraryBadge from "@/components/ui/LibraryBadge";
import PageHeader from "@/components/layout/PageHeader";
import Spinner from "@/components/ui/Spinner";

export default function PersonaGroupPage() {
  const { projectId, groupId } = useParams<{ projectId: string; groupId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [confirmPending, setConfirmPending] = useState<{ message: string; action: () => void } | null>(null);

  const remove = useMutation({
    mutationFn: (personaId: string) => deletePersona(projectId, groupId, personaId),
    onMutate: async (personaId) => {
      await qc.cancelQueries({ queryKey: ["personas", groupId] });
      const prev = qc.getQueryData<Persona[]>(["personas", groupId]);
      if (prev) qc.setQueryData(["personas", groupId], prev.filter((p) => p.id !== personaId));
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(["personas", groupId], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["personas", groupId] }),
  });

  const removeAll = useMutation({
    mutationFn: () => deleteAllPersonas(projectId, groupId),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["personas", groupId] });
      const prev = qc.getQueryData<Persona[]>(["personas", groupId]);
      qc.setQueryData(["personas", groupId], []);
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(["personas", groupId], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["personas", groupId] }),
  });

  const { data: group } = useQuery({
    queryKey: ["persona-group", groupId],
    queryFn: () => getPersonaGroup(projectId, groupId),
    refetchInterval: (q) => {
      const status = q.state.data?.generation_status;
      return status === "generating" ? 2000 : false;
    },
  });

  const { data: personas, isLoading } = useQuery({
    queryKey: ["personas", groupId],
    queryFn: () => getPersonas(projectId, groupId),
    enabled: group?.generation_status === "complete",
    refetchInterval: group?.generation_status === "generating" ? 3000 : false,
  });

  if (!group) return null;

  return (
    <div className="px-8 py-8">
      <ConfirmDialog
        open={confirmPending !== null}
        message={confirmPending?.message ?? ""}
        onConfirm={() => confirmPending?.action()}
        onClose={() => setConfirmPending(null)}
      />
      <button
        onClick={() => router.push(`/projects/${projectId}`)}
        className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 mb-5 transition-colors"
      >
        <ArrowLeft size={13} /> Back to Project
      </button>

      <div className="flex items-start justify-between gap-4">
        <PageHeader title={group.name} description={`${group.age_min}–${group.age_max} yrs · ${group.gender} · ${group.occupation} · ${group.location}`} />
        {personas && personas.length > 0 && (
          <button
            onClick={() => {
              setConfirmPending({ message: `Delete all ${personas.length} persona(s) in this group?`, action: () => removeAll.mutate() });
            }}
            disabled={removeAll.isPending}
            className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 rounded-md px-3 py-1.5 transition-colors shrink-0 disabled:opacity-50"
          >
            <Trash2 size={13} /> Delete All Personas
          </button>
        )}
      </div>

      {/* Demographic summary */}
      <div className="flex flex-wrap gap-2 mb-7">
        <Badge variant="default">Income: {group.income_level}</Badge>
        <Badge variant="default">{group.persona_count} personas</Badge>
        {group.generation_status !== "complete" && (
          <Badge variant={group.generation_status === "generating" ? "warning" : group.generation_status === "failed" ? "error" : "pending"}>
            {group.generation_status === "generating" && <Spinner className="mr-1 h-3 w-3" />}
            {group.generation_status}
          </Badge>
        )}
      </div>

      {group.generation_status === "generating" && (
        <div className="mb-8 bg-amber-50 border border-amber-100 rounded-lg px-4 py-4 space-y-3">
          {group.generation_progress ? (
            <>
              <div className="flex items-center justify-between text-xs text-zinc-500">
                <span className="flex items-center gap-2">
                  <Spinner className="h-3 w-3 border-amber-400 border-t-amber-700" />
                  {group.generation_progress.current_name
                    ? `Generating ${group.generation_progress.current_name}…`
                    : "Preparing personas…"}
                </span>
                <span className="font-medium text-zinc-700">
                  {group.generation_progress.current} of {group.generation_progress.total}
                </span>
              </div>
              <div className="w-full bg-amber-100 rounded-full h-1.5">
                <div
                  className="bg-amber-500 h-1.5 rounded-full transition-all duration-500"
                  style={{
                    width: `${group.generation_progress.total > 0
                      ? (group.generation_progress.current / group.generation_progress.total) * 100
                      : 0}%`
                  }}
                />
              </div>
              {group.generation_progress.completed.length > 0 && (
                <div className="space-y-1">
                  {group.generation_progress.completed.map((name) => (
                    <div key={name} className="flex items-center gap-2 text-xs text-zinc-500">
                      <span className="text-emerald-500">✓</span>
                      {name}
                    </div>
                  ))}
                  {group.generation_progress.current_name && (
                    <div className="flex items-center gap-2 text-xs text-zinc-700 font-medium">
                      <Spinner className="h-3 w-3 border-zinc-300 border-t-zinc-600 shrink-0" />
                      {group.generation_progress.current_name}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center gap-3 text-sm text-zinc-500">
              <Spinner className="border-amber-400 border-t-amber-700" />
              Generating {group.persona_count} personas with AI…
            </div>
          )}
        </div>
      )}

      {isLoading && <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{[1,2,3,4,5].map(i => <div key={i} className="h-48 bg-zinc-100 rounded-lg animate-pulse" />)}</div>}

      {personas && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {personas.map((p) => (
            <Card
              key={p.id}
              onClick={() => router.push(`/projects/${projectId}/personas/${groupId}/${p.id}`)}
            >
              <div className="flex items-start gap-3 mb-3">
                <PersonaAvatar persona={p} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-medium text-zinc-900">{p.full_name}</h3>
                    {p.library_persona_id && <LibraryBadge />}
                  </div>
                  <p className="text-xs text-zinc-400">{p.age} · {p.occupation}</p>
                  {p.archetype_label && (
                    <p className="text-[10px] text-zinc-400 italic">{p.archetype_label}</p>
                  )}
                  <p className="text-[10px] font-mono text-zinc-300">#{p.persona_code}</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmPending({ message: `Delete ${p.full_name}?`, action: () => remove.mutate(p.id) });
                  }}
                  className="p-1 text-zinc-300 hover:text-red-500 transition-colors shrink-0"
                  title="Delete persona"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              {p.personality_traits && p.personality_traits.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {p.personality_traits.slice(0, 3).map((t) => (
                    <Badge key={t} variant="default">{t}</Badge>
                  ))}
                </div>
              )}

              {p.values_and_motivations && (
                <p className="text-xs text-zinc-500 line-clamp-2 mb-1">
                  <span className="font-medium text-zinc-700">Motivated by: </span>
                  {p.values_and_motivations}
                </p>
              )}
              {p.pain_points && (
                <p className="text-xs text-zinc-500 line-clamp-2">
                  <span className="font-medium text-zinc-700">Pain points: </span>
                  {p.pain_points}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}

    </div>
  );
}
