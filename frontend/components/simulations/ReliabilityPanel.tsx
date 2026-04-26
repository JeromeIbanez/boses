"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, RefreshCw, X } from "lucide-react";
import { getReliabilityCheck, createReliabilityCheck } from "@/lib/api";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";

function ScienceExplainer({ onClose }: { onClose: () => void }) {
  return (
    <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-3 text-xs text-zinc-600 space-y-2 relative">
      <button onClick={onClose} className="absolute top-2 right-2 text-zinc-400 hover:text-zinc-600">
        <X size={12} />
      </button>
      <p className="font-medium text-zinc-700">How this works</p>
      <p>We re-run your simulation multiple times with identical settings and measure consistency across runs using three signals:</p>
      <ul className="space-y-1.5 list-none">
        <li><span className="font-medium text-zinc-700">Sentiment agreement (40%)</span> — do the runs agree on whether the reaction is positive, neutral, or negative?</li>
        <li><span className="font-medium text-zinc-700">Distribution consistency (35%)</span> — how similar are the full sentiment distributions across runs? (measured using Jensen-Shannon divergence)</li>
        <li><span className="font-medium text-zinc-700">Theme stability (25%)</span> — which themes appear in most runs vs. only once?</li>
      </ul>
      <p className="text-zinc-400">A high score means your results are stable. A low score means the model is sensitive to randomness and you should interpret results with caution.</p>
    </div>
  );
}

interface Props {
  projectId: string;
  simulationId: string;
}

function confidenceLabel(pct: number): { text: string; color: string } {
  if (pct >= 80) return {
    text: "Results are highly stable across independent runs.",
    color: "text-emerald-600",
  };
  if (pct >= 60) return {
    text: "Core findings are consistent; specific percentages may vary ±10%.",
    color: "text-amber-600",
  };
  if (pct >= 40) return {
    text: "Notable variation between runs. Treat themes as directional only.",
    color: "text-orange-600",
  };
  return {
    text: "High variability. Findings are unreliable — consider a larger persona group.",
    color: "text-red-600",
  };
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "text-emerald-700" : pct >= 60 ? "text-amber-600" : pct >= 40 ? "text-orange-600" : "text-red-500";
  return (
    <span className={`text-2xl font-bold ${color}`}>{pct}%</span>
  );
}

function ScoreRow({ label, value, positiveHigh = true }: { label: string; value: number | null | undefined; positiveHigh?: boolean }) {
  if (value === null || value === undefined) return null;
  const pct = Math.round(value * 100);
  const good = positiveHigh ? pct >= 75 : pct <= 25;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={good ? "text-emerald-500" : "text-zinc-400"}>
        {good ? "✓" : "~"}
      </span>
      <span className="text-zinc-500 flex-1">{label}</span>
      <div className="w-24 bg-zinc-100 rounded-full h-1.5 overflow-hidden">
        <div className="bg-zinc-600 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-zinc-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function ReliabilityPanel({ projectId, simulationId }: Props) {
  const qc = useQueryClient();
  const [showExplainer, setShowExplainer] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["reliability", simulationId],
    queryFn: () => getReliabilityCheck(projectId, simulationId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "running" || status === "pending" ? 5000 : false;
    },
  });

  const create = useMutation({
    mutationFn: (nRuns: number) => createReliabilityCheck(projectId, simulationId, nRuns),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reliability", simulationId] }),
  });

  const header = (rightSlot?: React.ReactNode) => (
    <div className="flex items-center justify-between">
      <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
        <ShieldCheck size={14} /> Reliability Check
        <button
          onClick={() => setShowExplainer(v => !v)}
          className="text-[10px] font-medium text-zinc-400 hover:text-zinc-600 border border-zinc-200 rounded-full w-4 h-4 flex items-center justify-center leading-none transition-colors"
          title="How does this work?"
        >
          ?
        </button>
      </h3>
      {rightSlot}
    </div>
  );

  if (isLoading) return null;

  // No study yet
  if (!data?.exists) {
    return (
      <Card className="space-y-3">
        {header()}
        {showExplainer && <ScienceExplainer onClose={() => setShowExplainer(false)} />}
        <p className="text-xs text-zinc-500">
          Not sure how stable these results are? Run this simulation 2 more times automatically and get a confidence score.
        </p>
        <button
          onClick={() => create.mutate(3)}
          disabled={create.isPending}
          className="flex items-center gap-1.5 text-xs font-medium bg-zinc-900 text-white px-3 py-1.5 rounded-lg hover:bg-zinc-700 disabled:opacity-50 transition-colors"
        >
          {create.isPending ? <Spinner className="h-3 w-3 border-zinc-400 border-t-white" /> : <RefreshCw size={12} />}
          {create.isPending ? "Starting…" : "Check reliability (3 runs)"}
        </button>
      </Card>
    );
  }

  // Study running
  if (data.status === "running" || data.status === "pending") {
    return (
      <Card className="space-y-3">
        {header()}
        {showExplainer && <ScienceExplainer onClose={() => setShowExplainer(false)} />}
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <Spinner className="h-3 w-3 border-zinc-200 border-t-zinc-600" />
          Running {data.n_runs} simulations to assess consistency…
        </div>
      </Card>
    );
  }

  // Study complete (or failed)
  return (
    <Card className="space-y-4">
      {header(data.confidence_score != null ? <ConfidenceBadge score={data.confidence_score} /> : undefined)}
      {showExplainer && <ScienceExplainer onClose={() => setShowExplainer(false)} />}

      {data.confidence_score != null ? (
        <>
          {(() => {
            const pct = Math.round(data.confidence_score! * 100);
            const { text, color } = confidenceLabel(pct);
            return (
              <p className={`text-xs font-medium ${color}`}>{text}</p>
            );
          })()}
          <p className="text-xs text-zinc-400">
            Based on {data.n_runs} independent repeat runs.
          </p>

          <div className="space-y-2">
            <ScoreRow label="Sentiment agreement" value={data.sentiment_agreement_rate} />
            <ScoreRow label="Distribution consistency" value={data.distribution_variance_score} />
            <ScoreRow label="Theme stability" value={data.theme_overlap_coefficient} />
          </div>

          <div className="pt-1">
            <button
              onClick={() => create.mutate(3)}
              disabled={create.isPending}
              className="text-xs text-zinc-400 hover:text-zinc-600 transition-colors flex items-center gap-1"
            >
              <RefreshCw size={11} /> Re-run check
            </button>
          </div>
        </>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-red-500">Reliability check failed — not enough runs completed.</p>
          <button
            onClick={() => create.mutate(3)}
            disabled={create.isPending}
            className="flex items-center gap-1.5 text-xs font-medium bg-zinc-900 text-white px-3 py-1.5 rounded-lg hover:bg-zinc-700 disabled:opacity-50 transition-colors"
          >
            {create.isPending ? <Spinner className="h-3 w-3 border-zinc-400 border-t-white" /> : <RefreshCw size={12} />}
            {create.isPending ? "Starting…" : "Try again"}
          </button>
        </div>
      )}
    </Card>
  );
}
