"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function BosesAdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!user?.is_boses_staff) router.replace("/dashboard");
  }, [user, isLoading, router]);

  if (isLoading || !user?.is_boses_staff) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="w-5 h-5 border-2 border-zinc-300 border-t-zinc-700 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="border-b border-amber-200 bg-amber-50 px-6 py-2">
        <span className="text-xs font-medium text-amber-700">Boses Admin — staff only</span>
      </div>
      {children}
    </div>
  );
}
