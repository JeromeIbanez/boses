"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, TrendingUp, MessageSquare, Lightbulb, ChevronDown, ChevronUp, Users, Video, FileText, BarChart2, Share2, Check, X } from "lucide-react";
import { getSimulation, getSimulationResults, abortSimulation, generateShareLink, revokeShareLink } from "@/lib/api";
import ConvergencePanel from "@/components/simulations/ConvergencePanel";
import ReliabilityPanel from "@/components/simulations/ReliabilityPanel";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";
import type { SimulationResult, ConjointIndividualSections, ConjointAggregateSections } from "@/types";

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
            <div className="mt-3">
              <pre className="text-xs text-zinc-600 leading-relaxed whitespace-pre-wrap bg-zinc-50 rounded-lg p-4 font-sans">
                {result.transcript}
              </pre>
              <button
                onClick={() => setShowTranscript(false)}
                className="mt-2 flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
              >
                <ChevronUp size={12} /> Hide transcript
              </button>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// IDI report view
// ---------------------------------------------------------------------------

function IDIReportView({ results, projectId, simulationId }: { results: SimulationResult[]; projectId: string; simulationId: string }) {
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

  const hasTranscripts = individuals.some(r => r.transcript);

  return (
    <div className="space-y-8">
      {/* Executive Summary */}
      {aggregate && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
              <TrendingUp size={14} /> Executive Summary
            </h2>
            {hasTranscripts && (
              <a
                href={`/projects/${projectId}/simulations/${simulationId}/transcript`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
              >
                <FileText size={13} /> View transcript (PDF)
              </a>
            )}
          </div>
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
// Focus Group results view
// ---------------------------------------------------------------------------

type FGTranscriptEntry = { speaker: string; round: number; text: string; persona_id?: string };

const PERSONA_COLORS = [
  "bg-violet-700",
  "bg-sky-700",
  "bg-emerald-700",
  "bg-orange-600",
  "bg-pink-700",
  "bg-teal-700",
  "bg-rose-700",
  "bg-indigo-700",
];

function FocusGroupReportView({ results }: { results: SimulationResult[] }) {
  const aggregate = results.find(r => r.result_type === "focus_group_aggregate");
  const individuals = results.filter(r => r.result_type === "focus_group_individual");

  const aggSections = aggregate?.report_sections as {
    transcript?: FGTranscriptEntry[];
    moderator_summary?: string;
    consensus_themes?: string[];
    disagreements?: string[];
    recommendations?: string;
  } | null;

  // Assign a stable color to each unique non-Moderator speaker
  const speakerColors: Record<string, string> = {};
  let colorIdx = 0;
  (aggSections?.transcript ?? []).forEach(e => {
    if (e.speaker !== "Moderator" && !speakerColors[e.speaker]) {
      speakerColors[e.speaker] = PERSONA_COLORS[colorIdx % PERSONA_COLORS.length];
      colorIdx++;
    }
  });

  const round1 = (aggSections?.transcript ?? []).filter(e => e.round === 1);
  const round2 = (aggSections?.transcript ?? []).filter(e => e.round === 2);
  const moderatorOpening = (aggSections?.transcript ?? []).find(e => e.speaker === "Moderator" && e.round === 0);
  const moderatorBridge = (aggSections?.transcript ?? []).find(e => e.speaker === "Moderator" && e.round === 1);

  // Build persona name map
  const personaNames: Record<string, string> = {};
  individuals.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  return (
    <div className="space-y-8">
      {/* Aggregate Panel */}
      {aggregate && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <TrendingUp size={14} /> Focus Group Summary
          </h2>
          <Card className="space-y-5">
            {aggSections?.moderator_summary && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <MessageSquare size={12} /> Moderator Summary
                </p>
                <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggSections.moderator_summary}</p>
              </div>
            )}

            {aggSections?.consensus_themes && aggSections.consensus_themes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Consensus Themes</p>
                <div className="flex flex-wrap gap-2">
                  {aggSections.consensus_themes.map(t => (
                    <Badge key={t} variant="info">{t}</Badge>
                  ))}
                </div>
              </div>
            )}

            {aggSections?.disagreements && aggSections.disagreements.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Points of Disagreement</p>
                <div className="flex flex-wrap gap-2">
                  {aggSections.disagreements.map(d => (
                    <span key={d} className="text-xs px-2.5 py-1 rounded-full bg-amber-50 border border-amber-100 text-amber-700">{d}</span>
                  ))}
                </div>
              </div>
            )}

            {aggregate.sentiment_distribution && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-3">Sentiment</p>
                <SentimentBar distribution={aggregate.sentiment_distribution} />
              </div>
            )}

            {aggSections?.recommendations && (
              <div className="bg-zinc-50 rounded-lg p-4">
                <p className="text-xs font-medium text-zinc-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Lightbulb size={12} /> Recommendations
                </p>
                <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggSections.recommendations}</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Discussion Transcript */}
      {aggSections?.transcript && aggSections.transcript.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <Users size={14} /> Discussion Transcript
          </h2>
          <div className="space-y-3">
            {/* Moderator opening */}
            {moderatorOpening && (
              <div className="bg-zinc-50 border border-zinc-200 rounded-xl px-4 py-3">
                <p className="text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wide">Moderator — Opening</p>
                <p className="text-sm text-zinc-700 leading-relaxed">{moderatorOpening.text}</p>
              </div>
            )}

            {/* Round 1 */}
            {round1.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide px-1 my-3">Round 1 — Initial Responses</p>
                <div className="space-y-2.5">
                  {round1.map((e, i) => (
                    <div key={i} className="flex gap-3">
                      <div className={`w-8 h-8 rounded-full ${speakerColors[e.speaker] ?? "bg-zinc-600"} text-white flex items-center justify-center text-xs font-semibold shrink-0`}>
                        {e.speaker.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-zinc-500 mb-1">{e.speaker}</p>
                        <p className="text-sm text-zinc-700 leading-relaxed">{e.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Moderator bridge */}
            {moderatorBridge && (
              <div className="bg-zinc-50 border border-zinc-200 rounded-xl px-4 py-3 my-1">
                <p className="text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wide">Moderator — Follow-up</p>
                <p className="text-sm text-zinc-700 leading-relaxed">{moderatorBridge.text}</p>
              </div>
            )}

            {/* Round 2 */}
            {round2.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide px-1 my-3">Round 2 — Reactions</p>
                <div className="space-y-2.5">
                  {round2.map((e, i) => (
                    <div key={i} className="flex gap-3">
                      <div className={`w-8 h-8 rounded-full ${speakerColors[e.speaker] ?? "bg-zinc-600"} text-white flex items-center justify-center text-xs font-semibold shrink-0`}>
                        {e.speaker.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-zinc-500 mb-1">{e.speaker}</p>
                        <p className="text-sm text-zinc-700 leading-relaxed">{e.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Individual Cards */}
      {individuals.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <MessageSquare size={14} /> Individual Contributions ({individuals.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {individuals.map((r, idx) => {
              const name = r.persona_id ? (personaNames[r.persona_id] || `Persona ${idx + 1}`) : `Persona ${idx + 1}`;
              const sections = r.report_sections as { round_1_text?: string; round_2_text?: string } | null;
              const color = speakerColors[name] ?? PERSONA_COLORS[idx % PERSONA_COLORS.length];
              return (
                <Card key={r.id} className="flex flex-col gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-8 h-8 rounded-full ${color} text-white flex items-center justify-center text-sm font-medium shrink-0`}>
                      {name.charAt(0)}
                    </div>
                    <span className="text-sm font-medium text-zinc-900">{name}</span>
                  </div>
                  {sections?.round_1_text && (
                    <div>
                      <p className="text-xs text-zinc-400 mb-1">Round 1</p>
                      <p className="text-sm text-zinc-700 leading-relaxed">{sections.round_1_text}</p>
                    </div>
                  )}
                  {sections?.round_2_text && (
                    <div className="border-t border-zinc-100 pt-3">
                      <p className="text-xs text-zinc-400 mb-1">Round 2</p>
                      <p className="text-sm text-zinc-700 leading-relaxed">{sections.round_2_text}</p>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Survey results view
// ---------------------------------------------------------------------------

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

function LikertBar({ distribution, scale, lowLabel, highLabel, average }: {
  distribution: Record<string, number>;
  scale: number;
  lowLabel?: string;
  highLabel?: string;
  average?: number;
}) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  if (total === 0) return null;
  const buckets = Array.from({ length: scale }, (_, i) => i + 1);
  const colors = ["bg-red-300", "bg-orange-300", "bg-yellow-300", "bg-lime-300", "bg-emerald-400"];
  return (
    <div className="space-y-2">
      {average != null && (
        <p className="text-2xl font-semibold text-zinc-900">{average.toFixed(1)} <span className="text-sm font-normal text-zinc-400">/ {scale}</span></p>
      )}
      <div className="flex gap-1 items-end h-10">
        {buckets.map(n => {
          const count = distribution[String(n)] ?? 0;
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div key={n} className="flex-1 flex flex-col items-center gap-0.5">
              <div
                className={`w-full rounded-sm ${colors[Math.min(n - 1, colors.length - 1)]}`}
                style={{ height: `${Math.max(4, pct)}%`, minHeight: count > 0 ? 8 : 4 }}
                title={`${n}: ${count}`}
              />
              <span className="text-xs text-zinc-400">{n}</span>
            </div>
          );
        })}
      </div>
      {(lowLabel || highLabel) && (
        <div className="flex justify-between text-xs text-zinc-400">
          <span>{lowLabel}</span>
          <span>{highLabel}</span>
        </div>
      )}
    </div>
  );
}

function ChoiceBar({ distribution, options }: { distribution: Record<string, number>; options?: string[] }) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  const keys = options?.length ? options : Object.keys(distribution);
  if (total === 0) return null;
  return (
    <div className="space-y-2">
      {keys.map(opt => {
        const count = distribution[opt] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={opt} className="space-y-1">
            <div className="flex justify-between text-xs text-zinc-600">
              <span>{opt}</span>
              <span className="font-medium">{pct}% <span className="text-zinc-400 font-normal">({count})</span></span>
            </div>
            <div className="w-full bg-zinc-100 rounded-full h-2 overflow-hidden">
              <div className="bg-zinc-700 h-2 rounded-full" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SurveyReportView({ results, projectId, simulationId }: {
  results: SimulationResult[];
  projectId: string;
  simulationId: string;
}) {
  const aggregate = results.find(r => r.result_type === "survey_aggregate");
  const individuals = results.filter(r => r.result_type === "survey_individual");

  const aggSections = aggregate?.report_sections as {
    per_question?: SurveyAggQuestion[];
    executive_summary?: string;
    recommendations?: string;
  } | null;

  const personaNames: Record<string, string> = {};
  individuals.forEach((r, i) => {
    if (r.persona_id) personaNames[r.persona_id] = `Persona ${i + 1}`;
  });

  return (
    <div className="space-y-8">
      {/* Executive Summary */}
      {aggregate && (aggSections?.executive_summary || aggSections?.recommendations) && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
              <TrendingUp size={14} /> Executive Summary
            </h2>
            <a
              href={`/projects/${projectId}/simulations/${simulationId}/survey-export`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
            >
              <FileText size={13} /> Export as PDF
            </a>
          </div>
          <Card className="space-y-4">
            {aggSections?.executive_summary && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <MessageSquare size={12} /> Summary
                </p>
                <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggSections.executive_summary}</p>
              </div>
            )}
            {aggSections?.recommendations && (
              <div className="bg-zinc-50 rounded-lg p-4">
                <p className="text-xs font-medium text-zinc-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Lightbulb size={12} /> Recommendations
                </p>
                <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{aggSections.recommendations}</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Per-question aggregate results */}
      {aggSections?.per_question && aggSections.per_question.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <TrendingUp size={14} /> Results by Question
          </h2>
          <div className="space-y-4">
            {aggSections.per_question.map((q, i) => (
              <Card key={q.id} className="space-y-3">
                <div>
                  <p className="text-xs text-zinc-400 mb-0.5">Q{i + 1} · <span className={`${q.type === "likert" ? "text-blue-500" : q.type === "multiple_choice" ? "text-purple-500" : "text-zinc-400"}`}>{q.type === "multiple_choice" ? "Multiple choice" : q.type === "likert" ? "Likert scale" : "Open-ended"}</span></p>
                  <p className="text-sm font-medium text-zinc-800">{q.text}</p>
                </div>
                {q.type === "likert" && q.distribution && (
                  <LikertBar
                    distribution={q.distribution}
                    scale={q.scale ?? 5}
                    lowLabel={q.low_label}
                    highLabel={q.high_label}
                    average={q.average}
                  />
                )}
                {q.type === "multiple_choice" && q.distribution && (
                  <ChoiceBar distribution={q.distribution} options={q.options} />
                )}
                {q.type === "open_ended" && (
                  <div className="space-y-3">
                    {q.themes && q.themes.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {q.themes.map(t => <Badge key={t} variant="info">{t}</Badge>)}
                      </div>
                    )}
                    {q.notable_quotes && q.notable_quotes.length > 0 && (
                      <div className="space-y-2">
                        {q.notable_quotes.map((quote, j) => (
                          <blockquote key={j} className="border-l-2 border-zinc-200 pl-3 text-sm text-zinc-500 italic">
                            "{quote}"
                          </blockquote>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <p className="text-xs text-zinc-400">{q.n} respondent{q.n !== 1 ? "s" : ""}</p>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Individual responses */}
      {individuals.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <MessageSquare size={14} /> Individual Responses ({individuals.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {individuals.map(r => {
              const answers = (r.report_sections as { answers?: SurveyIndividualAnswer[] } | null)?.answers ?? [];
              const name = r.persona_id ? (personaNames[r.persona_id] || "Persona") : "Persona";
              return (
                <Card key={r.id} className="flex flex-col gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-medium shrink-0">
                      {name.charAt(0)}
                    </div>
                    <span className="text-sm font-medium text-zinc-900">{name}</span>
                  </div>
                  <div className="space-y-2.5">
                    {answers.map((a, i) => (
                      <div key={a.id ?? i} className="text-sm">
                        <p className="text-xs text-zinc-400 mb-0.5">Q{i + 1}. {a.question_text}</p>
                        <p className="text-zinc-700">{String(a.answer)}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conjoint results view
// ---------------------------------------------------------------------------

function AttributeImportanceChart({ importances }: { importances: Record<string, number> }) {
  const sorted = Object.entries(importances).sort(([, a], [, b]) => b - a);
  const maxVal = sorted[0]?.[1] ?? 100;
  return (
    <div className="space-y-2.5">
      {sorted.map(([attr, pct]) => (
        <div key={attr} className="space-y-1">
          <div className="flex justify-between text-xs text-zinc-600">
            <span className="font-medium">{attr}</span>
            <span>{pct.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-zinc-100 rounded-full h-3 overflow-hidden">
            <div
              className="bg-zinc-800 h-3 rounded-full transition-all"
              style={{ width: `${maxVal > 0 ? (pct / maxVal) * 100 : 0}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function PartWorthChart({ partWorths }: { partWorths: Record<string, Record<string, number>> }) {
  return (
    <div className="space-y-5">
      {Object.entries(partWorths).map(([attr, levels]) => {
        const maxAbs = Math.max(...Object.values(levels).map(Math.abs), 0.01);
        const sorted = Object.entries(levels).sort(([, a], [, b]) => b - a);
        return (
          <div key={attr}>
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">{attr}</p>
            <div className="space-y-1.5">
              {sorted.map(([level, utility]) => {
                const pct = Math.abs(utility) / maxAbs * 44;
                const isPos = utility >= 0;
                return (
                  <div key={level} className="flex items-center gap-2 text-xs">
                    <span className="text-zinc-500 w-24 shrink-0 text-right truncate">{level}</span>
                    <div className="flex-1 flex items-center">
                      <div className="w-1/2 flex justify-end">
                        {!isPos && <div className="bg-red-300 h-2.5 rounded-l-sm" style={{ width: `${pct}%` }} />}
                      </div>
                      <div className="w-px h-3 bg-zinc-300 mx-0.5 shrink-0" />
                      <div className="w-1/2 flex justify-start">
                        {isPos && <div className="bg-emerald-400 h-2.5 rounded-r-sm" style={{ width: `${pct}%` }} />}
                      </div>
                    </div>
                    <span className={`w-12 text-right font-mono shrink-0 ${isPos ? "text-emerald-600" : "text-red-500"}`}>
                      {utility > 0 ? "+" : ""}{utility.toFixed(3)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ConjointReportView({ results }: { results: SimulationResult[] }) {
  const [activeTab, setActiveTab] = useState<"overview" | "personas" | "simulator">("overview");

  const aggregate = results.find(r => r.result_type === "conjoint_aggregate");
  const individuals = results.filter(r => r.result_type === "conjoint_individual");
  const agg = aggregate?.report_sections as ConjointAggregateSections | null;

  // Assign stable colors per persona index
  const personaColorMap: Record<string, string> = {};
  individuals.forEach((r, i) => {
    if (r.persona_id) personaColorMap[r.persona_id] = PERSONA_COLORS[i % PERSONA_COLORS.length];
  });

  return (
    <div className="space-y-6">
      {/* Tab nav */}
      <div className="flex gap-1 border-b border-zinc-200">
        {(["overview", "personas", "simulator"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm capitalize transition-colors ${
              activeTab === tab
                ? "border-b-2 border-zinc-800 text-zinc-900 font-medium"
                : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            {tab === "simulator" ? "Market Simulator" : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === "overview" && agg && (
        <div className="space-y-8">
          {/* Attribute importance */}
          <div>
            <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
              <BarChart2 size={14} /> Attribute Importance
            </h2>
            <Card>
              <AttributeImportanceChart importances={agg.attribute_importances} />
            </Card>
          </div>

          {/* Part-worth utilities */}
          <div>
            <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4">Level Utilities (Part-Worths)</h2>
            <Card>
              <p className="text-xs text-zinc-400 mb-4">Positive values = preferred levels; negative = dispreferred levels, within each attribute.</p>
              <PartWorthChart partWorths={agg.part_worths} />
            </Card>
          </div>

          {/* Executive summary */}
          {(agg.executive_summary || agg.recommendations) && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
                <MessageSquare size={14} /> Findings
              </h2>
              <Card className="space-y-4">
                {agg.executive_summary && (
                  <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{agg.executive_summary}</p>
                )}
                {agg.recommendations && (
                  <div className="bg-zinc-50 rounded-lg p-4">
                    <p className="text-xs font-medium text-zinc-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                      <Lightbulb size={12} /> Recommendations
                    </p>
                    <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{agg.recommendations}</p>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Persona segments */}
          {agg.persona_segments && agg.persona_segments.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4">Persona Segments</h2>
              <div className="grid grid-cols-2 gap-3">
                {agg.persona_segments.map(seg => (
                  <Card key={seg.label}>
                    <p className="text-sm font-medium text-zinc-800">{seg.label}</p>
                    <p className="text-xs text-zinc-400 mt-0.5">{seg.persona_ids.length} persona{seg.persona_ids.length !== 1 ? "s" : ""}</p>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Personas */}
      {activeTab === "personas" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {individuals.map((r, idx) => {
            const sections = r.report_sections as ConjointIndividualSections | null;
            const color = r.persona_id ? (personaColorMap[r.persona_id] ?? PERSONA_COLORS[idx % PERSONA_COLORS.length]) : PERSONA_COLORS[idx % PERSONA_COLORS.length];
            const initial = String.fromCharCode(65 + (idx % 26)); // A, B, C…
            const [showTasks, setShowTasks] = useState(false);
            return (
              <Card key={r.id} className="flex flex-col gap-3">
                <div className="flex items-center gap-2.5">
                  <div className={`w-8 h-8 rounded-full ${color} text-white flex items-center justify-center text-sm font-medium shrink-0`}>
                    {initial}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-zinc-900">Persona {idx + 1}</p>
                    {sections?.top_driver && (
                      <p className="text-xs text-zinc-400">Top driver: <span className="text-zinc-600 font-medium">{sections.top_driver}</span></p>
                    )}
                  </div>
                </div>

                {sections?.attribute_importances && (
                  <div className="space-y-1.5">
                    {Object.entries(sections.attribute_importances)
                      .sort(([, a], [, b]) => b - a)
                      .map(([attr, pct]) => (
                        <div key={attr} className="flex items-center gap-2 text-xs">
                          <span className="text-zinc-500 w-24 shrink-0 truncate">{attr}</span>
                          <div className="flex-1 bg-zinc-100 rounded-full h-1.5 overflow-hidden">
                            <div className="bg-zinc-600 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-zinc-400 w-8 text-right">{pct.toFixed(0)}%</span>
                        </div>
                      ))}
                  </div>
                )}

                {sections?.tasks && sections.tasks.length > 0 && (
                  <div>
                    <button
                      onClick={() => setShowTasks(v => !v)}
                      className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
                    >
                      {showTasks ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      {showTasks ? "Hide" : "Show"} {sections.tasks.length} choice tasks
                    </button>
                    {showTasks && (
                      <div className="mt-2 space-y-2.5 max-h-64 overflow-y-auto pr-1">
                        {sections.tasks.map(task => (
                          <div key={task.task_index} className="text-xs border border-zinc-100 rounded-lg p-2.5 space-y-1.5">
                            <div className="flex gap-2">
                              <div className={`flex-1 rounded-md p-1.5 text-xs ${task.chosen === "A" ? "bg-emerald-50 border border-emerald-100" : "bg-zinc-50 border border-zinc-100 opacity-60"}`}>
                                <p className="font-medium text-zinc-700 mb-0.5">Option A {task.chosen === "A" && <span className="text-emerald-600">✓</span>}</p>
                                {Object.entries(task.profile_a).map(([k, v]) => (
                                  <p key={k} className="text-zinc-500">{k}: {v}</p>
                                ))}
                              </div>
                              <div className={`flex-1 rounded-md p-1.5 text-xs ${task.chosen === "B" ? "bg-emerald-50 border border-emerald-100" : "bg-zinc-50 border border-zinc-100 opacity-60"}`}>
                                <p className="font-medium text-zinc-700 mb-0.5">Option B {task.chosen === "B" && <span className="text-emerald-600">✓</span>}</p>
                                {Object.entries(task.profile_b).map(([k, v]) => (
                                  <p key={k} className="text-zinc-500">{k}: {v}</p>
                                ))}
                              </div>
                            </div>
                            {task.reasoning && (
                              <p className="text-zinc-500 italic">"{task.reasoning}"</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Market Simulator */}
      {activeTab === "simulator" && agg?.market_share_simulation && (
        <div className="space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
              <TrendingUp size={14} /> Predicted Market Share
            </h2>
            <Card className="space-y-4">
              <p className="text-xs text-zinc-400">Based on persona utility scores, each hypothetical product&apos;s predicted first-choice market share.</p>
              <ChoiceBar distribution={agg.market_share_simulation.shares} />
              <div className="space-y-3 border-t border-zinc-100 pt-4">
                {agg.market_share_simulation.profiles_tested.map(p => (
                  <div key={p.name}>
                    <p className="text-xs font-medium text-zinc-700 mb-0.5">{p.name}</p>
                    <p className="text-xs text-zinc-400">{Object.entries(p.attributes).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p>
                  </div>
                ))}
              </div>
            </Card>
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
  const qc = useQueryClient();
  const [showAbortConfirm, setShowAbortConfirm] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  const share = useMutation({
    mutationFn: () => generateShareLink(projectId, simulationId),
    onSuccess: (updated) => {
      qc.setQueryData(["simulation", simulationId], updated);
      const url = `${window.location.origin}/share/${updated.share_token}`;
      navigator.clipboard.writeText(url).then(() => {
        setShareCopied(true);
        setTimeout(() => setShareCopied(false), 2500);
      });
    },
  });

  const unshare = useMutation({
    mutationFn: () => revokeShareLink(projectId, simulationId),
    onSuccess: (updated) => {
      qc.setQueryData(["simulation", simulationId], updated);
    },
  });

  const abort = useMutation({
    mutationFn: () => abortSimulation(projectId, simulationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation", simulationId] });
      setShowAbortConfirm(false);
    },
  });

  const { data: simulation } = useQuery({
    queryKey: ["simulation", simulationId],
    queryFn: () => getSimulation(projectId, simulationId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "pending" || status === "running" || status === "generating_report" ? 3000 : false;
    },
  });

  const isIDI = simulation?.simulation_type === "idi_ai" || simulation?.simulation_type === "idi_manual";
  const isSurvey = simulation?.simulation_type === "survey";
  const isFocusGroup = simulation?.simulation_type === "focus_group";
  const isConjoint = simulation?.simulation_type === "conjoint";

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
    if (simulation?.simulation_type === "survey") return "Survey";
    if (simulation?.simulation_type === "focus_group") return "Focus Group";
    if (simulation?.simulation_type === "conjoint") return "Conjoint Test";
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
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
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
          {simulation?.status === "complete" && (
            <div className="flex items-center gap-2">
              {simulation.share_token ? (
                <>
                  <button
                    onClick={() => {
                      const url = `${window.location.origin}/share/${simulation.share_token}`;
                      navigator.clipboard.writeText(url).then(() => {
                        setShareCopied(true);
                        setTimeout(() => setShareCopied(false), 2500);
                      });
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors"
                  >
                    {shareCopied ? <Check size={12} /> : <Share2 size={12} />}
                    {shareCopied ? "Copied!" : "Copy link"}
                  </button>
                  <button
                    onClick={() => unshare.mutate()}
                    disabled={unshare.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-500 border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors"
                    title="Revoke share link"
                  >
                    <X size={12} /> Revoke
                  </button>
                </>
              ) : (
                <button
                  onClick={() => share.mutate()}
                  disabled={share.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-700 border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors"
                >
                  <Share2 size={12} />
                  {share.isPending ? "Generating…" : "Share results"}
                </button>
              )}
            </div>
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
          {showAbortConfirm ? (
            <div className="w-full mb-4 border border-red-200 bg-red-50 rounded-xl px-4 py-3 text-center">
              <p className="text-sm font-medium text-red-700 mb-3">Stop this simulation?</p>
              <p className="text-xs text-red-500 mb-4">Any personas already interviewed will be discarded.</p>
              <div className="flex gap-2 justify-center">
                <button
                  onClick={() => abort.mutate()}
                  disabled={abort.isPending}
                  className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {abort.isPending ? "Stopping…" : "Yes, stop it"}
                </button>
                <button
                  onClick={() => setShowAbortConfirm(false)}
                  className="px-3 py-1.5 text-xs font-medium text-zinc-600 bg-white border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}

          {simulation?.progress ? (
            <div className="w-full space-y-4">
              <div className="text-center">
                <p className="text-sm font-medium text-zinc-800">
                  {simulation.progress.stage === "generating_report"
                    ? "Generating report…"
                    : simulation.progress.stage === "moderator_bridge"
                      ? "Moderator synthesising Round 1…"
                      : simulation.progress.current_name
                        ? `${simulation.progress.stage === "round_2" ? "Round 2 — " : ""}${simulation.progress.current_name}…`
                        : "Running simulation…"}
                </p>
                <p className="text-xs text-zinc-400 mt-1">
                  {simulation.progress.stage === "generating_report"
                    ? "Synthesising findings across all interviews"
                    : simulation.progress.stage === "moderator_bridge"
                      ? "Preparing follow-up question"
                      : simulation.progress.stage === "round_1"
                        ? `Round 1 — ${simulation.progress.current} of ${simulation.progress.total} personas`
                        : simulation.progress.stage === "round_2"
                          ? `Round 2 — ${simulation.progress.current} of ${simulation.progress.total} personas`
                          : simulation.progress.stage === "choice_tasks"
                            ? `Choice tasks — ${simulation.progress.current} of ${simulation.progress.total} personas`
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
                  {(simulation.progress.stage === "interviewing" || simulation.progress.stage === "round_1" || simulation.progress.stage === "round_2" || simulation.progress.stage === "choice_tasks") && simulation.progress.current_name && (
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

          {!showAbortConfirm && (simulation?.simulation_type === "idi_ai" || simulation?.simulation_type === "focus_group" || simulation?.simulation_type === "conjoint") && (
            <button
              onClick={() => setShowAbortConfirm(true)}
              className="mt-6 text-xs text-zinc-400 hover:text-red-500 transition-colors"
            >
              Stop interview
            </button>
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

      {/* Trust panels — shown once simulation is complete */}
      {simulation?.status === "complete" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <ReliabilityPanel projectId={projectId} simulationId={simulationId} />
          {simulation.persona_group_id && (
            <ConvergencePanel
              projectId={projectId}
              personaGroupId={simulation.persona_group_id}
              briefingId={simulation.briefing_ids?.[0] ?? null}
            />
          )}
        </div>
      )}

      {/* Results */}
      {simulation?.status === "complete" && results && (
        <>
          {isConjoint ? (
            <ConjointReportView results={results} />
          ) : isFocusGroup ? (
            <FocusGroupReportView results={results} />
          ) : isSurvey ? (
            <SurveyReportView results={results} projectId={projectId} simulationId={simulationId} />
          ) : isIDI ? (
            <IDIReportView results={results} projectId={projectId} simulationId={simulationId} />
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
