"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { BookMarked, Search, Trash2, X } from "lucide-react";
import { getLibraryPersonas, getLibraryPersona, deleteLibraryPersona, deleteAllLibraryPersonas } from "@/lib/api";
import type { LibraryPersona } from "@/types";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Modal from "@/components/ui/Modal";
import PageHeader from "@/components/layout/PageHeader";
import Spinner from "@/components/ui/Spinner";

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

interface Filters {
  location: string;
  gender: string;
  income_level: string;
  age_min: string;
  age_max: string;
}

const defaultFilters: Filters = {
  location: "",
  gender: "",
  income_level: "",
  age_min: "",
  age_max: "",
};

// ---------------------------------------------------------------------------
// Persona detail modal
// ---------------------------------------------------------------------------

function PersonaDetailModal({
  personaId,
  onClose,
}: {
  personaId: string;
  onClose: () => void;
}) {
  const { data: p, isLoading } = useQuery({
    queryKey: ["library-persona", personaId],
    queryFn: () => getLibraryPersona(personaId),
  });

  return (
    <Modal open onClose={onClose} title={p?.full_name ?? "Loading…"} width="max-w-2xl">
      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}
      {p && (
        <div className="space-y-4 text-sm">
          {/* Header row */}
          <div className="flex flex-wrap gap-2">
            <Badge variant="default">{p.age} yrs</Badge>
            <Badge variant="default">{p.gender}</Badge>
            <Badge variant="default">{p.occupation}</Badge>
            <Badge variant="default">{p.location}</Badge>
            <Badge variant="default">{p.income_level}</Badge>
            {p.simulation_count > 0 && (
              <Badge variant="success">Used in {p.simulation_count} simulation{p.simulation_count !== 1 ? "s" : ""}</Badge>
            )}
          </div>

          {/* Traits */}
          {p.personality_traits && p.personality_traits.length > 0 && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Personality</p>
              <div className="flex flex-wrap gap-1">
                {p.personality_traits.map((t) => (
                  <Badge key={t} variant="default">{t}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Background */}
          {p.background && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Background</p>
              <p className="text-zinc-600 leading-relaxed">{p.background}</p>
            </div>
          )}

          {/* Pain points */}
          {p.pain_points && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Pain Points</p>
              <p className="text-zinc-600 leading-relaxed">{p.pain_points}</p>
            </div>
          )}

          {/* Media */}
          {p.media_consumption && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Media Consumption</p>
              <p className="text-zinc-600 leading-relaxed">{p.media_consumption}</p>
            </div>
          )}

          {/* Day in the life */}
          {p.day_in_the_life && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">A Day in the Life</p>
              <p className="text-zinc-600 leading-relaxed italic">{p.day_in_the_life}</p>
            </div>
          )}

          {/* Source citations */}
          {p.data_source_references && p.data_source_references.length > 0 && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Sources</p>
              <ul className="list-disc list-inside space-y-0.5">
                {p.data_source_references.map((ref, i) => (
                  <li key={i} className="text-xs text-zinc-400">{ref}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-xs text-zinc-300 pt-2 border-t border-zinc-100">
            Added {new Date(p.created_at).toLocaleDateString()}
          </p>
        </div>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Persona card
// ---------------------------------------------------------------------------

function LibraryPersonaCard({
  persona,
  onClick,
  onDelete,
}: {
  persona: LibraryPersona;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <Card onClick={onClick}>
      <div className="flex items-start gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-zinc-800 text-white flex items-center justify-center text-sm font-medium shrink-0">
          {persona.full_name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-zinc-900 truncate">{persona.full_name}</h3>
          <p className="text-xs text-zinc-400">{persona.age} · {persona.occupation}</p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm(`Delete ${persona.full_name} from the library?`)) onDelete();
          }}
          className="p-1 text-zinc-300 hover:text-red-500 transition-colors shrink-0"
          title="Delete persona"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        <Badge variant="default">{persona.income_level}</Badge>
        <Badge variant="default">{persona.location}</Badge>
      </div>

      {persona.personality_traits && persona.personality_traits.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {persona.personality_traits.slice(0, 3).map((t) => (
            <Badge key={t} variant="default">{t}</Badge>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-100">
        <span className="text-xs text-zinc-400 capitalize">{persona.data_source}</span>
        {persona.simulation_count > 0 ? (
          <span className="text-xs text-emerald-600 font-medium">
            {persona.simulation_count} simulation{persona.simulation_count !== 1 ? "s" : ""}
          </span>
        ) : (
          <span className="text-xs text-zinc-300">Not yet simulated</span>
        )}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function LibraryPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [activeFilters, setActiveFilters] = useState<Filters>(defaultFilters);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const qc = useQueryClient();

  const remove = useMutation({
    mutationFn: (id: string) => deleteLibraryPersona(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-personas"] }),
  });

  const removeAll = useMutation({
    mutationFn: () => deleteAllLibraryPersonas(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library-personas"] }),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["library-personas", activeFilters],
    queryFn: () =>
      getLibraryPersonas({
        location: activeFilters.location || undefined,
        gender: activeFilters.gender || undefined,
        income_level: activeFilters.income_level || undefined,
        age_min: activeFilters.age_min ? Number(activeFilters.age_min) : undefined,
        age_max: activeFilters.age_max ? Number(activeFilters.age_max) : undefined,
        limit: 60,
      }),
  });

  const applyFilters = () => setActiveFilters({ ...filters });
  const clearFilters = () => {
    setFilters(defaultFilters);
    setActiveFilters(defaultFilters);
  };
  const hasActiveFilters = Object.values(activeFilters).some((v) => v !== "");

  return (
    <div className="px-8 py-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Personas"
          description="Persistent personas built across all projects. Reused automatically when demographics match."
        />
        {data && data.total > 0 && (
          <button
            onClick={() => {
              if (confirm(`Permanently delete all ${data.total} persona(s) from the library?`)) removeAll.mutate();
            }}
            disabled={removeAll.isPending}
            className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 rounded-md px-3 py-1.5 transition-colors shrink-0 disabled:opacity-50"
          >
            <Trash2 size={13} /> Delete All
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-3 mb-6 p-4 bg-zinc-50 border border-zinc-200 rounded-lg">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500 font-medium">Location</label>
          <input
            className="text-sm border border-zinc-200 rounded-md px-3 py-1.5 w-44 focus:outline-none focus:ring-1 focus:ring-zinc-400"
            placeholder="e.g. Metro Manila"
            value={filters.location}
            onChange={(e) => setFilters({ ...filters, location: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && applyFilters()}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500 font-medium">Gender</label>
          <select
            className="text-sm border border-zinc-200 rounded-md px-3 py-1.5 w-32 focus:outline-none focus:ring-1 focus:ring-zinc-400 bg-white"
            value={filters.gender}
            onChange={(e) => setFilters({ ...filters, gender: e.target.value })}
          >
            <option value="">Any</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Non-binary">Non-binary</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500 font-medium">Income Level</label>
          <select
            className="text-sm border border-zinc-200 rounded-md px-3 py-1.5 w-40 focus:outline-none focus:ring-1 focus:ring-zinc-400 bg-white"
            value={filters.income_level}
            onChange={(e) => setFilters({ ...filters, income_level: e.target.value })}
          >
            <option value="">Any</option>
            <option value="Low">Low</option>
            <option value="Lower-middle">Lower-middle</option>
            <option value="Middle">Middle</option>
            <option value="Upper-middle">Upper-middle</option>
            <option value="High">High</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500 font-medium">Age range</label>
          <div className="flex items-center gap-1.5">
            <input
              type="number"
              className="text-sm border border-zinc-200 rounded-md px-2 py-1.5 w-16 focus:outline-none focus:ring-1 focus:ring-zinc-400"
              placeholder="Min"
              value={filters.age_min}
              onChange={(e) => setFilters({ ...filters, age_min: e.target.value })}
            />
            <span className="text-zinc-400 text-xs">–</span>
            <input
              type="number"
              className="text-sm border border-zinc-200 rounded-md px-2 py-1.5 w-16 focus:outline-none focus:ring-1 focus:ring-zinc-400"
              placeholder="Max"
              value={filters.age_max}
              onChange={(e) => setFilters({ ...filters, age_max: e.target.value })}
            />
          </div>
        </div>

        <button
          onClick={applyFilters}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-zinc-900 text-white text-sm rounded-md hover:bg-zinc-700 transition-colors"
        >
          <Search size={13} />
          Search
        </button>

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
          >
            <X size={12} />
            Clear
          </button>
        )}
      </div>

      {/* Stats row */}
      {data && (
        <p className="text-xs text-zinc-400 mb-5">
          {data.total} persona{data.total !== 1 ? "s" : ""} in library
          {hasActiveFilters && ` matching filters`}
        </p>
      )}

      {/* Grid */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-48 bg-zinc-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && data?.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <BookMarked size={32} className="text-zinc-200 mb-3" strokeWidth={1.5} />
          <p className="text-sm text-zinc-400">No personas in the library yet.</p>
          <p className="text-xs text-zinc-300 mt-1">
            Generate personas in a project and they'll appear here automatically.
          </p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((p) => (
            <LibraryPersonaCard
              key={p.id}
              persona={p}
              onClick={() => setSelectedId(p.id)}
              onDelete={() => remove.mutate(p.id)}
            />
          ))}
        </div>
      )}

      {selectedId && (
        <PersonaDetailModal
          personaId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
