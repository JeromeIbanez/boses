"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Sparkles, Loader2 } from "lucide-react";
import Link from "next/link";
import { createAdminPersona, generateAdminPersonaFromNotes } from "@/lib/api";

type Mode = "manual" | "ai";

const FIELD_GROUPS = [
  {
    label: "Core",
    fields: [
      { key: "educational_background", label: "Educational Background" },
      { key: "family_situation", label: "Family Situation" },
      { key: "background", label: "Background (2-3 sentences)", multiline: true },
    ],
  },
  {
    label: "Psychographics",
    fields: [
      { key: "archetype_label", label: "Archetype Label" },
      { key: "psychographic_segment", label: "Psychographic Segment (VALS)" },
      { key: "personality_traits", label: "Personality Traits (comma-separated)", isTraits: true },
      { key: "aspirational_identity", label: "Aspirational Identity", multiline: true },
    ],
  },
  {
    label: "Behaviors",
    fields: [
      { key: "media_consumption", label: "Media Consumption", multiline: true },
      { key: "digital_behavior", label: "Digital Behavior", multiline: true },
      { key: "spending_habits", label: "Spending Habits", multiline: true },
      { key: "tech_savviness", label: "Tech Savviness" },
    ],
  },
  {
    label: "Market Insights",
    fields: [
      { key: "goals", label: "Goals", multiline: true },
      { key: "pain_points", label: "Pain Points", multiline: true },
      { key: "brand_attitudes", label: "Brand Attitudes", multiline: true },
      { key: "buying_triggers", label: "Buying Triggers", multiline: true },
      { key: "day_in_the_life", label: "Day in the Life", multiline: true },
    ],
  },
];

function FieldInput({
  fieldKey,
  label,
  multiline,
  isTraits,
  value,
  onChange,
}: {
  fieldKey: string;
  label: string;
  multiline?: boolean;
  isTraits?: boolean;
  value: string;
  onChange: (v: string) => void;
}) {
  const base =
    "w-full text-sm border border-zinc-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-zinc-300";
  if (multiline) {
    return (
      <textarea
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={isTraits ? "e.g. ambitious, skeptical, impulsive, status-conscious, risk-averse" : ""}
        className={`${base} resize-y`}
      />
    );
  }
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={base}
    />
  );
}

