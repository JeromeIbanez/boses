"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, Play, ChevronRight, Trash2 } from "lucide-react";
import { getSimulations, createSimulation, getPersonaGroups, getBriefings, deleteSimulation } from "@/lib/api";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Select from "@/components/ui/Select";
import Textarea from "@/components/ui/Textarea";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

interface Props { projectId: string }

const statusVariant: Record<string, "pending" | "warning" | "success" | "error"> = {
  pending: "pending",
  running: "warning",
  complete: "success",
  failed: "error",
};

export default function SimulationsTab({ projectId }: Props) {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [groupId, setGroupId] = useState("");
  const [briefingId, setBriefingId] = useState("");
  const [question, setQuestion] = useState("");

  const { data: simulations, isLoading } = useQuery({
    queryKey: ["simulations", projectId],
    queryFn: () => getSimulations(projectId),
  });

  const { data: groups } = useQuery({
    queryKey: ["persona-groups", projectId],
    queryFn: () => getPersonaGroups(projectId),
    enabled: open,
  });

  const { data: briefings } = useQuery({
    queryKey: ["briefings", projectId],
    queryFn: () => getBriefings(projectId),
    enabled: open,
  });

  const deleteSim = useMutation({
    mutationFn: (simId: string) => deleteSimulation(projectId, simId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulations", projectId] }),
  });

  const run = useMutation({
    mutationFn: () => createSimulation(projectId, {
      persona_group_id: groupId,
      briefing_id: briefingId,
      prompt_question: question,
    }),
    onSuccess: (sim) => {
      qc.invalidateQueries({ queryKey: ["simulations", projectId] });
      setOpen(false);
      setStep(0);
      setGroupId("");
      setBriefingId("");
      setQuestion("");
      router.push(`/projects/${projectId}/simulations/${sim.id}`);
    },
  });

  return (
    <>
      <div className="flex justify-end mb-5">
        <Button onClick={() => setOpen(true)}><Plus size={14} /> Run Simulation</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[1, 2].map(i => <div key={i} className="h-20 bg-zinc-100 rounded-lg animate-pulse" />)}</div>
      ) : !simulations?.length ? (
        <EmptyState icon={Play} title="No simulations yet" description="Run your first simulation to see how your target personas react to your product." action={<Button onClick={() => setOpen(true)}><Play size={14} /> Run Simulation</Button>} />
      ) : (
        <div className="space-y-3">
          {simulations.map(s => (
            <Card key={s.id} onClick={() => router.push(`/projects/${projectId}/simulations/${s.id}`)}>
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={statusVariant[s.status]}>{s.status}</Badge>
                    <span className="text-xs text-zinc-400">{formatDate(s.created_at)}</span>
                  </div>
                  <p className="text-sm text-zinc-700 truncate">{s.prompt_question}</p>
                </div>
                <div className="flex items-center gap-1 ml-3 shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm("Delete this simulation and all its results?")) deleteSim.mutate(s.id);
                    }}
                    className="p-1.5 text-zinc-300 hover:text-red-500 transition-colors"
                    title="Delete simulation"
                  >
                    <Trash2 size={14} />
                  </button>
                  <ChevronRight size={16} className="text-zinc-300" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Simulation Wizard */}
      <Modal open={open} onClose={() => { setOpen(false); setStep(0); }} title={`Run Simulation — Step ${step + 1} of 3`} width="max-w-xl">
        <div className="space-y-4">
          {step === 0 && (
            <>
              <p className="text-sm text-zinc-500">Select the persona group to simulate against.</p>
              <Select label="Persona Group" value={groupId} onChange={e => setGroupId(e.target.value)}>
                <option value="">Select a group…</option>
                {groups?.filter(g => g.generation_status === "complete").map(g => (
                  <option key={g.id} value={g.id}>{g.name} ({g.persona_count} personas)</option>
                ))}
              </Select>
              {groups && groups.filter(g => g.generation_status === "complete").length === 0 && (
                <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-md">No groups with generated personas yet. Generate personas first.</p>
              )}
            </>
          )}
          {step === 1 && (
            <>
              <p className="text-sm text-zinc-500">Choose the briefing document to test.</p>
              <Select label="Briefing" value={briefingId} onChange={e => setBriefingId(e.target.value)}>
                <option value="">Select a briefing…</option>
                {briefings?.map(b => (
                  <option key={b.id} value={b.id}>{b.title}</option>
                ))}
              </Select>
            </>
          )}
          {step === 2 && (
            <>
              <p className="text-sm text-zinc-500">What do you want to know? Be specific about what to test.</p>
              <Textarea
                label="Simulation question"
                placeholder={"e.g. How would they react to this tagline? or Would they trust this brand based on the briefing?"}
                rows={4}
                value={question}
                onChange={e => setQuestion(e.target.value)}
              />
            </>
          )}

          {/* Wizard nav */}
          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => { if (step === 0) setOpen(false); else setStep(s => s - 1); }}>
              {step === 0 ? "Cancel" : "Back"}
            </Button>
            {step < 2 ? (
              <Button
                onClick={() => setStep(s => s + 1)}
                disabled={(step === 0 && !groupId) || (step === 1 && !briefingId)}
              >
                Next
              </Button>
            ) : (
              <Button onClick={() => run.mutate()} disabled={!question.trim() || run.isPending}>
                {run.isPending ? "Starting…" : "Run Simulation"}
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  );
}
