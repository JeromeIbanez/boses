"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getSharedSimulation } from "@/lib/api";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import Badge from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { SimulationResult } from "@/types";

// ---------------------------------------------------------------------------
// Helpers (duplicated from results page to keep the share page self-contained)
// ---------------------------------------------------------------------------

const SENTIMENT_PILL: Record<string, string> = {
  Positive: "bg-emerald-50 border-emerald-100 text-emerald-700",
  Neutral: "bg-zinc-50 border-zinc-100 text-zinc-600",
  Negative: "bg-red-50 border-red-100 text-red-700",
};

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
            <div key={label} className={color} style={{ width: `${(count / total) * 100}%` }} title={`${label}: ${count}`} />
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

function IndividualCard({ result, index }: { result: SimulationResult; index: number }) {
  const variant = (result.sentiment ?? "Neutral") as keyof typeof SENTIMENT_PILL;
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-medium shrink-0">
            {index + 1}
          </div>
          <span className="text-sm font-medium text-zinc-900">Persona {index + 1}</span>
        </div>
        {result.sentiment && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${SENTIMENT_PILL[variant]}`}>
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
          {result.key_themes.map((t) => (
            <span key={t} className="text-xs bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full">{t}</span>
          ))}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SharedSimulationPage() {
  const { token } = useParams<{ token: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["share", token],
    queryFn: () => getSharedSimulation(token),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <Spinner className="h-7 w-7 border-zinc-200 border-t-zinc-700" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-zinc-50 flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="text-base font-medium text-zinc-800">Link not found</p>
        <p className="text-sm text-zinc-500">This share link may have expired or been revoked.</p>
        <a href="https://app.temujintechnologies.com" className="text-sm text-zinc-500 underline mt-2">Go to Boses</a>
      </div>
    );
  }

  const simTypeLabel: Record<string, string> = {
    concept_test: "Concept Test",
    focus_group: "Focus Group",
    idi_ai: "IDI — AI Assisted",
    idi_manual: "IDI — Manual",
    survey: "Survey",
    conjoint: "Conjoint Analysis",
  };

  const aggregate = data.results.find(r => r.result_type === "aggregate");
  const individual = data.results.filter(r => r.result_type === "individual");

  return (
    <div className="min-h-screen bg-zinc-50">
      {/* Header */}
      <div className="bg-white border-b border-zinc-100 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-zinc-900">Boses</span>
          <span className="text-zinc-200">|</span>
          <span className="text-sm text-zinc-500">{data.project_name}</span>
        </div>
        <a
          href="https://app.temujintechnologies.com"
          className="text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
        >
          Try Boses →
        </a>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="mb-7">
          <div className="flex items-center gap-2 mb-2">
            <h1 className="text-xl font-semibold text-zinc-900">Simulation Results</h1>
            <Badge variant="success">complete</Badge>
            <Badge variant="default">{simTypeLabel[data.simulation_type] ?? data.simulation_type}</Badge>
          </div>
          <p className="text-sm text-zinc-500">
            {formatDate(data.created_at)}
            {data.prompt_question && <> · {data.prompt_question}</>}
          </p>
        </div>

        {/* Aggregate summary */}
        {aggregate && (
          <Card className="mb-6 flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-zinc-900">Summary</h2>
            {aggregate.sentiment_distribution && Object.keys(aggregate.sentiment_distribution).length > 0 && (
              <SentimentBar distribution={aggregate.sentiment_distribution} />
            )}
            {aggregate.summary_text && (
              <p className="text-sm text-zinc-700 leading-relaxed">{aggregate.summary_text}</p>
            )}
            {aggregate.top_themes && aggregate.top_themes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 mb-2">Top themes</p>
                <div className="flex flex-wrap gap-1.5">
                  {aggregate.top_themes.map((t) => (
                    <span key={t} className="text-xs bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {aggregate.recommendations && (
              <div>
                <p className="text-xs font-medium text-zinc-500 mb-1.5">Recommendations</p>
                <p className="text-sm text-zinc-700 leading-relaxed">{aggregate.recommendations}</p>
              </div>
            )}
          </Card>
        )}

        {/* Individual results */}
        {individual.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-zinc-900 mb-3">Individual responses</h2>
            <div className="flex flex-col gap-3">
              {individual.map((r, i) => (
                <IndividualCard key={r.id} result={r} index={i} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="max-w-3xl mx-auto px-6 pb-12 pt-4">
        <p className="text-xs text-zinc-400 text-center">
          Powered by{" "}
          <a href="https://app.temujintechnologies.com" className="underline hover:text-zinc-600">Boses</a>
          {" "}— AI-powered market simulation for Southeast Asia
        </p>
      </div>
    </div>
  );
}
