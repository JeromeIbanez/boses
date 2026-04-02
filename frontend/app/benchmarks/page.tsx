"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical, ExternalLink, TrendingUp, CheckCircle, XCircle, Clock } from "lucide-react";
import { getBenchmarkCases, getMyBenchmarkRuns } from "@/lib/api";
import Card from "@/components/ui/Card";

const CATEGORY_LABELS: Record<string, string> = {
  product_launch: "Product Launch",
  ad_campaign: "Ad Campaign",
  brand_perception: "Brand Perception",
};

const SENTIMENT_STYLES: Record<string, { bg: string; text: string }> = {
  Positive: { bg: "bg-emerald-50 border-emerald-100", text: "text-emerald-700" },
  Neutral:  { bg: "bg-zinc-50 border-zinc-100",       text: "text-zinc-600" },
  Negative: { bg: "bg-red-50 border-red-100",         text: "text-red-700" },
};

function AccuracyBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "text-emerald-700" : pct >= 60 ? "text-amber-600" : "text-red-500";
  return <span className={`text-sm font-bold ${color}`}>{pct}%</span>;
}

function RunStatusIcon({ status }: { status: string }) {
  if (status === "complete") return <CheckCircle size={14} className="text-emerald-500" />;
  if (status === "failed") return <XCircle size={14} className="text-red-400" />;
  return <Clock size={14} className="text-zinc-400" />;
}

export default function BenchmarksPage() {
  const { data: cases, isLoading: loadingCases } = useQuery({
    queryKey: ["benchmark-cases"],
    queryFn: getBenchmarkCases,
  });

  const { data: runs } = useQuery({
    queryKey: ["benchmark-runs"],
    queryFn: getMyBenchmarkRuns,
    refetchInterval: (q) => {
      const pending = (q.state.data || []).some(r => r.status === "pending");
      return pending ? 5000 : false;
    },
  });

  return (
    <div className="px-8 py-8 max-w-4xl">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <FlaskConical size={20} className="text-zinc-600" />
          <h1 className="text-xl font-semibold text-zinc-900">Validation Library</h1>
        </div>
        <p className="text-sm text-zinc-500 max-w-xl">
          Run Boses against historical cases where real consumer research outcomes are documented. See how accurately the platform predicts known results.
        </p>
      </div>

      {/* Benchmark cases grid */}
      {loadingCases ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-36 bg-zinc-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          {(cases ?? []).map(c => {
            const sentimentStyle = SENTIMENT_STYLES[c.ground_truth.sentiment] ?? SENTIMENT_STYLES.Neutral;
            const myRun = (runs ?? []).find(r => r.benchmark_case_slug === c.slug && r.status === "complete");
            return (
              <Card key={c.slug} className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs text-zinc-400 mb-0.5">{CATEGORY_LABELS[c.category] ?? c.category}</p>
                    <p className="text-sm font-semibold text-zinc-900">{c.title}</p>
                  </div>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border shrink-0 ${sentimentStyle.bg} ${sentimentStyle.text}`}>
                    {c.ground_truth.sentiment}
                  </span>
                </div>

                <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">
                  {c.ground_truth.outcome_summary}
                </p>

                <div className="flex items-center justify-between pt-1 border-t border-zinc-100">
                  {myRun && myRun.overall_accuracy_score != null ? (
                    <div className="flex items-center gap-1.5 text-xs text-zinc-500">
                      <CheckCircle size={12} className="text-emerald-500" />
                      Your score: <AccuracyBadge score={myRun.overall_accuracy_score} />
                    </div>
                  ) : (
                    <span className="text-xs text-zinc-400">Not yet run</span>
                  )}
                  <Link
                    href={`/benchmarks/${c.slug}`}
                    className="flex items-center gap-1 text-xs font-medium text-zinc-700 hover:text-zinc-900 transition-colors"
                  >
                    Run benchmark <ExternalLink size={11} />
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Your past runs */}
      {(runs ?? []).length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <TrendingUp size={14} /> Your Runs
          </h2>
          <div className="border border-zinc-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left text-xs font-medium text-zinc-500 px-4 py-2.5">Case</th>
                  <th className="text-left text-xs font-medium text-zinc-500 px-4 py-2.5">Status</th>
                  <th className="text-left text-xs font-medium text-zinc-500 px-4 py-2.5">Accuracy</th>
                  <th className="text-left text-xs font-medium text-zinc-500 px-4 py-2.5">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {(runs ?? []).map(run => (
                  <tr key={run.id}>
                    <td className="px-4 py-2.5">
                      <Link href={`/benchmarks/${run.benchmark_case_slug}`} className="text-zinc-700 hover:text-zinc-900">
                        {run.benchmark_case_title ?? run.benchmark_case_slug}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <RunStatusIcon status={run.status} />
                        <span className="text-xs text-zinc-500 capitalize">{run.status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      {run.overall_accuracy_score != null
                        ? <AccuracyBadge score={run.overall_accuracy_score} />
                        : <span className="text-xs text-zinc-400">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-zinc-400">
                      {new Date(run.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
