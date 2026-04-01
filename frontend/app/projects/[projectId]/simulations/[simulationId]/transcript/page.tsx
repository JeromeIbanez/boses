"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getSimulation, getSimulationResults } from "@/lib/api";
import type { SimulationResult } from "@/types";
import { formatDate } from "@/lib/utils";

export default function TranscriptPage() {
  const { projectId, simulationId } = useParams<{ projectId: string; simulationId: string }>();

  const { data: simulation } = useQuery({
    queryKey: ["simulation", simulationId],
    queryFn: () => getSimulation(projectId, simulationId),
  });

  const { data: results } = useQuery({
    queryKey: ["simulation-results", simulationId],
    queryFn: () => getSimulationResults(projectId, simulationId),
    enabled: simulation?.status === "complete",
  });

  const individuals = (results ?? []).filter(
    (r): r is SimulationResult & { transcript: string } =>
      (r.result_type === "idi_individual") && !!r.transcript
  );

  const aggregate = results?.find(r => r.result_type === "idi_aggregate");
  const aggSections = aggregate?.report_sections as {
    executive_summary?: string;
    cross_persona_themes?: string[];
    per_persona_highlights?: string[];
    recommendations?: string;
  } | null;

  const personaNames: Record<string, string> = {};
  individuals.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  if (!simulation) {
    return (
      <div className="p-12 text-center text-sm text-zinc-400">Loading…</div>
    );
  }

  return (
    <>
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
      `}</style>

      {/* Print button */}
      <div className="no-print fixed top-4 right-4 z-50">
        <button
          onClick={() => window.print()}
          className="px-4 py-2 text-sm font-medium bg-zinc-900 text-white rounded-lg hover:bg-zinc-700 transition-colors shadow-lg"
        >
          Save as PDF
        </button>
      </div>

      <div className="max-w-3xl mx-auto px-8 py-12 text-zinc-900">
        {/* Header */}
        <div className="mb-10 border-b border-zinc-200 pb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-2">
            IDI Research Report
          </p>
          <h1 className="text-2xl font-bold text-zinc-900 mb-1">
            Interview Transcripts
          </h1>
          <p className="text-sm text-zinc-500">
            {formatDate(simulation.created_at)}
            {" · "}
            <span className="font-mono text-xs">#{simulation.id.slice(0, 8)}</span>
          </p>
        </div>

        {/* Executive Summary */}
        {(aggSections?.executive_summary || aggregate?.summary_text) && (
          <section className="mb-10">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-3">
              Executive Summary
            </h2>
            <p className="text-sm leading-relaxed text-zinc-700 whitespace-pre-line">
              {aggSections?.executive_summary || aggregate?.summary_text}
            </p>
          </section>
        )}

        {/* Key Themes */}
        {aggregate?.top_themes && aggregate.top_themes.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-3">
              Key Themes
            </h2>
            <div className="flex flex-wrap gap-2">
              {aggregate.top_themes.map(t => (
                <span
                  key={t}
                  className="text-xs px-2.5 py-1 bg-zinc-100 text-zinc-700 rounded-full border border-zinc-200"
                >
                  {t}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Recommendations */}
        {(aggSections?.recommendations || aggregate?.recommendations) && (
          <section className="mb-10">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-3">
              Recommendations
            </h2>
            <p className="text-sm leading-relaxed text-zinc-700 whitespace-pre-line">
              {aggSections?.recommendations || aggregate?.recommendations}
            </p>
          </section>
        )}

        {/* Divider */}
        {individuals.length > 0 && (
          <div className="border-t border-zinc-200 my-10" />
        )}

        {/* Transcripts */}
        {individuals.map((result, idx) => {
          const name = result.persona_id
            ? (personaNames[result.persona_id] || `Persona ${idx + 1}`)
            : `Persona ${idx + 1}`;

          const sections = result.report_sections as {
            summary?: string;
            notable_quotes?: string[];
          } | null;

          return (
            <section key={result.id} className="mb-14">
              {/* Persona header */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-semibold shrink-0">
                  {name.charAt(0)}
                </div>
                <div>
                  <p className="text-base font-semibold text-zinc-900">{name}</p>
                  {result.sentiment && (
                    <span className={`text-xs font-medium ${
                      result.sentiment === "Positive" ? "text-emerald-600" :
                      result.sentiment === "Negative" ? "text-red-600" :
                      "text-zinc-500"
                    }`}>
                      {result.sentiment}
                    </span>
                  )}
                </div>
              </div>

              {/* Summary */}
              {sections?.summary && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-1.5">Summary</p>
                  <p className="text-sm leading-relaxed text-zinc-700">{sections.summary}</p>
                </div>
              )}

              {/* Key themes */}
              {result.key_themes && result.key_themes.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-1.5">Key Themes</p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.key_themes.map(t => (
                      <span key={t} className="text-xs px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded-full border border-zinc-200">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Notable quotes */}
              {sections?.notable_quotes && sections.notable_quotes.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-1.5">Notable Quotes</p>
                  <div className="space-y-2">
                    {sections.notable_quotes.map((q, i) => (
                      <blockquote key={i} className="border-l-2 border-zinc-300 pl-3 text-sm text-zinc-600 italic">
                        {q}
                      </blockquote>
                    ))}
                  </div>
                </div>
              )}

              {/* Full transcript */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-2">Full Transcript</p>
                <div className="bg-zinc-50 rounded-lg p-5 border border-zinc-100">
                  {result.transcript.split(/\n\n+/).map((block, i) => {
                    const isInterviewer = block.trimStart().startsWith("INTERVIEWER:");
                    const isRespondent = block.trimStart().startsWith("RESPONDENT:");
                    return (
                      <div key={i} className={`mb-4 last:mb-0 ${isInterviewer ? "pl-0" : "pl-4"}`}>
                        {isInterviewer ? (
                          <>
                            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-0.5">Interviewer</p>
                            <p className="text-sm text-zinc-700 leading-relaxed">
                              {block.replace(/^INTERVIEWER:\s*/i, "")}
                            </p>
                          </>
                        ) : isRespondent ? (
                          <>
                            <p className="text-xs font-semibold text-zinc-800 uppercase tracking-wide mb-0.5">{name}</p>
                            <p className="text-sm text-zinc-900 leading-relaxed">
                              {block.replace(/^RESPONDENT:\s*/i, "")}
                            </p>
                          </>
                        ) : (
                          <p className="text-sm text-zinc-600 leading-relaxed whitespace-pre-wrap">{block}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {idx < individuals.length - 1 && (
                <div className="border-t border-zinc-100 mt-10" />
              )}
            </section>
          );
        })}

        {individuals.length === 0 && (
          <p className="text-sm text-zinc-400 text-center py-12">No transcripts available.</p>
        )}

        {/* Footer */}
        <div className="border-t border-zinc-200 pt-6 mt-10">
          <p className="text-xs text-zinc-400 text-center">
            Generated by Boses · {formatDate(simulation.created_at)}
          </p>
        </div>
      </div>
    </>
  );
}
