"use client";

import { useReducer, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, Play, ChevronRight, Trash2, Bot, User, MessageSquare, ClipboardList, Users, BarChart2 } from "lucide-react";
import {
  getSimulations, createSimulation, getPersonaGroups, getBriefings,
  deleteSimulation, getPersonas, uploadSurveyFile, runSurvey, runConjointDesign,
} from "@/lib/api";
import type { ConjointAttribute } from "@/types";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Select from "@/components/ui/Select";
import Textarea from "@/components/ui/Textarea";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

interface Props { projectId: string }

const statusVariant: Record<string, "pending" | "warning" | "success" | "error"> = {
  pending: "pending",
  running: "warning",
  active: "warning",
  generating_report: "warning",
  complete: "success",
  failed: "error",
};

import type { Simulation as SimType_ } from "@/types";
type SimType = SimType_["simulation_type"];

const SIM_TYPES: { id: SimType; label: string; description: string; icon: React.ReactNode }[] = [
  {
    id: "concept_test",
    label: "Concept Test",
    description: "All personas read a briefing and answer a single research question.",
    icon: <MessageSquare size={18} />,
  },
  {
    id: "idi_ai",
    label: "IDI — AI Assisted",
    description: "Boses interviews every persona in the group using your script. A report is generated automatically.",
    icon: <Bot size={18} />,
  },
  {
    id: "idi_manual",
    label: "IDI — Manual",
    description: "You conduct the interview yourself in a live chat with one persona. End anytime to generate a report.",
    icon: <User size={18} />,
  },
  {
    id: "survey",
    label: "Survey",
    description: "Upload your survey form and every persona fills it out independently. Get per-question aggregate results.",
    icon: <ClipboardList size={18} />,
  },
  {
    id: "focus_group",
    label: "Focus Group",
    description: "Personas discuss a topic together in a moderated group session, reacting to each other's statements.",
    icon: <Users size={18} />,
  },
  {
    id: "conjoint",
    label: "Conjoint / Trade-Off Test",
    description: "Personas choose between product profiles with different attributes and prices, revealing what they actually trade off.",
    icon: <BarChart2 size={18} />,
  },
];

// ---------------------------------------------------------------------------
// Wizard state — useReducer keeps all form state in one place and makes
// handleClose a single dispatch({ type: "RESET" }) instead of 13 setters.
// ---------------------------------------------------------------------------

interface WizardState {
  step: number;
  simType: SimType;
  groupIds: string[];
  briefingIds: string[];
  question: string;
  scriptMode: "text" | "file";
  scriptText: string;
  scriptFile: File | null;
  idiPersonaId: string;
  surveyFile: File | null;
  surveySimId: string | null;
  parsedQuestions: { id: string; type: string; text: string }[];
  conjointAttributes: ConjointAttribute[];
  conjointNTasks: number;
  conjointSimId: string | null;
}

const INITIAL_WIZARD_STATE: WizardState = {
  step: 0,
  simType: "concept_test",
  groupIds: [],
  briefingIds: [],
  question: "",
  scriptMode: "text",
  scriptText: "",
  scriptFile: null,
  idiPersonaId: "",
  surveyFile: null,
  surveySimId: null,
  parsedQuestions: [],
  conjointAttributes: [
    { name: "Price", levels: ["$49", "$99", "$149"] },
    { name: "Feature", levels: ["Basic", "Premium"] },
  ],
  conjointNTasks: 10,
  conjointSimId: null,
};

