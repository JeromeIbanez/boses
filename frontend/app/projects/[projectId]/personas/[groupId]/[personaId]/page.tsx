"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { getPersona, deletePersona } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import LibraryBadge from "@/components/ui/LibraryBadge";
import Spinner from "@/components/ui/Spinner";
import PersonaPDFButton from "@/components/personas/PersonaPDFButton";

const API_ROOT = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");

function avatarSrc(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http")) return url;
  return API_ROOT + url;
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

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white border border-zinc-100 rounded-xl p-5 ${className}`}>
      {children}
    </div>
  );
}

export default function PersonaProfilePage() {
  const { projectId, groupId, personaId } = useParams<{
    projectId: string;
    groupId: string;
    personaId: string;
  }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [imgError, setImgError] = useState(false);
  const [confirmPending, setConfirmPending] = useState<{ message: string; action: () => void } | null>(null);

  const { data: persona, isLoading } = useQuery({
    queryKey: ["persona", personaId],
    queryFn: () => getPersona(projectId, groupId, personaId),
  });

  const remove = useMutation({
    mutationFn: () => deletePersona(projectId, groupId, personaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas", groupId] });
      router.push(`/projects/${projectId}/personas/${groupId}`);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (!persona) return null;

  const photo = !imgError ? avatarSrc(persona.avatar_url) : null;

  return (
    <div className="bg-zinc-50 min-h-screen">
      <ConfirmDialog
        open={confirmPending !== null}
        message={confirmPending?.message ?? ""}
        onConfirm={() => confirmPending?.action()}
        onClose={() => setConfirmPending(null)}
      />
      {/* Top bar */}
      <div className="bg-white border-b border-zinc-100 px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push(`/projects/${projectId}/personas/${groupId}`)}
          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
        >
          <ArrowLeft size={13} />
          Back to group
        </button>
        <span className="text-zinc-200">/</span>
        <span className="text-xs text-zinc-700 font-medium">{persona.full_name}</span>
        <div className="ml-auto flex items-center gap-2">
          <PersonaPDFButton
            personas={[persona]}
            filename={`${persona.persona_code}.pdf`}
          />
          <span className="font-mono text-[11px] text-zinc-400 bg-zinc-50 border border-zinc-100 px-2 py-0.5 rounded">
            #{persona.persona_code}
          </span>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 flex gap-6 items-start">

        {/* ── LEFT SIDEBAR ── */}
        <div className="w-60 shrink-0 space-y-4 sticky top-8">

          {/* Photo + name card */}
          <div className="bg-white border border-zinc-100 rounded-xl overflow-hidden">
            {/* Photo */}
            <div className="aspect-square bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center relative">
              {photo ? (
                <img
                  src={photo}
                  alt={persona.full_name}
                  className="w-full h-full object-cover"
                  onError={() => setImgError(true)}
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-zinc-700 flex items-center justify-center text-4xl font-semibold text-white">
                  {persona.full_name.charAt(0)}
                </div>
              )}
            </div>

            {/* Identity */}
            <div className="px-4 pt-4 pb-3">
              <div className="flex items-center gap-2 flex-wrap mb-0.5">
                <h1 className="text-sm font-semibold text-zinc-900">{persona.full_name}</h1>
                {persona.library_persona_id && <LibraryBadge />}
              </div>
              <p className="text-[11px] text-zinc-400">
                {persona.age} · {persona.gender} · {persona.location}
              </p>
              <div className="mt-2">
                <span className="font-mono text-[10px] text-zinc-400 bg-zinc-50 border border-zinc-100 px-1.5 py-0.5 rounded">
                  #{persona.persona_code}
                </span>
              </div>

              {/* Archetype badges */}
              <div className="flex flex-wrap gap-1.5 mt-3">
                {persona.archetype_label && (
                  <Badge variant="default">{persona.archetype_label}</Badge>
                )}
                {persona.psychographic_segment && (
                  <Badge variant="default">{persona.psychographic_segment}</Badge>
                )}
              </div>
            </div>
          </div>

          {/* At a glance */}
          <Card>
            <SectionLabel>At a Glance</SectionLabel>
            <div className="space-y-2.5">
              <div className="flex justify-between items-baseline gap-2">
                <span className="text-[11px] text-zinc-400 shrink-0">Occupation</span>
                <span className="text-[11px] text-zinc-700 font-medium text-right leading-snug">{persona.occupation}</span>
              </div>
              <div className="flex justify-between items-baseline gap-2">
                <span className="text-[11px] text-zinc-400 shrink-0">Income</span>
                <span className="text-[11px] text-zinc-700 font-medium text-right">{persona.income_level}</span>
              </div>
              {persona.educational_background && (
                <div className="flex justify-between items-baseline gap-2">
                  <span className="text-[11px] text-zinc-400 shrink-0">Education</span>
                  <span className="text-[11px] text-zinc-700 font-medium text-right leading-snug">{persona.educational_background}</span>
                </div>
              )}
              {persona.family_situation && (
                <div className="flex justify-between items-baseline gap-2">
                  <span className="text-[11px] text-zinc-400 shrink-0">Family</span>
                  <span className="text-[11px] text-zinc-700 font-medium text-right leading-snug">{persona.family_situation}</span>
                </div>
              )}
            </div>
          </Card>

          {/* Personality traits */}
          {persona.personality_traits && persona.personality_traits.length > 0 && (
            <Card>
              <SectionLabel>Personality</SectionLabel>
              <div className="flex flex-wrap gap-1.5">
                {persona.personality_traits.map((t) => (
                  <Badge key={t} variant="default">{t}</Badge>
                ))}
              </div>
            </Card>
          )}

          {/* Actions */}
          <Card>
            <button
              onClick={() => {
                setConfirmPending({ message: `Delete ${persona.full_name}? This cannot be undone.`, action: () => remove.mutate() });
              }}
              disabled={remove.isPending}
              className="w-full flex items-center justify-center gap-2 text-red-400 hover:text-red-600 text-xs font-medium py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Trash2 size={13} />
              Delete Persona
            </button>
          </Card>
        </div>

        {/* ── MAIN CONTENT ── */}
        <div className="flex-1 min-w-0 space-y-4">

          {/* What Drives Them */}
          <Card>
            <SectionLabel>What Drives Them</SectionLabel>
            <TwoColGrid>
              <Field label="Values & Motivations" value={persona.values_and_motivations} />
              <Field label="Aspirational Identity" value={persona.aspirational_identity} />
              <Field label="Pain Points" value={persona.pain_points} />
              <Field label="Buying Triggers" value={persona.buying_triggers} />
            </TwoColGrid>
          </Card>

          {/* Brands & Digital Life */}
          <Card>
            <SectionLabel>Brands & Digital Life</SectionLabel>
            <TwoColGrid>
              <Field label="Brand Attitudes" value={persona.brand_attitudes} />
              <Field label="Digital Behavior" value={persona.digital_behavior} />
              <Field label="Media Consumption" value={persona.media_consumption} />
              <Field label="Purchase Behavior" value={persona.purchase_behavior} />
            </TwoColGrid>
          </Card>

          {/* A Day in Their Life */}
          {persona.day_in_the_life && (
            <Card>
              <SectionLabel>A Day in Their Life</SectionLabel>
              <blockquote className="border-l-2 border-zinc-200 pl-4">
                <p className="text-sm text-zinc-600 italic leading-relaxed">
                  &ldquo;{persona.day_in_the_life}&rdquo;
                </p>
              </blockquote>
            </Card>
          )}

          {/* Data Sources */}
          {persona.data_source_references && persona.data_source_references.length > 0 && (
            <Card>
              <SectionLabel>Grounding Sources</SectionLabel>
              <ul className="space-y-1">
                {persona.data_source_references.map((ref) => (
                  <li key={ref} className="text-[11px] text-zinc-400 leading-relaxed">
                    · {ref}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
