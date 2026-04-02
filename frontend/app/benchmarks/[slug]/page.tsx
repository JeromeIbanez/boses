"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FlaskConical, CheckCircle, BookOpen } from "lucide-react";
import { getBenchmarkCase, getPersonaGroups, getProjects, getMyBenchmarkRuns, runBenchmark } from "@/lib/api";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";

const SENTIMENT_STYLES: Record<string, { bg: string; text: string; bar: string }> = {
  Positive: { bg: "bg-emerald-50 border-emerald-100", text: "text-emerald-700", bar: "bg-emerald-400" },
  Neutral:  { bg: "bg-zinc-50 border-zinc-100",       text: "text-zinc-600",   bar: "bg-zinc-300" },
  Negative: { bg: "bg-red-50 border-red-100",         text: "text-red-700",    bar: "bg-red-400" },
};

function ScoreBreakdownPanel({ breakdown }: { breakdown: Record<string, unknown> }) {
  const direction = breakdown.direction_match as boolean | null;
  const dirScore = breakdown.direction_score as number | null;
  const distScore = breakdown.distribution_accuracy_score as number | null;
  const themeScore = breakdown.theme_overlap_score as number | null;
  const overall = breakdown.overall_accuracy_score as number | null;
  const predictedSentiment = breakdown.predicted_sentiment as string | null;
  const actualSentiment = breakdown.actual_sentiment as string | null;
  const predictedThemes = breakdown.predicted_themes as string[] | null;
  const actualThemes = breakdown.actual_themes as string[] | null;

  return (
    <Card className="space-y-4">
      <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide">Your Score</h3>
      {overall != null && (
        <div className="text-center">
          <p className={`text-4xl font-bold ${overall >= 0.8 ? "text-emerald-600" : overall >= 0.6 ? "text-amber-600" : "text-red-500"}`}>
            {Math.round(overall * 100)}%
          </p>
          <p className="text-xs text-zinc-400 mt-1">Overall accuracy</p>
        </div>
      )}

      <div className="space-y-3">
        {/* Sentiment direction */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-zinc-500">Sentiment direction (40%)</p>
            <span className={`text-xs font-medium ${direction ? "text-emerald-600" : "text-red-500"}`}>
              {direction ? "✓ Match" : "✗ Miss"}
            </span>
          </div>
          {predictedSentiment && actualSentiment && (
            <p className="text-xs text-zinc-400">
              Predicted: <span className="font-medium text-zinc-600">{predictedSentiment}</span>
              {" · "}
              Actual: <span className="font-medium text-zinc-600">{actualSentiment}</span>
            </p>
          )}
        </div>

        {/* Distribution accuracy */}
        {distScore != null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs text-zinc-500">Distribution accuracy (35%)</p>
              <span className="text-xs font-medium text-zinc-600">{Math.round(distScore * 100)}%</span>
            </div>
            <div className="bg-zinc-100 rounded-full h-1.5 overflow-hidden">
              <div className="bg-zinc-600 h-1.5 rounded-full" style={{ width: `${Math.round(distScore * 100)}%` }} />
            </div>
          </div>
        )}

        {/* Theme overlap */}
        {themeScore != null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs text-zinc-500">Theme overlap (25%)</p>
              <span className="text-xs font-medium text-zinc-600">{Math.round(themeScore * 100)}%</span>
            </div>
            <div className="bg-zinc-100 rounded-full h-1.5 overflow-hidden">
              <div className="bg-zinc-600 h-1.5 rounded-full" style={{ width: `${Math.round(themeScore * 100)}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* Themes comparison */}
      {(predictedThemes || actualThemes) && (
        <div className="grid grid-cols-2 gap-3 border-t border-zinc-100 pt-3">
          {predictedThemes && predictedThemes.length > 0 && (
            <div>
              <p className="text-xs font-medium text-zinc-500 mb-1">Your themes</p>
              <div className="space-y-1">
                {predictedThemes.map(t => (
                  <p key={t} className="text-xs text-zinc-600 bg-zinc-50 rounded px-1.5 py-0.5">{t}</p>
                ))}
              </div>
            </div>
          )}
          {actualThemes && actualThemes.length > 0 && (
            <div>
              <p className="text-xs font-medium text-zinc-500 mb-1">Actual themes</p>
              <div className="space-y-1">
                {actualThemes.map(t => (
                  <p key={t} className="text-xs text-zinc-600 bg-zinc-50 rounded px-1.5 py-0.5">{t}</p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default function BenchmarkDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [selectedGroupId, setSelectedGroupId] = useState<string>("");

  const { data: benchmarkCase, isLoading } = useQuery({
    queryKey: ["benchmark-case", slug],
    queryFn: () => getBenchmarkCase(slug),
  });

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: getProjects,
  });

  const { data: groups } = useQuery({
    queryKey: ["persona-groups", selectedProjectId],
    queryFn: () => getPersonaGroups(selectedProjectId),
    enabled: !!selectedProjectId,
  });

  const { data: myRuns } = useQuery({
    queryKey: ["benchmark-runs"],
    queryFn: getMyBenchmarkRuns,
    refetchInterval: (q) => {
      const pending = (q.state.data || []).some(r => r.benchmark_case_slug === slug && r.status === "pending");
      return pending ? 5000 : false;
    },
  });

  const latestRun = (myRuns ?? [])
    .filter(r => r.benchmark_case_slug === slug)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

  const run = useMutation({
    mutationFn: () => runBenchmark(slug, { persona_group_id: selectedGroupId, project_id: selectedProjectId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["benchmark-runs"] });
      setSelectedGroupId("");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner className="h-6 w-6 border-zinc-200 border-t-zinc-600" />
      </div>
    );
  }

  if (!benchmarkCase) {
    return <div className="px-8 py-8 text-sm text-zinc-500">Benchmark case not found.</div>;
  }

  const sentimentStyle = SENTIMENT_STYLES[benchmarkCase.ground_truth.sentiment] ?? SENTIMENT_STYLES.Neutral;
  const gt = benchmarkCase.ground_truth;

  return (
    <div className="px-8 py-8 max-w-4xl">
      <button
        onClick={() => router.push("/benchmarks")}
        className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 mb-5 transition-colors"
      >
        <ArrowLeft size={13} /> Back to Benchmarks
      </button>

      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <FlaskConical size={18} className="text-zinc-600" />
          <h1 className="text-xl font-semibold text-zinc-900">{benchmarkCase.title}</h1>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${sentimentStyle.bg} ${sentimentStyle.text}`}>
            {gt.sentiment}
          </span>
        </div>
        <p className="text-sm text-zinc-500">{benchmarkCase.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ground truth */}
        <div className="space-y-4">
          <Card className="space-y-4">
            <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide flex items-center gap-2">
              <BookOpen size={14} /> Known Outcome
            </h3>

            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">What actually happened</p>
              <p className="text-sm text-zinc-700 leading-relaxed">{gt.outcome_summary}</p>
            </div>

            {gt.positive_pct != null && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Real sentiment breakdown</p>
                <div className="space-y-1.5">
                  {[
                    { label: "Positive", pct: gt.positive_pct ?? 0, bar: "bg-emerald-400" },
                    { label: "Neutral",  pct: gt.neutral_pct ?? 0,  bar: "bg-zinc-300" },
                    { label: "Negative", pct: gt.negative_pct ?? 0, bar: "bg-red-400" },
                  ].map(({ label, pct, bar }) => (
                    <div key={label} className="flex items-center gap-2 text-xs">
                      <span className="text-zinc-500 w-14">{label}</span>
                      <div className="flex-1 bg-zinc-100 rounded-full h-1.5 overflow-hidden">
                        <div className={`${bar} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-zinc-400 w-8 text-right">{pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {gt.top_themes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Documented themes</p>
                <div className="flex flex-wrap gap-1.5">
                  {gt.top_themes.map(t => (
                    <span key={t} className="text-xs bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full">{t}</span>
                  ))}
                </div>
              </div>
            )}

            {benchmarkCase.source_citations && benchmarkCase.source_citations.length > 0 && (
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Sources</p>
                <ul className="space-y-0.5">
                  {benchmarkCase.source_citations.map((c, i) => (
                    <li key={i} className="text-xs text-zinc-400">{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* Run form */}
          <Card className="space-y-3">
            <h3 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide">Run this benchmark</h3>
            <p className="text-xs text-zinc-500">
              Select a persona group to simulate against this case. Boses will run a concept test using the documented briefing and score it against the known outcome.
            </p>

            <div className="space-y-2">
              <div>
                <label className="text-xs font-medium text-zinc-600 block mb-1">Project</label>
                <select
                  value={selectedProjectId}
                  onChange={e => { setSelectedProjectId(e.target.value); setSelectedGroupId(""); }}
                  className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 bg-white text-zinc-700 focus:outline-none focus:ring-1 focus:ring-zinc-400"
                >
                  <option value="">Select project…</option>
                  {(projects ?? []).map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {selectedProjectId && (
                <div>
                  <label className="text-xs font-medium text-zinc-600 block mb-1">Persona Group</label>
                  <select
                    value={selectedGroupId}
                    onChange={e => setSelectedGroupId(e.target.value)}
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 bg-white text-zinc-700 focus:outline-none focus:ring-1 focus:ring-zinc-400"
                  >
                    <option value="">Select persona group…</option>
                    {(groups ?? [])
                      .filter(g => g.generation_status === "complete")
                      .map(g => (
                        <option key={g.id} value={g.id}>{g.name}</option>
                      ))}
                  </select>
                </div>
              )}

              <button
                onClick={() => run.mutate()}
                disabled={!selectedGroupId || !selectedProjectId || run.isPending}
                className="w-full flex items-center justify-center gap-2 text-sm font-medium bg-zinc-900 text-white py-2 rounded-lg hover:bg-zinc-700 disabled:opacity-40 transition-colors"
              >
                {run.isPending ? (
                  <><Spinner className="h-3.5 w-3.5 border-zinc-400 border-t-white" /> Running…</>
                ) : (
                  <><FlaskConical size={14} /> Run benchmark</>
                )}
              </button>

              {latestRun?.status === "pending" && (
                <p className="text-xs text-amber-600 text-center">Simulation in progress…</p>
              )}
            </div>
          </Card>
        </div>

        {/* Score breakdown (if run is complete) */}
        <div>
          {latestRun?.status === "complete" && latestRun.score_breakdown ? (
            <ScoreBreakdownPanel breakdown={latestRun.score_breakdown} />
          ) : latestRun?.status === "pending" ? (
            <Card className="flex flex-col items-center justify-center py-12 space-y-3">
              <Spinner className="h-6 w-6 border-zinc-200 border-t-zinc-600" />
              <p className="text-sm text-zinc-500">Simulation running…</p>
              <p className="text-xs text-zinc-400">Results will appear here when complete.</p>
            </Card>
          ) : (
            <Card className="flex flex-col items-center justify-center py-12 space-y-2">
              <CheckCircle size={28} className="text-zinc-200" />
              <p className="text-sm text-zinc-400">Your accuracy score will appear here after running the benchmark.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
