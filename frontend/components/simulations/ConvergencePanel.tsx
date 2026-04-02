"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, GitMerge } from "lucide-react";
import { getConvergence } from "@/lib/api";
import type { ConvergencePair } from "@/types";
import Card from "@/components/ui/Card";

interface Props {
  projectId: string;
  personaGroupId: string;
  briefingId?: string | null;
}

const SIM_TYPE_LABELS: Record<string, string> = {
  concept_test: "Concept Test",
  focus_group: "Focus Group",
  idi_ai: "IDI — AI",
  idi_manual: "IDI — Manual",
  survey: "Survey",
  conjoint: "Conjoint",
};

const INTERPRETATION_STYLES: Record<string, { bar: string; label: string; text: string }> = {
  strong:   { bar: "bg-emerald-400", label: "Strong convergence", text: "text-emerald-700" },
  moderate: { bar: "bg-amber-400",   label: "Moderate convergence", text: "text-amber-700" },
  weak:     { bar: "bg-red-400",     label: "Weak convergence", text: "text-red-700" },
};

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-zinc-100 rounded-full h-1.5 overflow-hidden">
        <div className="bg-zinc-700 h-1.5 rounded-full" style={{ width: `${Math.round(score * 100)}%` }} />
      </div>
      <span className="text-xs text-zinc-500 w-8 text-right">{Math.round(score * 100)}%</span>
    </div>
  );
}

function PairCard({ pair }: { pair: ConvergencePair }) {
  return (
    <div className="border border-zinc-100 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-zinc-700">
          {SIM_TYPE_LABELS[pair.sim_a_type] ?? pair.sim_a_type}
          {" · "}
          {SIM_TYPE_LABELS[pair.sim_b_type] ?? pair.sim_b_type}
        </p>
        <span className={`text-xs font-semibold ${pair.convergence_score >= 0.75 ? "text-emerald-600" : pair.convergence_score >= 0.5 ? "text-amber-600" : "text-red-500"}`}>
          {Math.round(pair.convergence_score * 100)}%
        </span>
      </div>

      <div className="space-y-1">
        {pair.direction_match !== null && (
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className={pair.direction_match ? "text-emerald-500" : "text-red-400"}>
              {pair.direction_match ? "✓" : "✗"}
            </span>
            Dominant sentiment {pair.direction_match ? "agrees" : "disagrees"}
          </div>
        )}
        {pair.distribution_similarity !== null && (
          <div className="space-y-0.5">
            <p className="text-xs text-zinc-400">Distribution similarity</p>
            <ScoreBar score={pair.distribution_similarity} />
          </div>
        )}
        <div className="space-y-0.5">
          <p className="text-xs text-zinc-400">Theme overlap</p>
          <ScoreBar score={pair.theme_overlap} />
        </div>
      </div>

      {pair.shared_themes.length > 0 && (
        <div>
          <p className="text-xs text-zinc-400 mb-1">Shared themes</p>
          <div className="flex flex-wrap gap-1">
            {pair.shared_themes.map(t => (
              <span key={t} className="text-xs bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded-full border border-emerald-100">{t}</span>
            ))}
          </div>
        </div>
      )}

      {pair.diverging_themes.length > 0 && (
        <div>
          <p className="text-xs text-zinc-400 mb-1">Diverging themes</p>
          <div className="flex flex-wrap gap-1">
            {pair.diverging_themes.map(t => (
              <span key={t} className="text-xs bg-zinc-50 text-zinc-500 px-1.5 py-0.5 rounded-full border border-zinc-100">{t}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ConvergencePanel({ projectId, personaGroupId, briefingId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["convergence", projectId, personaGroupId, briefingId],
    queryFn: () => getConvergence(projectId, personaGroupId, briefingId),
    staleTime: 60_000,
  });

  if (isLoading) return null;
  if (!data || !data.overall_convergence_score) return null;
  if (data.pairwise_convergence.length === 0) return null;

  const style = INTERPRETATION_STYLES[data.interpretation ?? "moderate"] ?? INTERPRETATION_STYLES.moderate;

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
          <GitMerge size={14} /> Cross-Simulation Convergence
        </h3>
        <span className={`text-sm font-bold ${style.text}`}>
          {Math.round(data.overall_convergence_score * 100)}%
        </span>
      </div>

      <div>
        <div className="flex-1 bg-zinc-100 rounded-full h-2 overflow-hidden mb-1">
          <div className={`${style.bar} h-2 rounded-full`} style={{ width: `${Math.round(data.overall_convergence_score * 100)}%` }} />
        </div>
        <p className={`text-xs ${style.text}`}>
          {style.label} across {data.simulations_analysed.length} simulations
        </p>
      </div>

      {data.pairwise_convergence.length > 0 && (
        <div className="space-y-2">
          {data.pairwise_convergence.map((pair, i) => (
            <PairCard key={i} pair={pair} />
          ))}
        </div>
      )}

      <p className="text-xs text-zinc-400">
        Convergence measures how consistently multiple simulation types on the same brief reach the same conclusions.
      </p>
    </Card>
  );
}
