"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, MapPin, RefreshCw } from "lucide-react";
import { getAdminPersonas, retireAdminPersona, regenerateAdminAvatar } from "@/lib/api";
import type { LibraryPersona } from "@/types";

const SOURCE_TYPE_LABELS: Record<string, string> = {
  ethnographic: "Ethnographic",
  interview: "Interview",
  composite: "Composite",
};

function PersonaCard({ persona }: { persona: LibraryPersona }) {
  const qc = useQueryClient();
  const retireMut = useMutation({
    mutationFn: () => retireAdminPersona(persona.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-personas"] }),
  });
  const avatarMut = useMutation({
    mutationFn: () => regenerateAdminAvatar(persona.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-personas"] }),
  });

  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4 flex gap-4">
      <div className="shrink-0">
        {persona.avatar_url ? (
          <img
            src={persona.avatar_url}
            alt={persona.full_name}
            className="w-16 h-16 rounded-full object-cover border border-zinc-200"
          />
        ) : (
          <div className="w-16 h-16 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-400 text-xl font-medium">
            {persona.full_name[0]}
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-medium text-zinc-900 text-sm">{persona.full_name}</h3>
            <p className="text-xs text-zinc-500">
              {persona.age} · {persona.gender} · {persona.occupation}
            </p>
            <p className="text-xs text-zinc-400 flex items-center gap-1 mt-0.5">
              <MapPin size={10} /> {persona.location}
            </p>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {persona.source_type && (
              <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200">
                {SOURCE_TYPE_LABELS[persona.source_type] ?? persona.source_type}
              </span>
            )}
            {persona.is_retired && (
              <span className="px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-400 text-xs">Retired</span>
            )}
          </div>
        </div>
        {persona.archetype_label && (
          <p className="text-xs text-zinc-600 mt-1 italic">{persona.archetype_label}</p>
        )}
        {persona.research_notes && (
          <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{persona.research_notes}</p>
        )}
        <div className="flex items-center gap-2 mt-3">
          <Link
            href={`/boses-admin/personas/${persona.id}`}
            className="text-xs text-zinc-600 hover:text-zinc-900 underline underline-offset-2"
          >
            Edit
          </Link>
          <button
            onClick={() => avatarMut.mutate()}
            disabled={avatarMut.isPending}
            className="text-xs text-zinc-400 hover:text-zinc-700 flex items-center gap-1"
          >
            <RefreshCw size={11} className={avatarMut.isPending ? "animate-spin" : ""} />
            Regen avatar
          </button>
          {!persona.is_retired && (
            <button
              onClick={() => {
                if (confirm(`Retire ${persona.full_name}? They will no longer appear in user libraries.`))
                  retireMut.mutate();
              }}
              disabled={retireMut.isPending}
              className="text-xs text-red-400 hover:text-red-600"
            >
              Retire
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BosesAdminPage() {
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [showRetired, setShowRetired] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-personas", sourceFilter, showRetired],
    queryFn: () =>
      getAdminPersonas({
        curated_only: true,
        source_type: sourceFilter || undefined,
        is_retired: showRetired ? undefined : false,
        limit: 100,
      }),
  });

  const filtered = (data?.items ?? []).filter((p) =>
    search
      ? p.full_name.toLowerCase().includes(search.toLowerCase()) ||
        p.location.toLowerCase().includes(search.toLowerCase()) ||
        p.occupation.toLowerCase().includes(search.toLowerCase())
      : true
  );

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">Curated Personas</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {data?.total ?? 0} Boses-curated personas in the library
          </p>
        </div>
        <Link
          href="/boses-admin/personas/new"
          className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white text-sm rounded-md hover:bg-zinc-800 transition-colors"
        >
          <Plus size={15} />
          New Persona
        </Link>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search by name, location, occupation..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-zinc-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-zinc-300"
          />
        </div>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="text-sm border border-zinc-200 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-zinc-300"
        >
          <option value="">All sources</option>
          <option value="ethnographic">Ethnographic</option>
          <option value="interview">Interview</option>
          <option value="composite">Composite</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-zinc-500 cursor-pointer">
          <input
            type="checkbox"
            checked={showRetired}
            onChange={(e) => setShowRetired(e.target.checked)}
            className="rounded"
          />
          Show retired
        </label>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-5 h-5 border-2 border-zinc-300 border-t-zinc-700 rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-zinc-400">
          <p className="text-sm">No curated personas yet.</p>
          <Link
            href="/boses-admin/personas/new"
            className="text-sm text-zinc-600 underline underline-offset-2 mt-1 inline-block"
          >
            Create the first one
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((p) => (
            <PersonaCard key={p.id} persona={p} />
          ))}
        </div>
      )}
    </div>
  );
}