type WizardAction =
  | { type: "RESET" }
  | { type: "SET_STEP"; payload: number }
  | { type: "SET_SIM_TYPE"; payload: SimType }
  | { type: "SET_GROUP_IDS"; payload: string[] }
  | { type: "SET_BRIEFING_IDS"; payload: string[] }
  | { type: "SET_QUESTION"; payload: string }
  | { type: "SET_SCRIPT_MODE"; payload: "text" | "file" }
  | { type: "SET_SCRIPT_TEXT"; payload: string }
  | { type: "SET_SCRIPT_FILE"; payload: File | null }
  | { type: "SET_IDI_PERSONA_ID"; payload: string }
  | { type: "SET_SURVEY_FILE"; payload: File | null }
  | { type: "SET_SURVEY_SIM_ID"; payload: string | null }
  | { type: "SET_PARSED_QUESTIONS"; payload: { id: string; type: string; text: string }[] }
  | { type: "SET_CONJOINT_ATTRIBUTES"; payload: ConjointAttribute[] }
  | { type: "SET_CONJOINT_N_TASKS"; payload: number }
  | { type: "SET_CONJOINT_SIM_ID"; payload: string | null };

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "RESET": return INITIAL_WIZARD_STATE;
    case "SET_STEP": return { ...state, step: action.payload };
    case "SET_SIM_TYPE": return { ...state, simType: action.payload };
    case "SET_GROUP_IDS": return { ...state, groupIds: action.payload, idiPersonaId: "" };
    case "SET_BRIEFING_IDS": return { ...state, briefingIds: action.payload };
    case "SET_QUESTION": return { ...state, question: action.payload };
    case "SET_SCRIPT_MODE": return { ...state, scriptMode: action.payload };
    case "SET_SCRIPT_TEXT": return { ...state, scriptText: action.payload };
    case "SET_SCRIPT_FILE": return { ...state, scriptFile: action.payload };
    case "SET_IDI_PERSONA_ID": return { ...state, idiPersonaId: action.payload };
    case "SET_SURVEY_FILE": return { ...state, surveyFile: action.payload };
    case "SET_SURVEY_SIM_ID": return { ...state, surveySimId: action.payload };
    case "SET_PARSED_QUESTIONS": return { ...state, parsedQuestions: action.payload };
    case "SET_CONJOINT_ATTRIBUTES": return { ...state, conjointAttributes: action.payload };
    case "SET_CONJOINT_N_TASKS": return { ...state, conjointNTasks: action.payload };
    case "SET_CONJOINT_SIM_ID": return { ...state, conjointSimId: action.payload };
    default: return state;
  }
}

