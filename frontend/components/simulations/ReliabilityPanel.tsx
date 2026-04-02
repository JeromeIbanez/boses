"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { getReliabilityCheck, createReliabilityCheck } from "@/lib/api";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";

interface Props {
  projectId: string;
  simulationId: string;
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "text-emerald-700" : pct >= 60 ? "text-amber-600" : "text-red-500";
  const bg = pct >= 80 ? "bg-emerald-50 border-emerald-100" : pct >= 60 ? "bg-amber-50 border-amber-100" : "bg-red-50 border-red-100";
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

  if (isLoading) return null;

  // No study yet
  if (!data?.exists) {
    return (
      <Card className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
          <ShieldCheck size={14} /> Reliability Check
        </h3>
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
        <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
          <ShieldCheck size={14} /> Reliability Check
        </h3>
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
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
          <ShieldCheck size={14} /> Reliability Check
        </h3>
        {data.confidence_score != null && <ConfidenceBadge score={data.confidence_score} />}
      </div>

      {data.confidence_score != null ? (
        <>
          <p className="text-xs text-zinc-500">
            Confidence score based on {data.n_runs} repeat runs.
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
        <p className="text-xs text-red-500">Reliability check failed — not enough runs completed.</p>
      )}
    </Card>
  );
}
