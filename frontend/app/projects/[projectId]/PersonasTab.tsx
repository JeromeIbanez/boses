"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, Users, Sparkles } from "lucide-react";
import { getPersonaGroups, createPersonaGroup, generatePersonas } from "@/lib/api";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Input from "@/components/ui/Input";
import Textarea from "@/components/ui/Textarea";
import Select from "@/components/ui/Select";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import type { PersonaGroup } from "@/types";

interface Props { projectId: string }

const statusVariant = {
  pending: "pending" as const,
  generating: "warning" as const,
  complete: "success" as const,
  failed: "error" as const,
};

export default function PersonasTab({ projectId }: Props) {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", description: "", age_min: "25", age_max: "45",
    gender: "All", location: "", occupation: "", income_level: "Middle",
    psychographic_notes: "", persona_count: "5",
  });

  const { data: groups, isLoading } = useQuery({
    queryKey: ["persona-groups", projectId],
    queryFn: () => getPersonaGroups(projectId),
  });

  const create = useMutation({
    mutationFn: () => createPersonaGroup(projectId, {
      ...form,
      age_min: Number(form.age_min),
      age_max: Number(form.age_max),
      persona_count: Number(form.persona_count),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["persona-groups", projectId] }); setOpen(false); },
  });

  const generate = useMutation({
    mutationFn: (groupId: string) => generatePersonas(projectId, groupId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["persona-groups", projectId] }),
  });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <>
      <div className="flex justify-end mb-5">
        <Button onClick={() => setOpen(true)}><Plus size={14} /> New Persona Group</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[1, 2].map(i => <div key={i} className="h-24 bg-zinc-100 rounded-lg animate-pulse" />)}</div>
      ) : !groups?.length ? (
        <EmptyState icon={Users} title="No persona groups yet" description="Define a target market to generate personas for simulation." action={<Button onClick={() => setOpen(true)}><Plus size={14} /> New Group</Button>} />
      ) : (
        <div className="space-y-3">
          {groups.map(g => (
            <Card key={g.id}>
              <div className="flex items-start justify-between">
                <div className="cursor-pointer flex-1" onClick={() => router.push(`/projects/${projectId}/personas/${g.id}`)}>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-medium text-zinc-900">{g.name}</h3>
                    <Badge variant={statusVariant[g.generation_status]}>{g.generation_status}</Badge>
                  </div>
                  <p className="text-xs text-zinc-500">
                    {g.age_min}–{g.age_max} yrs · {g.gender} · {g.occupation} · {g.location}
                  </p>
                  <p className="text-xs text-zinc-400 mt-0.5">{g.persona_count} personas</p>
                </div>
                {g.generation_status === "pending" && (
                  <Button size="sm" onClick={() => generate.mutate(g.id)}>
                    <Sparkles size={13} /> Generate
                  </Button>
                )}
                {g.generation_status === "failed" && (
                  <Button size="sm" variant="danger" onClick={() => generate.mutate(g.id)}>
                    Retry
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="New Persona Group" width="max-w-xl">
        <div className="space-y-4">
          <Input label="Group name" placeholder='e.g. "Metro Manila Mothers"' value={form.name} onChange={set("name")} />
          <Input label="Description (optional)" placeholder="Brief description of this demographic" value={form.description} onChange={set("description")} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Min age" type="number" value={form.age_min} onChange={set("age_min")} />
            <Input label="Max age" type="number" value={form.age_max} onChange={set("age_max")} />
          </div>
          <Select label="Gender" value={form.gender} onChange={set("gender")}>
            <option>All</option><option>Female</option><option>Male</option><option>Non-binary</option>
          </Select>
          <Input label="Location" placeholder="e.g. Metro Manila, Philippines" value={form.location} onChange={set("location")} />
          <Input label="Occupation" placeholder="e.g. Call center agent" value={form.occupation} onChange={set("occupation")} />
          <Select label="Income level" value={form.income_level} onChange={set("income_level")}>
            <option>Low</option><option>Middle</option><option>Upper-middle</option><option>High</option>
          </Select>
          <Textarea label="Psychographic notes (optional)" placeholder="Values, lifestyle, pain points, media habits..." rows={3} value={form.psychographic_notes} onChange={set("psychographic_notes")} />
          <Input label="Number of personas to generate" type="number" min={1} max={10} value={form.persona_count} onChange={set("persona_count")} />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => create.mutate()} disabled={!form.name || !form.location || !form.occupation || create.isPending}>
              {create.isPending ? "Creating…" : "Create Group"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
