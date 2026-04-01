"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getSimulation, getSimulationResults } from "@/lib/api";
import { formatDate } from "@/lib/utils";

type SurveyAggQuestion = {
  id: string;
  type: "likert" | "multiple_choice" | "open_ended";
  text: string;
  scale?: number;
  low_label?: string;
  high_label?: string;
  average?: number;
  distribution?: Record<string, number>;
  options?: string[];
  themes?: string[];
  notable_quotes?: string[];
  n?: number;
};

type SurveyIndividualAnswer = {
  id: string;
  question_text: string;
  type: string;
  answer: string | number;
};

export default function SurveyExportPage() {
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

  const aggregate = results?.find(r => r.result_type === "survey_aggregate");
  const individuals = (results ?? []).filter(r => r.result_type === "survey_individual");

  const aggSections = aggregate?.report_sections as {
    per_question?: SurveyAggQuestion[];
    executive_summary?: string;
    recommendations?: string;
  } | null;

  const personaNames: Record<string, string> = {};
  individuals.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  if (!simulation || !results) {
    return <div className="p-8 text-sm text-zinc-400">Loading…</div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-8 py-10 font-sans text-zinc-900">
      {/* Print button — hidden in print */}
      <div className="print:hidden mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Survey Results</h1>
          <p className="text-xs text-zinc-400 mt-0.5">{formatDate(simulation.created_at)}</p>
        </div>
        <button
          onClick={() => window.print()}
          className="px-4 py-2 text-sm font-medium bg-zinc-900 text-white rounded-lg hover:bg-zinc-700 transition-colors"
        >
          Save as PDF
        </button>
      </div>

      {/* Header */}
      <div className="mb-8 pb-6 border-b border-zinc-200">
        <p className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Survey Simulation Report</p>
        <h1 className="text-2xl font-bold text-zinc-900 mb-1">Survey Results</h1>
        <p className="text-sm text-zinc-500">{formatDate(simulation.created_at)} · {individuals.length} respondent{individuals.length !== 1 ? "s" : ""}</p>
      </div>

      {/* Executive Summary */}
      {(aggSections?.executive_summary || aggSections?.recommendations) && (
        <section className="mb-10">
          <h2 className="text-base font-semibold text-zinc-800 mb-4 uppercase tracking-wide text-xs">Executive Summary</h2>
          {aggSections?.executive_summary && (
            <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line mb-4">{aggSections.executive_summary}</p>
          )}
          {aggSections?.recommendations && (
            <div className="bg-zinc-50 rounded-lg p-4">
              <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wide mb-2">Recommendations</p>
              <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggSections.recommendations}</p>
            </div>
          )}
        </section>
      )}

      {/* Per-question aggregate */}
      {aggSections?.per_question && aggSections.per_question.length > 0 && (
        <section className="mb-10">
          <h2 className="text-xs font-semibold text-zinc-800 uppercase tracking-wide mb-4">Results by Question</h2>
          <div className="space-y-6">
            {aggSections.per_question.map((q, i) => (
              <div key={q.id} className="border border-zinc-200 rounded-lg p-4">
                <p className="text-xs text-zinc-400 mb-0.5">
                  Q{i + 1} · {q.type === "likert" ? "Likert scale" : q.type === "multiple_choice" ? "Multiple choice" : "Open-ended"}
                  {q.n != null && <> · {q.n} respondents</>}
                </p>
                <p className="text-sm font-medium text-zinc-800 mb-3">{q.text}</p>

                {q.type === "likert" && q.distribution && (
                  <div className="space-y-1">
                    {q.average != null && (
                      <p className="text-lg font-semibold text-zinc-900 mb-2">
                        {q.average.toFixed(1)} <span className="text-sm font-normal text-zinc-400">/ {q.scale ?? 5}</span>
                      </p>
                    )}
                    {Array.from({ length: q.scale ?? 5 }, (_, j) => j + 1).map(n => {
                      const total = Object.values(q.distribution!).reduce((a, b) => a + b, 0);
                      const count = q.distribution![String(n)] ?? 0;
                      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                      return (
                        <div key={n} className="flex items-center gap-2 text-xs">
                          <span className="w-4 text-zinc-500 text-right">{n}</span>
                          <div className="flex-1 bg-zinc-100 rounded h-2 overflow-hidden">
                            <div className="bg-zinc-600 h-2" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="w-10 text-zinc-500">{pct}% ({count})</span>
                        </div>
                      );
                    })}
                    {(q.low_label || q.high_label) && (
                      <div className="flex justify-between text-xs text-zinc-400 mt-1 pl-6">
                        <span>{q.low_label}</span>
                        <span>{q.high_label}</span>
                      </div>
                    )}
                  </div>
                )}

                {q.type === "multiple_choice" && q.distribution && (
                  <div className="space-y-1.5">
                    {(q.options?.length ? q.options : Object.keys(q.distribution)).map(opt => {
                      const total = Object.values(q.distribution!).reduce((a, b) => a + b, 0);
                      const count = q.distribution![opt] ?? 0;
                      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                      return (
                        <div key={opt} className="flex items-center gap-2 text-xs">
                          <span className="w-28 text-zinc-700 truncate">{opt}</span>
                          <div className="flex-1 bg-zinc-100 rounded h-2 overflow-hidden">
                            <div className="bg-zinc-600 h-2" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="w-14 text-zinc-500">{pct}% ({count})</span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {q.type === "open_ended" && (
                  <div className="space-y-2">
                    {q.themes && q.themes.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {q.themes.map(t => (
                          <span key={t} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{t}</span>
                        ))}
                      </div>
                    )}
                    {q.notable_quotes && q.notable_quotes.length > 0 && (
                      <div className="space-y-1.5">
                        {q.notable_quotes.map((quote, j) => (
                          <blockquote key={j} className="border-l-2 border-zinc-200 pl-3 text-sm text-zinc-500 italic">
                            "{quote}"
                          </blockquote>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Individual responses */}
      {individuals.length > 0 && (
        <section className="mb-10">
          <h2 className="text-xs font-semibold text-zinc-800 uppercase tracking-wide mb-4">Individual Responses</h2>
          <div className="space-y-6">
            {individuals.map((r, idx) => {
              const answers = (r.report_sections as { answers?: SurveyIndividualAnswer[] } | null)?.answers ?? [];
              const name = r.persona_id ? (personaNames[r.persona_id] || `Persona ${idx + 1}`) : `Persona ${idx + 1}`;
              return (
                <div key={r.id} className="border border-zinc-200 rounded-lg p-4 break-inside-avoid">
                  <p className="text-sm font-semibold text-zinc-800 mb-3">{name}</p>
                  <div className="space-y-3">
                    {answers.map((a, i) => (
                      <div key={a.id ?? i}>
                        <p className="text-xs text-zinc-400 mb-0.5">Q{i + 1}. {a.question_text}</p>
                        <p className="text-sm text-zinc-700">{String(a.answer)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <style>{`
        @media print {
          body { -webkit-print-color-adjust: exact; }
        }
      `}</style>
    </div>
  );
}
