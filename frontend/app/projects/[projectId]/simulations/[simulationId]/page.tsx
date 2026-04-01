"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, TrendingUp, MessageSquare, Lightbulb, ChevronDown, ChevronUp, Users, Video } from "lucide-react";
import { getSimulation, getSimulationResults } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";
import type { SimulationResult } from "@/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

const SENTIMENT_PILL: Record<string, string> = {
  Positive: "bg-emerald-50 border-emerald-100 text-emerald-700",
  Neutral: "bg-zinc-50 border-zinc-100 text-zinc-600",
  Negative: "bg-red-50 border-red-100 text-red-700",
};

// ---------------------------------------------------------------------------
// Concept-test individual card (unchanged)
// ---------------------------------------------------------------------------

function ConceptIndividualCard({ result, personas }: { result: SimulationResult; personas: Record<string, string> }) {
  const variant = result.sentiment ? (result.sentiment as keyof typeof SENTIMENT_PILL) : "Neutral";
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
          {result.key_themes.map(t => (
            <Badge key={t} variant="default">{t}</Badge>
          ))}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// IDI per-persona card
// ---------------------------------------------------------------------------

function IDIPersonaCard({ result, name }: { result: SimulationResult; name: string }) {
  const [showTranscript, setShowTranscript] = useState(false);
  const variant = result.sentiment ?? "Neutral";
  const sections = result.report_sections as { summary?: string; notable_quotes?: string[] } | null;

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
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${SENTIMENT_PILL[variant as keyof typeof SENTIMENT_PILL] ?? SENTIMENT_PILL["Neutral"]}`}>
            {result.sentiment}
          </span>
        )}
      </div>

      {sections?.summary && (
        <p className="text-sm text-zinc-700 leading-relaxed">{sections.summary}</p>
      )}

      {sections?.notable_quotes && sections.notable_quotes.length > 0 && (
        <div className="space-y-2">
          {sections.notable_quotes.map((q, i) => (
            <blockquote key={i} className="border-l-2 border-zinc-200 pl-3 text-sm text-zinc-500 italic">
              {q}
            </blockquote>
          ))}
        </div>
      )}

      {result.key_themes && result.key_themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {result.key_themes.map(t => (
            <Badge key={t} variant="default">{t}</Badge>
          ))}
        </div>
      )}

      {result.transcript && (
        <div>
          <button
            onClick={() => setShowTranscript(v => !v)}
            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
          >
            {showTranscript ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showTranscript ? "Hide transcript" : "View full transcript"}
          </button>
          {showTranscript && (
            <pre className="mt-3 text-xs text-zinc-600 leading-relaxed whitespace-pre-wrap bg-zinc-50 rounded-lg p-4 font-sans">
              {result.transcript}
            </pre>
          )}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// IDI report view
// ---------------------------------------------------------------------------

function IDIReportView({ results }: { results: SimulationResult[] }) {
  const aggregate = results.find(r => r.result_type === "idi_aggregate");
  const individuals = results.filter(r => r.result_type === "idi_individual");

  const aggSections = aggregate?.report_sections as {
    executive_summary?: string;
    cross_persona_themes?: string[];
    per_persona_highlights?: string[];
    recommendations?: string;
  } | null;

  // Build persona name map: index → "Persona N"
  const personaNames: Record<string, string> = {};
  individuals.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  return (
    <div className="space-y-8">
      {/* Executive Summary */}
      {aggregate && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <TrendingUp size={14} /> Executive Summary
          </h2>
          <Card className="space-y-5">
            {aggregate.top_themes && aggregate.top_themes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Key Themes</p>
                <div className="flex flex-wrap gap-2">
                  {aggregate.top_themes.map(t => (
                    <Badge key={t} variant="info">{t}</Badge>
                  ))}
                </div>
              </div>
            )}

            {(aggSections?.executive_summary || aggregate.summary_text) && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <MessageSquare size={12} /> Summary
                </p>
                <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">
                  {aggSections?.executive_summary || aggregate.summary_text}
                </p>
              </div>
            )}

            {aggSections?.cross_persona_themes && aggSections.cross_persona_themes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Users size={12} /> Cross-Persona Themes
                </p>
                <ul className="space-y-1.5">
                  {aggSections.cross_persona_themes.map((theme, i) => (
                    <li key={i} className="text-sm text-zinc-700 flex gap-2">
                      <span className="text-zinc-300 shrink-0">—</span>
                      {theme}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(aggSections?.recommendations || aggregate.recommendations) && (
              <div className="bg-zinc-50 rounded-lg p-4">
                <p className="text-xs font-medium text-zinc-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Lightbulb size={12} /> Recommendations
                </p>
                <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">
                  {aggSections?.recommendations || aggregate.recommendations}
                </p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Per-Persona Sections */}
      {individuals.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <MessageSquare size={14} /> Individual Interviews ({individuals.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {individuals.map(r => (
              <IDIPersonaCard
                key={r.id}
                result={r}
                name={r.persona_id ? (personaNames[r.persona_id] || "Persona") : "Persona"}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SimulationResultsPage() {
  const { projectId, simulationId } = useParams<{ projectId: string; simulationId: string }>();
  const router = useRouter();

  const { data: simulation } = useQuery({
    queryKey: ["simulation", simulationId],
    queryFn: () => getSimulation(projectId, simulationId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "pending" || status === "running" || status === "generating_report" ? 3000 : false;
    },
  });

  const isIDI = simulation?.simulation_type === "idi_ai" || simulation?.simulation_type === "idi_manual";

  const { data: results } = useQuery({
    queryKey: ["simulation-results", simulationId],
    queryFn: () => getSimulationResults(projectId, simulationId),
    enabled: simulation?.status === "complete",
  });

  const aggregate = results?.find(r => r.result_type === "aggregate");
  const individual = results?.filter(r => r.result_type === "individual") ?? [];

  const personaNames: Record<string, string> = {};
  individual.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  const isRunning = simulation?.status === "pending" || simulation?.status === "running" || simulation?.status === "generating_report";
  const isActive = simulation?.status === "active";
  const isFailed = simulation?.status === "failed";

  const simTypeLabel = () => {
    if (simulation?.simulation_type === "idi_ai") return "IDI — AI Assisted";
    if (simulation?.simulation_type === "idi_manual") return "IDI — Manual";
    return "Concept Test";
  };

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
            <>
              <Badge variant={
                simulation.status === "complete" ? "success" :
                simulation.status === "failed" ? "error" :
                simulation.status === "active" ? "warning" :
                "warning"
              }>{simulation.status}</Badge>
              <Badge variant="default">{simTypeLabel()}</Badge>
            </>
          )}
        </div>
        {simulation && (
          <p className="text-sm text-zinc-500">
            {formatDate(simulation.created_at)}
            {" · "}
            <code className="text-xs bg-zinc-100 text-zinc-500 px-1.5 py-0.5 rounded font-mono">
              #{String(simulation.id).slice(0, 8)}
            </code>
            {simulation.prompt_question && <>{" · "}{simulation.prompt_question}</>}
          </p>
        )}
      </div>

      {/* Active manual IDI — interview in progress */}
      {isActive && simulation?.simulation_type === "idi_manual" && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-14 h-14 rounded-full bg-zinc-100 flex items-center justify-center mb-5">
            <Video size={24} className="text-zinc-500" />
          </div>
          <p className="text-sm font-medium text-zinc-800 mb-1">Interview in progress</p>
          <p className="text-xs text-zinc-400 mb-5">Your manual interview session is still active.</p>
          <button
            onClick={() => router.push(`/projects/${projectId}/simulations/${simulationId}/chat`)}
            className="px-4 py-2 text-sm font-medium bg-zinc-900 text-white rounded-lg hover:bg-zinc-700 transition-colors"
          >
            Resume Interview
          </button>
        </div>
      )}

      {/* Running / generating state */}
      {isRunning && (
        <div className="flex flex-col items-center justify-center py-16 max-w-md mx-auto">
          <Spinner className="h-7 w-7 border-zinc-200 border-t-zinc-700 mb-6" />

          {simulation?.progress ? (
            <div className="w-full space-y-4">
              <div className="text-center">
                <p className="text-sm font-medium text-zinc-800">
                  {simulation.progress.stage === "generating_report"
                    ? "Generating report…"
                    : simulation.progress.current_name
                      ? `Interviewing ${simulation.progress.current_name}…`
                      : "Running simulation…"}
                </p>
                <p className="text-xs text-zinc-400 mt-1">
                  {simulation.progress.stage === "generating_report"
                    ? "Synthesising findings across all interviews"
                    : `${simulation.progress.current} of ${simulation.progress.total} personas`}
                </p>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-zinc-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-zinc-800 h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${simulation.progress.stage === "generating_report"
                      ? 100
                      : ((simulation.progress.current - 1) / simulation.progress.total) * 100}%`
                  }}
                />
              </div>

              {/* Completed personas */}
              {simulation.progress.completed.length > 0 && (
                <div className="space-y-1.5">
                  {simulation.progress.completed.map(name => (
                    <div key={name} className="flex items-center gap-2 text-xs text-zinc-500">
                      <span className="text-emerald-500">✓</span>
                      {name}
                    </div>
                  ))}
                  {simulation.progress.stage === "interviewing" && simulation.progress.current_name && (
                    <div className="flex items-center gap-2 text-xs text-zinc-700 font-medium">
                      <Spinner className="h-3 w-3 border-zinc-300 border-t-zinc-600 shrink-0" />
                      {simulation.progress.current_name}
                    </div>
                  )}
                  {simulation.progress.failed.map(name => (
                    <div key={name} className="flex items-center gap-2 text-xs text-red-400">
                      <span>✗</span>
                      {name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm font-medium text-zinc-800">
                {simulation?.status === "generating_report" ? "Generating report…" : "Running simulation…"}
              </p>
              <p className="text-xs text-zinc-400 mt-1">This takes a few minutes depending on group size.</p>
            </div>
          )}
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <div className="border border-red-200 bg-red-50 rounded-xl px-5 py-4">
          <p className="text-sm font-medium text-red-700 mb-1">Simulation failed</p>
          {simulation?.error_message && <p className="text-xs text-red-600">{simulation.error_message}</p>}
        </div>
      )}

      {/* Partial failure warning */}
      {simulation?.status === "complete" && simulation?.error_message && (
        <div className="border border-amber-200 bg-amber-50 rounded-xl px-4 py-3 mb-5">
          <p className="text-xs text-amber-700">⚠ Partial results — {simulation.error_message}</p>
        </div>
      )}

      {/* Results */}
      {simulation?.status === "complete" && results && (
        <>
          {isIDI ? (
            <IDIReportView results={results} />
          ) : (
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
                      <ConceptIndividualCard key={r.id} result={r} personas={personaNames} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
