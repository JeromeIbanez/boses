"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, TrendingUp, MessageSquare, Lightbulb } from "lucide-react";
import { getSimulation, getSimulationResults } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import PageHeader from "@/components/layout/PageHeader";
import { formatDate } from "@/lib/utils";
import type { SimulationResult } from "@/types";

function SentimentBar({ distribution }: { distribution: Record<string, number> }) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  const segments = [
    { label: "Positive", color: "bg-emerald-400", count: distribution["Positive"] || 0 },
    { label: "Neutral", color: "bg-zinc-300", count: distribution["Neutral"] || 0 },
    { label: "Negative", color: "bg-red-400", count: distribution["Negative"] || 0 },
  ];

  return (
    <div>
      <div className="flex rounded-full overflow-hidden h-2.5 mb-3">
        {segments.map(({ label, color, count }) =>
          count > 0 ? (
            <div key={label} className={`${color}`} style={{ width: `${(count / total) * 100}%` }} title={`${label}: ${count}`} />
          ) : null
        )}
      </div>
      <div className="flex gap-4">
        {segments.map(({ label, color, count }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${color}`} />
            <span className="text-xs text-zinc-600">{label}: <span className="font-medium">{count}</span></span>
          </div>
        ))}
      </div>
    </div>
  );
}

function IndividualResultCard({ result, personas }: { result: SimulationResult; personas: Record<string, string> }) {
  const sentimentColors = {
    Positive: "bg-emerald-50 border-emerald-100 text-emerald-700",
    Neutral: "bg-zinc-50 border-zinc-100 text-zinc-600",
    Negative: "bg-red-50 border-red-100 text-red-700",
  };
  const variant = result.sentiment ? (result.sentiment as keyof typeof sentimentColors) : "Neutral";
  const name = result.persona_id ? (personas[result.persona_id] || "Persona") : "Persona";

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-medium shrink-0">
            {name.charAt(0)}
          </div>
          <span className="text-sm font-medium text-zinc-900">{name}</span>
        </div>
        {result.sentiment && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${sentimentColors[variant]}`}>
            {result.sentiment}
          </span>
        )}
      </div>

      {result.reaction_text && (
        <p className="text-sm text-zinc-700 leading-relaxed">{result.reaction_text}</p>
      )}

      {result.notable_quote && (
        <blockquote className="border-l-2 border-zinc-200 pl-3 text-sm text-zinc-500 italic">
          "{result.notable_quote}"
        </blockquote>
      )}

      {result.key_themes && result.key_themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {result.key_themes.map(t => (
            <Badge key={t} variant="default">{t}</Badge>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function SimulationResultsPage() {
  const { projectId, simulationId } = useParams<{ projectId: string; simulationId: string }>();
  const router = useRouter();

  const { data: simulation } = useQuery({
    queryKey: ["simulation", simulationId],
    queryFn: () => getSimulation(projectId, simulationId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "pending" || status === "running" ? 3000 : false;
    },
  });

  const { data: results } = useQuery({
    queryKey: ["simulation-results", simulationId],
    queryFn: () => getSimulationResults(projectId, simulationId),
    enabled: simulation?.status === "complete",
    refetchInterval: simulation?.status === "complete" ? false : 3000,
  });

  const aggregate = results?.find(r => r.result_type === "aggregate");
  const individual = results?.filter(r => r.result_type === "individual") ?? [];

  // Build a quick persona_id → name lookup from results (not available without another query)
  // We'll use the order: Persona 1, Persona 2, etc. for MVP
  const personaNames: Record<string, string> = {};
  individual.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  const isRunning = simulation?.status === "pending" || simulation?.status === "running";
  const isFailed = simulation?.status === "failed";

  return (
    <div className="px-8 py-8">
      <button
        onClick={() => router.push(`/projects/${projectId}`)}
        className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 mb-5 transition-colors"
      >
        <ArrowLeft size={13} /> Back to Project
      </button>

      <div className="mb-7">
        <div className="flex items-center gap-2 mb-2">
          <h1 className="text-xl font-semibold text-zinc-900">Simulation Results</h1>
          {simulation && (
            <Badge variant={
              simulation.status === "complete" ? "success" :
              simulation.status === "failed" ? "error" :
              "warning"
            }>{simulation.status}</Badge>
          )}
        </div>
        {simulation && (
          <p className="text-sm text-zinc-500">
            {formatDate(simulation.created_at)} · {simulation.prompt_question}
          </p>
        )}
      </div>

      {/* Running state */}
      {isRunning && (
        <div className="flex flex-col items-center justify-center py-20">
          <Spinner className="h-8 w-8 border-zinc-200 border-t-zinc-700 mb-5" />
          <p className="text-sm font-medium text-zinc-800">Running simulation…</p>
          <p className="text-xs text-zinc-400 mt-1">Each persona is being interviewed by AI. This takes 30–90 seconds.</p>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <Card className="border-red-200 bg-red-50">
          <p className="text-sm font-medium text-red-700 mb-1">Simulation failed</p>
          {simulation?.error_message && <p className="text-xs text-red-600">{simulation.error_message}</p>}
        </Card>
      )}

      {/* Results */}
      {simulation?.status === "complete" && results && (
        <div className="space-y-8">
          {/* Aggregate Summary */}
          {aggregate && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
                <TrendingUp size={14} /> Aggregate Summary
              </h2>
              <Card className="space-y-5">
                {aggregate.sentiment_distribution && (
                  <div>
                    <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-3">Sentiment Breakdown</p>
                    <SentimentBar distribution={aggregate.sentiment_distribution} />
                  </div>
                )}

                {aggregate.top_themes && aggregate.top_themes.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Top Themes</p>
                    <div className="flex flex-wrap gap-2">
                      {aggregate.top_themes.map(t => (
                        <Badge key={t} variant="info">{t}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {aggregate.summary_text && (
                  <div>
                    <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5"><MessageSquare size={12} /> Summary</p>
                    <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggregate.summary_text}</p>
                  </div>
                )}

                {aggregate.recommendations && (
                  <div className="bg-zinc-50 rounded-lg p-4">
                    <p className="text-xs font-medium text-zinc-600 uppercase tracking-wide mb-2 flex items-center gap-1.5"><Lightbulb size={12} /> Strategic Recommendations</p>
                    <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggregate.recommendations}</p>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Individual Results */}
          {individual.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
                <MessageSquare size={14} /> Individual Reactions ({individual.length})
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {individual.map(r => (
                  <IndividualResultCard key={r.id} result={r} personas={personaNames} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
