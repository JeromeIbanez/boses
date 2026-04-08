"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import Badge from "@/components/ui/Badge";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import LibraryBadge from "@/components/ui/LibraryBadge";
import Modal from "@/components/ui/Modal";
import { Persona } from "@/types";

interface PersonaDetailModalProps {
  persona: Persona | null;
  onClose: () => void;
  onDelete?: (personaId: string) => void;
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] uppercase tracking-widest text-zinc-400 font-medium mb-2 mt-5 first:mt-0">
      {children}
    </p>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="mb-3">
      <p className="text-[11px] font-medium text-zinc-500 mb-0.5">{label}</p>
      <p className="text-xs text-zinc-700 leading-relaxed">{value}</p>
    </div>
  );
}

export default function PersonaDetailModal({ persona, onClose, onDelete }: PersonaDetailModalProps) {
  const [confirmPending, setConfirmPending] = useState<{ message: string; action: () => void } | null>(null);

  if (!persona) return null;

  return (
    <>
    <ConfirmDialog
      open={confirmPending !== null}
      message={confirmPending?.message ?? ""}
      onConfirm={() => confirmPending?.action()}
      onClose={() => setConfirmPending(null)}
    />
    <Modal open={!!persona} onClose={onClose} title="" width="max-w-2xl">
      {/* Scrollable body */}
      <div className="-mx-6 -my-5 overflow-y-auto max-h-[80vh] px-6 py-5">

        {/* Header */}
        <div className="flex items-start gap-4 mb-5">
          <div className="w-12 h-12 rounded-full bg-zinc-800 text-white flex items-center justify-center text-lg font-semibold shrink-0">
            {persona.full_name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h2 className="text-sm font-semibold text-zinc-900">{persona.full_name}</h2>
              {persona.library_persona_id && <LibraryBadge />}
            </div>
            <p className="text-xs text-zinc-500 mb-2">
              {persona.age} · {persona.gender} · {persona.location} · <span className="font-mono text-zinc-300">#{persona.persona_code}</span>
            </p>
            <div className="flex flex-wrap gap-1.5">
              {persona.archetype_label && (
                <Badge variant="default">{persona.archetype_label}</Badge>
              )}
              {persona.psychographic_segment && (
                <Badge variant="default">{persona.psychographic_segment}</Badge>
              )}
              <Badge variant="default">{persona.income_level}</Badge>
            </div>
          </div>
        </div>

        <div className="border-t border-zinc-100 pt-4">

          {/* WHO THEY ARE */}
          <SectionHeader>Who They Are</SectionHeader>
          <Field label="Occupation" value={persona.occupation} />
          <Field label="Education" value={persona.educational_background} />
          <Field label="Family & Household" value={persona.family_situation} />

          {persona.personality_traits && persona.personality_traits.length > 0 && (
            <div className="mb-3">
              <p className="text-[11px] font-medium text-zinc-500 mb-1.5">Personality Traits</p>
              <div className="flex flex-wrap gap-1">
                {persona.personality_traits.map((t) => (
                  <Badge key={t} variant="default">{t}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* WHAT DRIVES THEM */}
          <SectionHeader>What Drives Them</SectionHeader>
          <Field label="Values & Motivations" value={persona.values_and_motivations} />
          <Field label="Aspirational Identity" value={persona.aspirational_identity} />
          <Field label="Pain Points" value={persona.pain_points} />
          <Field label="Buying Triggers" value={persona.buying_triggers} />

          {/* BRANDS & MEDIA */}
          <SectionHeader>Brands & Media</SectionHeader>
          <Field label="Brand Attitudes" value={persona.brand_attitudes} />
          <Field label="Media Consumption" value={persona.media_consumption} />
          <Field label="Digital Behavior" value={persona.digital_behavior} />
          <Field label="Purchase Behavior" value={persona.purchase_behavior} />

          {/* A DAY IN THEIR LIFE */}
          {persona.day_in_the_life && (
            <>
              <SectionHeader>A Day in Their Life</SectionHeader>
              <p className="text-xs text-zinc-600 italic leading-relaxed mb-3">
                &ldquo;{persona.day_in_the_life}&rdquo;
              </p>
            </>
          )}

          {/* DATA SOURCES */}
          {persona.data_source_references && persona.data_source_references.length > 0 && (
            <>
              <SectionHeader>Data Sources</SectionHeader>
              <ul className="space-y-0.5 mb-4">
                {persona.data_source_references.map((ref) => (
                  <li key={ref} className="text-[10px] text-zinc-400 leading-relaxed">· {ref}</li>
                ))}
              </ul>
            </>
          )}

          {/* ACTIONS */}
          {onDelete && (
            <div className="border-t border-zinc-100 pt-4 mt-2">
              <button
                onClick={() => {
                  setConfirmPending({ message: `Delete ${persona.full_name}?`, action: () => { onDelete(persona.id); onClose(); } });
                }}
                className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 transition-colors"
              >
                <Trash2 size={13} /> Delete Persona
              </button>
            </div>
          )}

        </div>
      </div>
    </Modal>
    </>
  );
}
