"use client";

import { BookMarked } from "lucide-react";

interface LibraryBadgeProps {
  simulationCount?: number;
  matchScore?: number | null;
}

export default function LibraryBadge({ simulationCount, matchScore }: LibraryBadgeProps) {
  const label = simulationCount
    ? `From Library · used in ${simulationCount} study${simulationCount !== 1 ? "s" : ""}`
    : "From Library";

  const scoreLabel = matchScore != null ? ` · ${Math.round(matchScore * 100)}% match` : "";

  return (
    <span
      title={label + scoreLabel}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-600 border border-blue-100"
    >
      <BookMarked size={10} strokeWidth={2} />
      Library
      {matchScore != null && (
        <span className="text-blue-400">{Math.round(matchScore * 100)}%</span>
      )}
    </span>
  );
}
