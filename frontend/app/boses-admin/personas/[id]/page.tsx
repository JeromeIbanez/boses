"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw, Loader2, Save } from "lucide-react";
import Link from "next/link";
import { getAdminPersona, updateAdminPersona, regenerateAdminAvatar, retireAdminPersona } from "@/lib/api";
import type { LibraryPersona } from "@/types";

const EDITABLE_FIELDS: { key: keyof LibraryPersona; label: string; multiline?: boolean; isTraits?: boolean }[] = [
  { key: "full_name", label: "Full Name" },
  { key: "age", label: "Age" },
  { key: "gender", label: "Gender" },
  { key: "location", label: "Location" },
  { key: "occupation", label: "Occupation" },
  { key: "income_level", label: "Income Level" },
  { key: "source_type", label: "Source Type" },
  { key: "archetype_label", label: "Archetype Label" },
  { key: "psychographic_segment", label: "Psychographic Segment" },
  { key: "personality_traits", label: "Personality Traits (comma-separated)", isTraits: true },
  { key: "educational_background", label: "Educational Background", multiline: true },
  { key: "family_situation", label: "Family Situation", multiline: true },
  { key: "background", label: "Background", multiline: true },
  { key: "goals", label: "Goals", multiline: true },
  { key: "pain_points", label: "Pain Points", multiline: true },
  { key: "tech_savviness", label: "Tech Savviness" },
  { key: "media_consumption", label: "Media Consumption", multiline: true },
  { key: "spending_habits", label: "Spending Habits", multiline: true },
  { key: "brand_attitudes", label: "Brand Attitudes", multiline: true },
  { key: "buying_triggers", label: "Buying Triggers", multiline: true },
  { key: "aspirational_identity", label: "Aspirational Identity", multiline: true },
  { key: "digital_behavior", label: "Digital Behavior", multiline: true },
  { key: "day_in_the_life", label: "Day in the Life", multiline: true },
  { key: "research_notes", label: "Research Notes (internal)", multiline: true },
];

function toDisplayValue(key: keyof LibraryPersona, value: unknown): string {
  if (key === "personality_traits" && Array.isArray(value)) return value.join(", ");
  if (value === null || value === undefined) return "";
  return String(value);
}

function toSubmitValue(key: keyof LibraryPersona, raw: string): unknown {
  if (key === "personality_traits") {
    return raw ? raw.split(",").map((t) => t.trim()).filter(Boolean) : [];
  }
  if (key === "age") return parseInt(raw, 10) || 0;
  return raw || null;
}

export default function EditCuratedPersonaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();

  const { data: persona, isLoading } = useQuery({
    queryKey: ["admin-persona", id],
    queryFn: () => getAdminPersona(id),
  });

  const [draft, setDraft] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!persona) return;
    const initial: Record<string, string> = {};
    EDITABLE_FIELDS.forEach(({ key }) => {
      initial[key as string] = toDisplayValue(key, persona[key]);
    });
    setDraft(initial);
    setDirty(false);
  }, [persona]);

  const setField = (key: string, val: string) => {
    setDraft((prev) => ({ ...prev, [key]: val }));
    setDirty(true);
  };

  const saveMut = useMutation({
    mutationFn: () => {
      const body: Partial<LibraryPersona> = {};
      EDITABLE_FIELDS.forEach(({ key }) => {
        (body as Record<string, unknown>)[key as string] = toSubmitValue(key, draft[key as string] ?? "");
      });
      return updateAdminPersona(id, body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-persona", id] });
      qc.invalidateQueries({ queryKey: ["admin-personas"] });
      setDirty(false);
    },
  });

  const avatarMut = useMutation({
    mutationFn: () => regenerateAdminAvatar(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-persona", id] }),
  });

  const retireMut = useMutation({
    mutationFn: () => retireAdminPersona(id),
    onSuccess: () => router.push("/boses-admin"),
  });

  if (isLoading || !persona) {
    return (
      <div className="flex h-full items-center justify-center py-24">
        <div className="w-5 h-5 border-2 border-zinc-300 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/boses-admin" className="text-zinc-400 hover:text-zinc-700">
          <ArrowLeft size={18} />
        </Link>
        <h1 className="text-xl font-semibold text-zinc-900">{persona.full_name}</h1>
        {persona.is_retired && (
          <span className="px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-400 text-xs">Retired</span>
        )}
      </div>

      {/* Avatar */}
      <div className="flex items-center gap-4 mb-6 p-4 bg-white border border-zinc-200 rounded-lg">
        {persona.avatar_url ? (
          <img
            src={persona.avatar_url}
            alt={persona.full_name}
            className="w-20 h-20 rounded-full object-cover border border-zinc-200"
          />
        ) : (
          <div className="w-20 h-20 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-400 text-2xl font-medium">
            {persona.full_name[0]}
          </div>
        )}
        <div>
          <p className="text-sm text-zinc-500 mb-2">
            {persona.avatar_url ? "Avatar generated" : "No avatar yet"}
          </p>
          <button
            onClick={() => avatarMut.mutate()}
            disabled={avatarMut.isPending}
            className="flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-900 border border-zinc-200 rounded-md px-3 py-1.5 bg-white hover:bg-zinc-50 transition-colors"
          >
            <RefreshCw size={12} className={avatarMut.isPending ? "animate-spin" : ""} />
            {avatarMut.isPending ? "Generating…" : "Regenerate Avatar"}
          </button>
        </div>
      </div>

      {/* Fields */}
      <div className="space-y-4">
        {EDITABLE_FIELDS.map(({ key, label, multiline, isTraits }) => (
          <div key={key as string}>
            <label className="text-xs text-zinc-500 mb-1 block">{label}</label>
            {multiline ? (
              <textarea
                rows={3}
                value={draft[key as string] ?? ""}
                onChange={(e) => setField(key as string, e.target.value)}
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300 resize-y"
              />
            ) : (
              <input
                type={key === "age" ? "number" : "text"}
                value={draft[key as string] ?? ""}
                onChange={(e) => setField(key as string, e.target.value)}
                placeholder={isTraits ? "ambitious, skeptical, impulsive…" : ""}
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300"
              />
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mt-8 pt-6 border-t border-zinc-200">
        {!persona.is_retired ? (
          <button
            onClick={() => {
              if (confirm(`Retire ${persona.full_name}? They will no longer appear in user libraries.`))
                retireMut.mutate();
            }}
            disabled={retireMut.isPending}
            className="text-sm text-red-500 hover:text-red-700"
          >
            Retire persona
          </button>
        ) : (
          <span className="text-sm text-zinc-400">This persona is retired</span>
        )}
        <button
          onClick={() => saveMut.mutate()}
          disabled={!dirty || saveMut.isPending}
          className="flex items-center gap-2 px-5 py-2 bg-indigo-500 text-white text-sm rounded-[10px] hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {saveMut.isPending ? (
            <>
              <Loader2 size={14} className="animate-spin" /> Saving…
            </>
          ) : (
            <>
              <Save size={14} /> Save Changes
            </>
          )}
        </button>
      </div>

      {saveMut.error && (
        <p className="text-sm text-red-600 mt-3">{(saveMut.error as Error).message}</p>
      )}
    </div>
  );
}
