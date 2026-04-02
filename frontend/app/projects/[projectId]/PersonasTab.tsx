"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, Users, Sparkles, ArrowRight, RotateCcw, Trash2 } from "lucide-react";
import { getPersonaGroups, createPersonaGroup, generatePersonas, parsePersonaPrompt, deletePersonaGroup } from "@/lib/api";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Textarea from "@/components/ui/Textarea";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";

interface Props { projectId: string }

const statusVariant = {
  pending: "pending" as const,
  generating: "warning" as const,
  complete: "success" as const,
  failed: "error" as const,
};

type Step = "prompt" | "review";

const emptyForm = {
  name: "", age_min: "18", age_max: "45", gender: "All",
  location: "", occupation: "", income_level: "Middle",
  psychographic_notes: "", persona_count: "5",
};

export default function PersonasTab({ projectId }: Props) {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("prompt");
  const [prompt, setPrompt] = useState("");
  const [form, setForm] = useState(emptyForm);

  const { data: groups, isLoading } = useQuery({
    queryKey: ["persona-groups", projectId],
    queryFn: () => getPersonaGroups(projectId),
  });

  const parse = useMutation({
    mutationFn: () => parsePersonaPrompt(projectId, prompt),
    onSuccess: (data) => {
      setForm({
        name: data.name || "",
        age_min: String(data.age_min || 18),
        age_max: String(data.age_max || 45),
        gender: data.gender || "All",
        location: data.location || "",
        occupation: data.occupation || "",
        income_level: data.income_level || "Middle",
        psychographic_notes: data.psychographic_notes || "",
        persona_count: String(data.persona_count || 5),
      });
      setStep("review");
    },
  });

  const create = useMutation({
    mutationFn: () => createPersonaGroup(projectId, {
      ...form,
      age_min: Number(form.age_min),
      age_max: Number(form.age_max),
      persona_count: Number(form.persona_count),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["persona-groups", projectId] });
      setOpen(false);
      setStep("prompt");
      setPrompt("");
      setForm(emptyForm);
    },
  });

  const generate = useMutation({
    mutationFn: (groupId: string) => generatePersonas(projectId, groupId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["persona-groups", projectId] }),
  });

  const deleteGroup = useMutation({
    mutationFn: (groupId: string) => deletePersonaGroup(projectId, groupId),
    onMutate: async (groupId) => {
      await qc.cancelQueries({ queryKey: ["persona-groups", projectId] });
      const prev = qc.getQueryData(["persona-groups", projectId]);
      qc.setQueryData(["persona-groups", projectId], (old: typeof groups) =>
        old ? old.filter((g) => g.id !== groupId) : []
      );
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      qc.setQueryData(["persona-groups", projectId], ctx?.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["persona-groups", projectId] }),
  });

  const set = (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }));

  const handleClose = () => {
    setOpen(false);
    setStep("prompt");
    setPrompt("");
    setForm(emptyForm);
  };

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
                <div className="flex items-center gap-2 shrink-0">
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
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete "${g.name}" and all its personas?`)) deleteGroup.mutate(g.id);
                    }}
                    className="p-1.5 text-zinc-300 hover:text-red-500 transition-colors"
                    title="Delete group"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={handleClose} title="New Persona Group" width="max-w-xl">
        {step === "prompt" ? (
          <div className="space-y-4">
            <p className="text-sm text-zinc-500">
              Describe your target demographic in plain language. Be as specific or broad as you like.
            </p>
            <Textarea
              label="Who is your target audience?"
              placeholder={`e.g. "Metro Manila mothers aged 28–40, middle income, health-conscious working professionals who use TikTok and value family time"`}
              rows={4}
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              autoFocus
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={handleClose}>Cancel</Button>
              <Button
                onClick={() => parse.mutate()}
                disabled={!prompt.trim() || parse.isPending}
              >
                {parse.isPending ? "Analyzing…" : <><ArrowRight size={14} /> Continue</>}
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-500">Review and adjust the extracted details.</p>
              <button
                onClick={() => setStep("prompt")}
                className="text-xs text-zinc-400 hover:text-zinc-600 flex items-center gap-1"
              >
                <RotateCcw size={12} /> Edit prompt
              </button>
            </div>
            <Input label="Group name" value={form.name} onChange={set("name")} />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Min age" type="number" value={form.age_min} onChange={set("age_min")} />
              <Input label="Max age" type="number" value={form.age_max} onChange={set("age_max")} />
            </div>
            <Select label="Gender" value={form.gender} onChange={set("gender")}>
              <option>All</option><option>Female</option><option>Male</option><option>Non-binary</option>
            </Select>
            <Input label="Location" value={form.location} onChange={set("location")} />
            <Input label="Occupation" value={form.occupation} onChange={set("occupation")} />
            <Select label="Income level" value={form.income_level} onChange={set("income_level")}>
              <option>Low</option><option>Middle</option><option>Upper-middle</option><option>High</option>
            </Select>
            <Textarea label="Psychographic notes" rows={2} value={form.psychographic_notes} onChange={set("psychographic_notes")} />
            <Input label="Number of personas" type="number" min={1} max={10} value={form.persona_count} onChange={set("persona_count")} />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={handleClose}>Cancel</Button>
              <Button onClick={() => create.mutate()} disabled={!form.name || create.isPending}>
                {create.isPending ? "Creating…" : "Create Group"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