export default function NewCuratedPersonaPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("ai");

  // Shared demographics
  const [fullName, setFullName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [location, setLocation] = useState("");
  const [occupation, setOccupation] = useState("");
  const [incomeLevel, setIncomeLevel] = useState("");
  const [sourceType, setSourceType] = useState("composite");
  const [researchNotes, setResearchNotes] = useState("");

  // Manual-mode fields
  const [fields, setFields] = useState<Record<string, string>>({});
  const setField = (key: string, val: string) => setFields((prev) => ({ ...prev, [key]: val }));

  const aiMutation = useMutation({
    mutationFn: () =>
      generateAdminPersonaFromNotes({
        full_name: fullName,
        age: parseInt(age, 10),
        gender,
        location,
        occupation,
        income_level: incomeLevel,
        research_notes: researchNotes,
        source_type: sourceType,
      }),
    onSuccess: (p) => router.push(`/boses-admin/personas/${p.id}`),
  });

  const manualMutation = useMutation({
    mutationFn: () => {
      const traitsRaw = fields["personality_traits"] || "";
      const traits = traitsRaw
        ? traitsRaw.split(",").map((t) => t.trim()).filter(Boolean)
        : undefined;
      return createAdminPersona({
        full_name: fullName,
        age: parseInt(age, 10),
        gender,
        location,
        occupation,
        income_level: incomeLevel,
        source_type: sourceType,
        research_notes: researchNotes || undefined,
        ...Object.fromEntries(
          Object.entries(fields)
            .filter(([k, v]) => k !== "personality_traits" && v.trim())
        ),
        ...(traits ? { personality_traits: traits } : {}),
      } as Parameters<typeof createAdminPersona>[0]);
    },
    onSuccess: (p) => router.push(`/boses-admin/personas/${p.id}`),
  });

  const demographicsComplete =
    fullName && age && gender && location && occupation && incomeLevel;

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/boses-admin"
          className="text-zinc-400 hover:text-zinc-700 transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <h1 className="text-xl font-semibold text-zinc-900">New Curated Persona</h1>
      </div>

      {/* Mode toggle */}
      <div className="flex bg-zinc-100 rounded-lg p-1 mb-6 w-fit">
        <button
          onClick={() => setMode("ai")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === "ai" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
          }`}
        >
          <Sparkles size={14} />
          AI-assisted (recommended)
        </button>
        <button
          onClick={() => setMode("manual")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === "manual" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
          }`}
        >
          Manual entry
        </button>
      </div>

      <div className="space-y-5">
        {/* Demographics — always shown */}
        <section>
          <h2 className="text-sm font-medium text-zinc-700 mb-3">Demographics</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-zinc-500 mb-1 block">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Maria Santos"
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Age</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="28"
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-white"
              >
                <option value="">Select…</option>
                <option value="Female">Female</option>
                <option value="Male">Male</option>
                <option value="Non-binary">Non-binary</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Ortigas, Metro Manila"
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Occupation</label>
              <input
                type="text"
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                placeholder="e.g. Customer Service Rep"
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Income Level</label>
              <select
                value={incomeLevel}
                onChange={(e) => setIncomeLevel(e.target.value)}
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-white"
              >
                <option value="">Select…</option>
                <option value="Low">Low</option>
                <option value="Lower-middle">Lower-middle</option>
                <option value="Middle">Middle</option>
                <option value="Upper-middle">Upper-middle</option>
                <option value="High">High</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Source Type</label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-white"
              >
                <option value="composite">Composite</option>
                <option value="ethnographic">Ethnographic</option>
                <option value="interview">Interview</option>
              </select>
            </div>
          </div>
        </section>

        {/* Research notes — shown in both modes */}
        <section>
          <label className="text-xs text-zinc-500 mb-1 block">
            Research Notes {mode === "ai" && <span className="text-red-400">*</span>}
          </label>
          <p className="text-xs text-zinc-400 mb-2">
            {mode === "ai"
              ? "Paste your field notes, interview excerpts, or observations. GPT-4o will use these as the primary source to build the full profile."
              : "Optional internal notes for your reference (not shown to users)."}
          </p>
          <textarea
            rows={6}
            value={researchNotes}
            onChange={(e) => setResearchNotes(e.target.value)}
            placeholder={
              mode === "ai"
                ? "e.g. Interviewed at a sari-sari store in Ortigas. Works as a CSR at a BPO, 7am–4pm shift. Sends ~₱5,000/month to province. Uses GCash daily. Watches Netflix on phone during commute. Brand-loyal to Pantene but switches to Palmolive when budget is tight. Anxious about job security after automation news…"
                : "Optional field notes for internal reference…"
            }
            className="w-full text-sm border border-zinc-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-zinc-300 resize-y"
          />
        </section>

        {/* Manual-mode additional fields */}
        {mode === "manual" && (
          <>
            {FIELD_GROUPS.map((group) => (
              <section key={group.label}>
                <h2 className="text-sm font-medium text-zinc-700 mb-3">{group.label}</h2>
                <div className="space-y-3">
                  {group.fields.map((f) => (
                    <div key={f.key}>
                      <label className="text-xs text-zinc-500 mb-1 block">{f.label}</label>
                      <FieldInput
                        fieldKey={f.key}
                        label={f.label}
                        multiline={f.multiline}
                        isTraits={f.isTraits}
                        value={fields[f.key] ?? ""}
                        onChange={(v) => setField(f.key, v)}
                      />
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </>
        )}

        {/* Submit */}
        {mode === "ai" ? (
          <button
            onClick={() => aiMutation.mutate()}
            disabled={!demographicsComplete || !researchNotes || aiMutation.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 text-white text-sm rounded-md hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {aiMutation.isPending ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                Generating profile…
              </>
            ) : (
              <>
                <Sparkles size={15} />
                Generate Full Profile with AI
              </>
            )}
          </button>
        ) : (
          <button
            onClick={() => manualMutation.mutate()}
            disabled={!demographicsComplete || manualMutation.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 text-white text-sm rounded-md hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {manualMutation.isPending ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                Saving…
              </>
            ) : (
              "Save Persona"
            )}
          </button>
        )}

        {(aiMutation.error || manualMutation.error) && (
          <p className="text-sm text-red-600">
            {(aiMutation.error as Error)?.message || (manualMutation.error as Error)?.message}
          </p>
        )}
      </div>
    </div>
  );
}
