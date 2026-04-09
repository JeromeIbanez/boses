"use client";

import { ShieldCheck } from "lucide-react";

export default function CuratedBadge() {
  return (
    <span
      title="Boses-curated persona — built on real field research"
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200"
    >
      <ShieldCheck size={10} strokeWidth={2} />
      Boses Curated
    </span>
  );
}
