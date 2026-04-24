"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Target, CheckCircle2, Clock } from "lucide-react";
import {
  getPredictionCommitment,
  createPredictionCommitment,
  updatePredictionCommitment,
} from "@/lib/api";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";

interface Props {
  projectId: string;
  simulationId: string;
  predictedSentiment?: string | null;
  predictedThemes?: string[] | null;
}

function formatDueDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

export default function PredictionCommitmentPanel({
  projectId,
  simulationId,
  predictedSentiment,
  predictedThemes,
}: Props) {
  const qc = useQueryClient();
  const [kpi, setKpi] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [showOutcomeForm, setShowOutcomeForm] = useState(false);
  const [outcomeText, setOutcomeText] = useState("");
  const [directionalMatch, setDirectionalMatch] = useState<boolean | null>(null);
  const [notes, setNotes] = useState("");

  const { data: commitment, isLoading } = useQuery({
    queryKey: ["prediction-commitment", simulationId],
    queryFn: () => getPredictionCommitment(projectId, simulationId),
  });

  const create = useMutation({
    mutationFn: () =>
      createPredictionCommitment(projectId, simulationId, {
        kpi_description: kpi.trim(),
        outcome_due_date: new Date(dueDate).toISOString(),
        predicted_sentiment: predictedSentiment ?? null,
        predicted_themes: predictedThemes ?? null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prediction-commitment", simulationId] }),
  });

  const update = useMutation({
    mutationFn: () =>
      updatePredictionCommitment(projectId, simulationId, {
        actual_outcome_description: outcomeText.trim(),
        directional_match: directionalMatch ?? undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prediction-commitment", simulationId] });
      setShowOutcomeForm(false);
    },
  });

  const header = (
    <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
      <Target size={14} /> Track Real-World Outcome
    </h3>
  );

  if (isLoading) return null;

  // ── No commitment yet ─────────────────────────────────────────────────────
  if (!commitment) {
    const canSubmit = kpi.trim().length > 0 && dueDate.length > 0 && !create.isPending;
    return (
      <Card className="space-y-3">
        {header}
        <p className="text-xs text-zinc-500">
          Planning to launch based on these findings? Log a commitment — we'll remind you to report back and help build our predictive validity dataset.
        </p>
        <div className="space-y-2">
          <div>
            <label className="text-[11px] font-medium text-zinc-500 block mb-1">
              What KPI will you track?
            </label>
            <textarea
              rows={2}
              value={kpi}
              onChange={(e) => setKpi(e.target.value)}
              placeholder="e.g. Trial rate at 3 months, NPS at 6 months, week-1 sales vs. forecast…"
              className="w-full text-xs border border-zinc-200 rounded-lg px-3 py-2 text-zinc-700 placeholder:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-zinc-400 resize-none"
            />
          </div>
          <div>
            <label className="text-[11px] font-medium text-zinc-500 block mb-1">
              When will you report back?
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="text-xs border border-zinc-200 rounded-lg px-3 py-2 text-zinc-700 focus:outline-none focus:ring-1 focus:ring-zinc-400"
            />
          </div>
        </div>
        <button
          onClick={() => create.mutate()}
          disabled={!canSubmit}
          className="flex items-center gap-1.5 text-xs font-medium bg-zinc-900 text-white px-3 py-1.5 rounded-lg hover:bg-zinc-700 disabled:opacity-40 transition-colors"
        >
          {create.isPending ? <Spinner className="h-3 w-3 border-zinc-400 border-t-white" /> : <Target size={12} />}
          {create.isPending ? "Saving…" : "Log commitment"}
        </button>
        {create.isError && (
          <p className="text-xs text-red-500">Something went wrong — please try again.</p>
        )}
      </Card>
    );
  }

  // ── Commitment exists, outcome not yet reported ────────────────────────────
  if (commitment.status === "pending") {
    return (
      <Card className="space-y-3">
        {header}
        <div className="flex items-start gap-2 text-xs text-zinc-500">
          <Clock size={13} className="text-amber-500 mt-0.5 shrink-0" />
          <div className="space-y-0.5">
            <p className="font-medium text-zinc-700">{commitment.kpi_description}</p>
            <p>Outcome due by {formatDueDate(commitment.outcome_due_date)}</p>
          </div>
        </div>

        {!showOutcomeForm ? (
          <button
            onClick={() => setShowOutcomeForm(true)}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
          >
            Report outcome now →
          </button>
        ) : (
          <div className="space-y-2 border-t border-zinc-100 pt-3">
            <p className="text-[11px] font-medium text-zinc-500">Did the real-world result match the simulation direction?</p>
            <div className="flex gap-2">
              {[{ label: "Yes, it matched", value: true }, { label: "No, it didn't", value: false }].map(({ label, value }) => (
                <button
                  key={String(value)}
                  onClick={() => setDirectionalMatch(value)}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                    directionalMatch === value
                      ? "bg-zinc-900 text-white border-zinc-900"
                      : "border-zinc-200 text-zinc-600 hover:border-zinc-400"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <textarea
              rows={2}
              value={outcomeText}
              onChange={(e) => setOutcomeText(e.target.value)}
              placeholder="Describe what actually happened…"
              className="w-full text-xs border border-zinc-200 rounded-lg px-3 py-2 text-zinc-700 placeholder:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-zinc-400 resize-none"
            />
            <textarea
              rows={1}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any notes or context? (optional)"
              className="w-full text-xs border border-zinc-200 rounded-lg px-3 py-2 text-zinc-700 placeholder:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-zinc-400 resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={() => update.mutate()}
                disabled={!outcomeText.trim() || directionalMatch === null || update.isPending}
                className="flex items-center gap-1.5 text-xs font-medium bg-zinc-900 text-white px-3 py-1.5 rounded-lg hover:bg-zinc-700 disabled:opacity-40 transition-colors"
              >
                {update.isPending ? <Spinner className="h-3 w-3 border-zinc-400 border-t-white" /> : null}
                {update.isPending ? "Saving…" : "Submit outcome"}
              </button>
              <button
                onClick={() => setShowOutcomeForm(false)}
                className="text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </Card>
    );
  }

  // ── Outcome received ──────────────────────────────────────────────────────
  return (
    <Card className="space-y-3">
      {header}
      <div className="flex items-start gap-2 text-xs">
        <CheckCircle2 size={13} className="text-emerald-500 mt-0.5 shrink-0" />
        <div className="space-y-1">
          <p className="font-medium text-zinc-700">Outcome recorded</p>
          <p className="text-zinc-500">{commitment.actual_outcome_description}</p>
          {commitment.directional_match !== null && (
            <p className={commitment.directional_match ? "text-emerald-600" : "text-red-500"}>
              {commitment.directional_match
                ? "✓ Directional match — simulation predicted correctly"
                : "✗ No directional match — simulation diverged from reality"}
            </p>
          )}
          {commitment.notes && (
            <p className="text-zinc-400 italic">{commitment.notes}</p>
          )}
        </div>
      </div>
    </Card>
  );
}
