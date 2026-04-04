"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { getLibraryPersona, deleteLibraryPersona } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Spinner from "@/components/ui/Spinner";

const API_ROOT = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");

function avatarSrc(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : API_ROOT + url;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] uppercase tracking-widest text-zinc-400 font-semibold mb-3">
      {children}
    </p>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-[11px] font-medium text-zinc-400 mb-1">{label}</p>
      <p className="text-xs text-zinc-600 leading-relaxed">{value}</p>
    </div>
  );
}

function TwoColGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">{children}</div>;
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white border border-zinc-100 rounded-xl p-5">
      {children}
    </div>
  );
}

export default function LibraryPersonaProfilePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [imgError, setImgError] = useState(false);

  const { data: p, isLoading } = useQuery({
    queryKey: ["library-persona", id],
    queryFn: () => getLibraryPersona(id),
  });

  const remove = useMutation({
    mutationFn: () => deleteLibraryPersona(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["library-personas"] });
      router.push("/personas");
    },
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><Spinner /></div>;
  }

  if (!p) return null;

  const photo = !imgError ? avatarSrc(p.avatar_url) : null;
  const libraryCode = p.id.toString().replace(/-/g, "").slice(-8).toUpperCase();

  return (
    <div className="bg-zinc-50 min-h-screen">
      {/* Top bar */}
      <div className="bg-white border-b border-zinc-100 px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push("/personas")}
          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
        >
          <ArrowLeft size={13} />
          Back to Library
        </button>
        <span className="text-zinc-200">/</span>
        <span className="text-xs text-zinc-700 font-medium">{p.full_name}</span>
        <div className="ml-auto flex items-center gap-3">
          {p.simulation_count > 0 && (
            <span className="text-[11px] text-emerald-600 font-medium bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded">
              {p.simulation_count} simulation{p.simulation_count !== 1 ? "s" : ""}
            </span>
          )}
          <span className="font-mono text-[11px] text-zinc-400 bg-zinc-50 border border-zinc-100 px-2 py-0.5 rounded">
            #{libraryCode}
          </span>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 flex gap-6 items-start">

        {/* ── LEFT SIDEBAR ── */}
        <div className="w-60 shrink-0 space-y-4 sticky top-8">

          {/* Photo + identity */}
          <div className="bg-white border border-zinc-100 rounded-xl overflow-hidden">
            <div className="aspect-square bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center">
              {photo ? (
                <img
                  src={photo}
                  alt={p.full_name}
                  className="w-full h-full object-cover"
                  onError={() => setImgError(true)}
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-zinc-700 flex items-center justify-center text-4xl font-semibold text-white">
                  {p.full_name.charAt(0)}
                </div>
              )}
            </div>
            <div className="px-4 pt-4 pb-3">
              <h1 className="text-sm font-semibold text-zinc-900 leading-tight">{p.full_name}</h1>
              <p className="text-[11px] text-zinc-400 mt-0.5">{p.age} · {p.gender} · {p.location}</p>
              <div className="mt-2">
                <span className="font-mono text-[10px] text-zinc-400 bg-zinc-50 border border-zinc-100 px-1.5 py-0.5 rounded">
                  #{libraryCode}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-3">
                {p.archetype_label && <Badge variant="default">{p.archetype_label}</Badge>}
                {p.psychographic_segment && <Badge variant="default">{p.psychographic_segment}</Badge>}
              </div>
            </div>
          </div>

          {/* At a glance */}
          <Card>
            <SectionLabel>At a Glance</SectionLabel>
            <div className="space-y-2.5">
              <div className="flex justify-between items-baseline gap-2">
                <span className="text-[11px] text-zinc-400 shrink-0">Occupation</span>
                <span className="text-[11px] text-zinc-700 font-medium text-right leading-snug">{p.occupation}</span>
              </div>
              <div className="flex justify-between items-baseline gap-2">
                <span className="text-[11px] text-zinc-400 shrink-0">Income</span>
                <span className="text-[11px] text-zinc-700 font-medium">{p.income_level}</span>
              </div>
              {p.educational_background && (
                <div className="flex justify-between items-baseline gap-2">
                  <span className="text-[11px] text-zinc-400 shrink-0">Education</span>
                  <span className="text-[11px] text-zinc-700 font-medium text-right leading-snug">{p.educational_background}</span>
                </div>
              )}
              {p.family_situation && (
                <div className="flex justify-between items-baseline gap-2">
                  <span className="text-[11px] text-zinc-400 shrink-0">Family</span>
                  <span className="text-[11px] text-zinc-700 font-medium text-right leading-snug">{p.family_situation}</span>
                </div>
              )}
              <div className="flex justify-between items-baseline gap-2">
                <span className="text-[11px] text-zinc-400 shrink-0">Source</span>
                <span className="text-[11px] text-zinc-700 font-medium capitalize">{p.data_source}</span>
              </div>
            </div>
          </Card>

          {/* Personality */}
          {p.personality_traits && p.personality_traits.length > 0 && (
            <Card>
              <SectionLabel>Personality</SectionLabel>
              <div className="flex flex-wrap gap-1.5">
                {p.personality_traits.map((t) => (
                  <Badge key={t} variant="default">{t}</Badge>
                ))}
              </div>
            </Card>
          )}

          {/* Actions */}
          <Card>
            <button
              onClick={() => {
                if (confirm(`Delete ${p.full_name} from the library? This cannot be undone.`)) remove.mutate();
              }}
              disabled={remove.isPending}
              className="w-full flex items-center justify-center gap-2 text-red-400 hover:text-red-600 text-xs font-medium py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Trash2 size={13} />
              Delete from Library
            </button>
          </Card>
        </div>

        {/* ── MAIN CONTENT ── */}
        <div className="flex-1 min-w-0 space-y-4">

          <Card>
            <SectionLabel>Who They Are</SectionLabel>
            <TwoColGrid>
              <Field label="Background" value={p.background} />
              <Field label="Goals" value={p.goals} />
              <Field label="Aspirational Identity" value={p.aspirational_identity} />
              <Field label="Pain Points" value={p.pain_points} />
            </TwoColGrid>
          </Card>

          <Card>
            <SectionLabel>Brands & Digital Life</SectionLabel>
            <TwoColGrid>
              <Field label="Brand Attitudes" value={p.brand_attitudes} />
              <Field label="Digital Behavior" value={p.digital_behavior} />
              <Field label="Media Consumption" value={p.media_consumption} />
              <Field label="Spending Habits" value={p.spending_habits} />
              <Field label="Buying Triggers" value={p.buying_triggers} />
              <Field label="Tech Savviness" value={p.tech_savviness} />
            </TwoColGrid>
          </Card>

          {p.day_in_the_life && (
            <Card>
              <SectionLabel>A Day in Their Life</SectionLabel>
              <blockquote className="border-l-2 border-zinc-200 pl-4">
                <p className="text-sm text-zinc-600 italic leading-relaxed">&ldquo;{p.day_in_the_life}&rdquo;</p>
              </blockquote>
            </Card>
          )}

          {p.data_source_references && p.data_source_references.length > 0 && (
            <Card>
              <SectionLabel>Grounding Sources</SectionLabel>
              <ul className="space-y-1">
                {p.data_source_references.map((ref) => (
                  <li key={ref} className="text-[11px] text-zinc-400 leading-relaxed">· {ref}</li>
                ))}
              </ul>
            </Card>
          )}

          <p className="text-[10px] text-zinc-300 text-right">
            Added {new Date(p.created_at).toLocaleDateString()}
            {p.updated_at !== p.created_at && ` · Updated ${new Date(p.updated_at).toLocaleDateString()}`}
          </p>
        </div>
      </div>
    </div>
  );
}
