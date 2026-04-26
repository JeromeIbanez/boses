"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import type { Persona, LibraryPersona } from "@/types";
import type { PersonaPDFData } from "./PersonaPDF";

const API_ROOT = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");

function resolveAvatarUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : API_ROOT + url;
}

async function fetchBase64(url: string): Promise<string | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const blob = await res.blob();
    return await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}

function toPersonaPDFData(p: Persona | LibraryPersona): PersonaPDFData {
  if ("persona_code" in p) {
    // Persona (project)
    return {
      full_name: p.full_name,
      age: p.age,
      gender: p.gender,
      location: p.location,
      occupation: p.occupation,
      income_level: p.income_level,
      educational_background: p.educational_background,
      family_situation: p.family_situation,
      personality_traits: p.personality_traits,
      archetype_label: p.archetype_label,
      psychographic_segment: p.psychographic_segment,
      code: p.persona_code,
      values_and_motivations: p.values_and_motivations,
      pain_points: p.pain_points,
      aspirational_identity: p.aspirational_identity,
      buying_triggers: p.buying_triggers,
      brand_attitudes: p.brand_attitudes,
      digital_behavior: p.digital_behavior,
      media_consumption: p.media_consumption,
      purchase_behavior: p.purchase_behavior,
      day_in_the_life: p.day_in_the_life,
      data_source_references: p.data_source_references,
      generated_at: p.created_at,
    };
  } else {
    // LibraryPersona
    const code = p.id.replace(/-/g, "").slice(-8).toUpperCase();
    return {
      full_name: p.full_name,
      age: p.age,
      gender: p.gender,
      location: p.location,
      occupation: p.occupation,
      income_level: p.income_level,
      educational_background: p.educational_background,
      family_situation: p.family_situation,
      personality_traits: p.personality_traits,
      archetype_label: p.archetype_label,
      psychographic_segment: p.psychographic_segment,
      code,
      background: p.background,
      goals: p.goals,
      pain_points: p.pain_points,
      aspirational_identity: p.aspirational_identity,
      buying_triggers: p.buying_triggers,
      brand_attitudes: p.brand_attitudes,
      digital_behavior: p.digital_behavior,
      media_consumption: p.media_consumption,
      spending_habits: p.spending_habits,
      tech_savviness: p.tech_savviness,
      day_in_the_life: p.day_in_the_life,
      data_source_references: p.data_source_references,
      generated_at: p.created_at,
    };
  }
}

interface Props {
  personas: (Persona | LibraryPersona)[];
  filename: string;
  label?: string;
}

export default function PersonaPDFButton({ personas, filename, label = "Export PDF" }: Props) {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      const [{ pdf }, { default: PersonasPDF }] = await Promise.all([
        import("@react-pdf/renderer"),
        import("./PersonaPDF"),
      ]);

      // Resolve avatars to base64 in parallel
      const pdfData: PersonaPDFData[] = await Promise.all(
        personas.map(async (p) => {
          const data = toPersonaPDFData(p);
          const avatarUrl = resolveAvatarUrl(p.avatar_url);
          data.avatarBase64 = avatarUrl ? await fetchBase64(avatarUrl) : null;
          return data;
        })
      );

      const blob = await pdf(<PersonasPDF personas={pdfData} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-800 border border-zinc-200 hover:border-zinc-400 rounded-md px-3 py-1.5 transition-colors shrink-0 disabled:opacity-50 bg-white"
    >
      {loading ? (
        <Loader2 size={13} className="animate-spin" />
      ) : (
        <Download size={13} />
      )}
      {loading ? "Generating…" : label}
    </button>
  );
}