export default function SimulationsTab({ projectId }: Props) {
  const router = useRouter();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const surveyFileRef = useRef<HTMLInputElement>(null);

  const [open, setOpen] = useState(false);
  const [confirmPending, setConfirmPending] = useState<{ message: string; action: () => void } | null>(null);

  const [
    { step, simType, groupIds, briefingIds, question, scriptMode, scriptText, scriptFile,
      idiPersonaId, surveyFile, surveySimId, parsedQuestions, conjointAttributes, conjointNTasks, conjointSimId },
    dispatch,
  ] = useReducer(wizardReducer, INITIAL_WIZARD_STATE);

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

  const { data: personas } = useQuery({
    queryKey: ["personas", ...groupIds],
    queryFn: async () => {
      const results = await Promise.all(groupIds.map(id => getPersonas(projectId, id)));
      return results.flat();
    },
    enabled: open && simType === "idi_manual" && groupIds.length > 0,
  });

  const deleteSim = useMutation({
    mutationFn: (simId: string) => deleteSimulation(projectId, simId),
    onMutate: async (simId) => {
      await qc.cancelQueries({ queryKey: ["simulations", projectId] });
      const prev = qc.getQueryData(["simulations", projectId]);
      qc.setQueryData(["simulations", projectId], (old: typeof simulations) =>
        old ? old.filter((s) => s.id !== simId) : []
      );
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      qc.setQueryData(["simulations", projectId], ctx?.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["simulations", projectId] }),
  });

  // Conjoint step 3 → 4: create simulation, save sim ID, show design preview
  const createConjointSim = useMutation({
    mutationFn: async () => {
      const sim = await createSimulation(projectId, {
        simulation_type: "conjoint",
        persona_group_ids: groupIds,
        briefing_ids: briefingIds,
        prompt_question: question || "the product",
      });
      dispatch({ type: "SET_CONJOINT_SIM_ID", payload: sim.id });
      return sim;
    },
    onSuccess: () => dispatch({ type: "SET_STEP", payload: 4 }),
  });

  // Survey step 3 → 4: create simulation + upload file, show preview
  const uploadSurvey = useMutation({
    mutationFn: async () => {
      const sim = await createSimulation(projectId, {
        simulation_type: "survey",
        persona_group_ids: groupIds,
        briefing_ids: briefingIds,
      });
      const fd = new FormData();
      fd.append("file", surveyFile!);
      const updated = await uploadSurveyFile(projectId, sim.id, fd);
      return updated;
    },
    onSuccess: (sim) => {
      dispatch({ type: "SET_SURVEY_SIM_ID", payload: sim.id });
      dispatch({ type: "SET_PARSED_QUESTIONS", payload: sim.survey_schema?.questions ?? [] });
      dispatch({ type: "SET_STEP", payload: 4 });
    },
  });

  const run = useMutation({
    mutationFn: async () => {
      if (simType === "survey" && surveySimId) {
        return runSurvey(projectId, surveySimId);
      }

      if (simType === "conjoint" && conjointSimId) {
        return runConjointDesign(projectId, conjointSimId, {
          attributes: conjointAttributes.map(a => ({
            name: a.name,
            levels: a.levels.filter(l => l.trim()),
          })),
          n_tasks: conjointNTasks,
        });
      }

      const body: Parameters<typeof createSimulation>[1] = {
        simulation_type: simType,
        persona_group_ids: groupIds,
        briefing_ids: briefingIds,
      };

      if (simType === "concept_test" || simType === "focus_group") {
        body.prompt_question = question;
      } else if (simType === "idi_ai") {
        body.idi_script_text = scriptMode === "text" ? scriptText : null;
      } else if (simType === "idi_manual") {
        body.idi_persona_id = idiPersonaId;
        if (scriptMode === "text" && scriptText) body.idi_script_text = scriptText;
      }

      const sim = await createSimulation(projectId, body);

      // If file upload selected, upload the script now
      if ((simType === "idi_ai" || simType === "idi_manual") && scriptMode === "file" && scriptFile) {
        const fd = new FormData();
        fd.append("file", scriptFile);
        const { uploadIDIScript } = await import("@/lib/api");
        await uploadIDIScript(projectId, sim.id, fd);
      }

      return sim;
    },
    onSuccess: (sim) => {
      qc.invalidateQueries({ queryKey: ["simulations", projectId] });
      handleClose();
      if (sim.simulation_type === "idi_manual") {
        router.push(`/projects/${projectId}/simulations/${sim.id}/chat`);
      } else {
        router.push(`/projects/${projectId}/simulations/${sim.id}`);
      }
    },
  });

  const handleClose = () => {
    setOpen(false);
    dispatch({ type: "RESET" });
  };

  const totalSteps = simType === "survey" || simType === "conjoint" ? 5 : 4;
  const canProceed = () => {
    if (step === 0) return !!simType;
    if (step === 1) return groupIds.length > 0;
    if (step === 2) return simType !== "concept_test" || briefingIds.length > 0;
    if (step === 3) {
      if (simType === "concept_test") return !!question.trim();
      if (simType === "focus_group") return !!question.trim();
      if (simType === "idi_ai") return scriptMode === "text" ? !!scriptText.trim() : !!scriptFile;
      if (simType === "idi_manual") return !!idiPersonaId;
      if (simType === "survey") return !!surveyFile;
      if (simType === "conjoint") {
        return (
          conjointAttributes.length >= 2 &&
          conjointAttributes.every(
            a => a.name.trim() && a.levels.filter(l => l.trim()).length >= 2
          )
        );
      }
    }
    if (step === 4 && simType === "survey") return parsedQuestions.length > 0;
    if (step === 4 && simType === "conjoint") return !!conjointSimId;
    return false;
  };

  const simTypeLabel = (type: string) => {
    if (type === "idi_ai") return "IDI — AI";
    if (type === "idi_manual") return "IDI — Manual";
    if (type === "survey") return "Survey";
    if (type === "focus_group") return "Focus Group";
    if (type === "conjoint") return "Conjoint Test";
    return "Concept Test";
  };

  return (
    <>
      <div className="flex justify-end mb-5">
        <Button onClick={() => setOpen(true)}><Plus size={14} /> Run Simulation</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[1, 2].map(i => <div key={i} className="h-20 bg-zinc-100 rounded-lg animate-pulse" />)}</div>
      ) : !simulations?.length ? (
        <EmptyState icon={Play} title="No simulations yet" description="Run your first simulation to see how your target personas react." action={<Button onClick={() => setOpen(true)}><Play size={14} /> Run Simulation</Button>} />
      ) : (
        <div className="space-y-3">
          {simulations.map(s => (
            <Card key={s.id} onClick={() => {
              if (s.simulation_type === "idi_manual" && s.status === "active") {
                router.push(`/projects/${projectId}/simulations/${s.id}/chat`);
              } else {
                router.push(`/projects/${projectId}/simulations/${s.id}`);
              }
            }}>
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={statusVariant[s.status] ?? "pending"}>{s.status}</Badge>
                    <Badge variant="default">{simTypeLabel(s.simulation_type)}</Badge>
                    <span className="text-xs text-zinc-400">{formatDate(s.created_at)}</span>
                  </div>
                  <p className="text-sm text-zinc-700 truncate">
                    {s.prompt_question || (s.simulation_type === "idi_manual" ? "Manual interview" : s.simulation_type === "survey" ? "Survey simulation" : s.simulation_type === "focus_group" ? "Focus group session" : s.simulation_type === "conjoint" ? "Conjoint trade-off test" : "IDI — AI assisted")}
                  </p>
                </div>
                <div className="flex items-center gap-1 ml-3 shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmPending({ message: "Delete this simulation and all its results?", action: () => deleteSim.mutate(s.id) });
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

      <ConfirmDialog
        open={confirmPending !== null}
        message={confirmPending?.message ?? ""}
        onConfirm={() => confirmPending?.action()}
        onClose={() => setConfirmPending(null)}
      />
      <Modal open={open} onClose={handleClose} title={`Run Simulation — Step ${step + 1} of ${totalSteps}`} width="max-w-xl" key={simType}>
        <div className="space-y-4">

          {/* Step 0: Choose type */}
          {step === 0 && (
            <div className="space-y-3">
              <p className="text-sm text-zinc-500">What kind of research do you want to run?</p>
              {SIM_TYPES.map(t => (
                <button
                  key={t.id}
                  onClick={() => dispatch({ type: "SET_SIM_TYPE", payload: t.id })}
                  className={`w-full text-left rounded-lg border px-4 py-3 transition-colors ${simType === t.id ? "border-zinc-800 bg-zinc-50" : "border-zinc-200 hover:border-zinc-300"}`}
                >
                  <div className="flex items-center gap-2 mb-1 text-zinc-800">
                    {t.icon}
                    <span className="text-sm font-medium">{t.label}</span>
                  </div>
                  <p className="text-xs text-zinc-500 ml-7">{t.description}</p>
                </button>
              ))}
            </div>
          )}

          {/* Step 1: Persona groups (multi-select) */}
          {step === 1 && (
            <>
              <p className="text-sm text-zinc-500">Select one or more persona groups. Personas from all selected groups will be included in the simulation.</p>
              {groups && groups.filter(g => g.generation_status === "complete").length === 0 ? (
                <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-md">No groups with generated personas yet.</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {groups?.filter(g => g.generation_status === "complete").map(g => {
                    const checked = groupIds.includes(g.id);
                    return (
                      <label key={g.id} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors ${checked ? "border-zinc-800 bg-zinc-50" : "border-zinc-200 hover:border-zinc-300"}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={e => dispatch({ type: "SET_GROUP_IDS", payload: e.target.checked ? [...groupIds, g.id] : groupIds.filter(id => id !== g.id) })}
                          className="shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-zinc-800 font-medium truncate">{g.name}</p>
                          <p className="text-xs text-zinc-400">{g.persona_count} personas</p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
              {groupIds.length > 0 && (
                <p className="text-xs text-zinc-500 bg-zinc-50 px-3 py-2 rounded-md">
                  {groupIds.reduce((sum, id) => sum + (groups?.find(g => g.id === id)?.persona_count ?? 0), 0)} total personas selected across {groupIds.length} group{groupIds.length !== 1 ? "s" : ""}
                </p>
              )}
            </>
          )}

          {/* Step 2: Briefing selection */}
          {step === 2 && (
            <>
              <p className="text-sm text-zinc-500">
                {simType === "concept_test"
                  ? "Select one or more briefing documents to test against. Personas will react to all selected materials."
                  : "Optionally select one or more briefings to give your personas background context."}
              </p>
              {!briefings?.length ? (
                <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-md">No briefings uploaded yet. You can still run the simulation without one.</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {briefings.map(b => {
                    const checked = briefingIds.includes(b.id);
                    return (
                      <label key={b.id} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors ${checked ? "border-zinc-800 bg-zinc-50" : "border-zinc-200 hover:border-zinc-300"}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={e => dispatch({ type: "SET_BRIEFING_IDS", payload: e.target.checked ? [...briefingIds, b.id] : briefingIds.filter(id => id !== b.id) })}
                          className="shrink-0"
                        />
                        <div className="min-w-0">
                          <p className="text-sm text-zinc-800 font-medium truncate">{b.title}</p>
                          {b.description && <p className="text-xs text-zinc-400 truncate">{b.description}</p>}
                        </div>
                        <span className="text-xs text-zinc-400 shrink-0 uppercase">{b.file_type}</span>
                      </label>
                    );
                  })}
                </div>
              )}
              {simType === "concept_test" && briefingIds.length === 0 && (
                <p className="text-xs text-amber-600">Select at least one briefing to run a concept test.</p>
              )}
            </>
          )}

          {/* Step 3: Type-specific config */}
          {step === 3 && simType === "concept_test" && (
            <>
              <p className="text-sm text-zinc-500">What do you want to know? Be specific about what to test.</p>
              <Textarea
                label="Simulation question"
                placeholder="e.g. How would they react to this tagline? Would they trust this brand?"
                rows={4}
                value={question}
                onChange={e => dispatch({ type: "SET_QUESTION", payload: e.target.value })}
              />
            </>
          )}

          {step === 3 && simType === "focus_group" && (
            <>
              <p className="text-sm text-zinc-500">What topic should the group discuss? The moderator will use this to open the session and guide the conversation.</p>
              <Textarea
                label="Discussion topic"
                placeholder="e.g. How do you feel about this new product concept? What would make you try it or not?"
                rows={4}
                value={question}
                onChange={e => dispatch({ type: "SET_QUESTION", payload: e.target.value })}
              />
            </>
          )}

          {step === 3 && (simType === "idi_ai" || simType === "idi_manual") && (
            <>
              <p className="text-sm text-zinc-500">
                {simType === "idi_ai"
                  ? "Provide your interview script. Boses will use these questions to interview each persona."
                  : "Optionally upload your script as a reference during your interview."}
              </p>

              <div className="flex gap-2">
                <button
                  onClick={() => dispatch({ type: "SET_SCRIPT_MODE", payload: "text" })}
                  className={`flex-1 py-1.5 text-xs rounded-md border transition-colors ${scriptMode === "text" ? "border-zinc-800 bg-zinc-50 font-medium" : "border-zinc-200 text-zinc-500 hover:border-zinc-300"}`}
                >
                  Type questions
                </button>
                <button
                  onClick={() => dispatch({ type: "SET_SCRIPT_MODE", payload: "file" })}
                  className={`flex-1 py-1.5 text-xs rounded-md border transition-colors ${scriptMode === "file" ? "border-zinc-800 bg-zinc-50 font-medium" : "border-zinc-200 text-zinc-500 hover:border-zinc-300"}`}
                >
                  Upload script file
                </button>
              </div>

              {scriptMode === "text" && (
                <Textarea
                  label={simType === "idi_ai" ? "Interview questions (one per line)" : "Interview script (optional)"}
                  placeholder={"1. Can you tell me about yourself?\n2. How do you typically discover new products?\n3. What would make you trust a brand like this?"}
                  rows={6}
                  value={scriptText}
                  onChange={e => dispatch({ type: "SET_SCRIPT_TEXT", payload: e.target.value })}
                />
              )}

              {scriptMode === "file" && (
                <div>
                  <p className="text-xs text-zinc-500 mb-2">Accepted formats: .txt, .docx</p>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.docx"
                    className="hidden"
                    onChange={e => dispatch({ type: "SET_SCRIPT_FILE", payload: e.target.files?.[0] ?? null })}
                  />
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="w-full border border-dashed border-zinc-300 rounded-lg py-4 text-sm text-zinc-500 hover:border-zinc-400 transition-colors"
                  >
                    {scriptFile ? `✓ ${scriptFile.name}` : "Click to select a file"}
                  </button>
                </div>
              )}

              {simType === "idi_manual" && (
                <>
                  <Select label="Select persona to interview" value={idiPersonaId} onChange={e => dispatch({ type: "SET_IDI_PERSONA_ID", payload: e.target.value })}>
                    <option value="">Select a persona…</option>
                    {personas?.map(p => (
                      <option key={p.id} value={p.id}>{p.full_name} — {p.age}, {p.occupation}</option>
                    ))}
                  </Select>
                  {!personas?.length && groupIds.length > 0 && (
                    <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-md">No personas in the selected group(s) yet.</p>
                  )}
                </>
              )}
            </>
          )}

          {/* Step 3: Survey — upload form */}
          {step === 3 && simType === "survey" && (
            <>
              <p className="text-sm text-zinc-500">Upload your survey form. Boses will parse the questions automatically.</p>
              <div>
                <p className="text-xs text-zinc-500 mb-2">Accepted formats: .txt, .docx</p>
                <input
                  ref={surveyFileRef}
                  type="file"
                  accept=".txt,.docx"
                  className="hidden"
                  onChange={e => dispatch({ type: "SET_SURVEY_FILE", payload: e.target.files?.[0] ?? null })}
                />
                <button
                  onClick={() => surveyFileRef.current?.click()}
                  className="w-full border border-dashed border-zinc-300 rounded-lg py-4 text-sm text-zinc-500 hover:border-zinc-400 transition-colors"
                >
                  {surveyFile ? `✓ ${surveyFile.name}` : "Click to select a file"}
                </button>
              </div>
            </>
          )}

          {/* Step 3: Conjoint — attribute builder */}
          {step === 3 && simType === "conjoint" && (
            <div className="space-y-4">
              <p className="text-sm text-zinc-500">Define the product attributes and their levels. Personas will make forced trade-off choices between product profiles.</p>

              <Textarea
                label="Product category"
                placeholder="e.g. Wireless over-ear headphones"
                rows={2}
                value={question}
                onChange={e => dispatch({ type: "SET_QUESTION", payload: e.target.value })}
              />

              <div className="space-y-3">
                {conjointAttributes.map((attr, attrIdx) => (
                  <div key={attrIdx} className="border border-zinc-200 rounded-lg p-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <input
                        className="flex-1 text-sm border-b border-zinc-200 bg-transparent focus:outline-none focus:border-zinc-500 py-0.5"
                        placeholder="Attribute name (e.g. Price)"
                        value={attr.name}
                        onChange={e => {
                          const next = [...conjointAttributes];
                          next[attrIdx] = { ...next[attrIdx], name: e.target.value };
                          dispatch({ type: "SET_CONJOINT_ATTRIBUTES", payload: next });
                        }}
                      />
                      {conjointAttributes.length > 2 && (
                        <button
                          onClick={() => dispatch({ type: "SET_CONJOINT_ATTRIBUTES", payload: conjointAttributes.filter((_, i) => i !== attrIdx) })}
                          className="text-xs text-zinc-300 hover:text-red-500 transition-colors shrink-0"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {attr.levels.map((lv, lvIdx) => (
                        <div key={lvIdx} className="flex items-center gap-1 bg-zinc-50 border border-zinc-200 rounded-md px-2 py-0.5">
                          <input
                            className="text-xs bg-transparent w-20 focus:outline-none"
                            value={lv}
                            placeholder="Level…"
                            onChange={e => {
                              const next = [...conjointAttributes];
                              const levels = [...next[attrIdx].levels];
                              levels[lvIdx] = e.target.value;
                              next[attrIdx] = { ...next[attrIdx], levels };
                              dispatch({ type: "SET_CONJOINT_ATTRIBUTES", payload: next });
                            }}
                          />
                          {attr.levels.length > 2 && (
                            <button
                              onClick={() => {
                                const next = [...conjointAttributes];
                                next[attrIdx] = { ...next[attrIdx], levels: next[attrIdx].levels.filter((_, i) => i !== lvIdx) };
                                dispatch({ type: "SET_CONJOINT_ATTRIBUTES", payload: next });
                              }}
                              className="text-zinc-300 hover:text-red-400 text-xs ml-0.5"
                            >×</button>
                          )}
                        </div>
                      ))}
                      <button
                        onClick={() => {
                          const next = [...conjointAttributes];
                          next[attrIdx] = { ...next[attrIdx], levels: [...next[attrIdx].levels, ""] };
                          dispatch({ type: "SET_CONJOINT_ATTRIBUTES", payload: next });
                        }}
                        className="text-xs text-zinc-400 hover:text-zinc-600 px-2 py-0.5 border border-dashed border-zinc-200 rounded-md transition-colors"
                      >
                        + Level
                      </button>
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => dispatch({ type: "SET_CONJOINT_ATTRIBUTES", payload: [...conjointAttributes, { name: "", levels: ["", ""] }] })}
                  className="w-full text-xs text-zinc-400 hover:text-zinc-600 border border-dashed border-zinc-200 rounded-lg py-2 transition-colors"
                >
                  + Add attribute
                </button>
              </div>

              <div className="flex items-center gap-3">
                <label className="text-xs text-zinc-500 shrink-0">Tasks per persona:</label>
                <input
                  type="range" min={6} max={20} step={1}
                  value={conjointNTasks}
                  onChange={e => dispatch({ type: "SET_CONJOINT_N_TASKS", payload: Number(e.target.value) })}
                  className="flex-1"
                />
                <span className="text-xs text-zinc-700 font-medium w-6 text-right">{conjointNTasks}</span>
              </div>
            </div>
          )}

          {/* Step 4: Conjoint — design preview */}
          {step === 4 && simType === "conjoint" && (
            <div className="space-y-4">
              <p className="text-sm text-zinc-500">
                Confirm your conjoint design. Each persona will complete <span className="font-medium text-zinc-800">{conjointNTasks} choice tasks</span> across <span className="font-medium text-zinc-800">{conjointAttributes.length} attributes</span>.
              </p>
              <div className="space-y-2">
                {conjointAttributes.map((attr, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-zinc-400 text-xs w-4 mt-0.5 shrink-0">{i + 1}.</span>
                    <span className="font-medium text-zinc-700 shrink-0">{attr.name}:</span>
                    <span className="text-zinc-500">{attr.levels.filter(l => l.trim()).join(", ")}</span>
                  </div>
                ))}
              </div>
              <div className="text-xs text-zinc-400 bg-zinc-50 rounded-lg px-3 py-2">
                Estimated {conjointNTasks * groupIds.reduce((sum, id) => sum + (groups?.find(g => g.id === id)?.persona_count ?? 0), 0)} total choice observations across all personas.
              </div>
            </div>
          )}

          {/* Step 4: Survey — preview parsed questions */}
          {step === 4 && simType === "survey" && (
            <>
              <p className="text-sm text-zinc-500">
                Boses parsed <span className="font-medium text-zinc-800">{parsedQuestions.length} question{parsedQuestions.length !== 1 ? "s" : ""}</span> from your survey. Review and confirm.
              </p>
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {parsedQuestions.map((q, i) => (
                  <div key={q.id} className="flex items-start gap-2.5 text-sm">
                    <span className="text-xs text-zinc-400 shrink-0 mt-0.5 w-5">{i + 1}.</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-zinc-700">{q.text}</span>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${
                      q.type === "likert" ? "bg-blue-50 text-blue-600" :
                      q.type === "multiple_choice" ? "bg-purple-50 text-purple-600" :
                      "bg-zinc-100 text-zinc-500"
                    }`}>
                      {q.type === "multiple_choice" ? "choice" : q.type}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Run error */}
          {run.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">
              {(run.error as Error).message}
            </div>
          )}

          {/* Nav */}
          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => { if (step === 0) handleClose(); else dispatch({ type: "SET_STEP", payload: step - 1 }); }}>
              {step === 0 ? "Cancel" : "Back"}
            </Button>
            {/* Survey step 3: "Next" uploads + parses */}
            {step === 3 && simType === "survey" ? (
              <Button onClick={() => uploadSurvey.mutate()} disabled={!canProceed() || uploadSurvey.isPending}>
                {uploadSurvey.isPending ? "Parsing…" : "Next"}
              </Button>
            ) : step === 3 && simType === "conjoint" ? (
              <Button onClick={() => createConjointSim.mutate()} disabled={!canProceed() || createConjointSim.isPending}>
                {createConjointSim.isPending ? "Saving…" : "Next"}
              </Button>
            ) : step < totalSteps - 1 ? (
              <Button onClick={() => dispatch({ type: "SET_STEP", payload: step + 1 })} disabled={!canProceed()}>
                Next
              </Button>
            ) : (
              <Button onClick={() => run.mutate()} disabled={!canProceed() || run.isPending}>
                {run.isPending ? "Starting…" : simType === "idi_manual" ? "Start Interview" : "Run Simulation"}
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  );
}
