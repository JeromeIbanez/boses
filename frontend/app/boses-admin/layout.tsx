"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

const NAV = [
  { href: "/boses-admin", label: "Personas" },
  { href: "/boses-admin/invites", label: "Invites" },
];

export default function BosesAdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

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
      <div className="border-b border-amber-200 bg-amber-50 px-6 py-2 flex items-center gap-6">
        <span className="text-xs font-medium text-amber-700">Boses Admin — staff only</span>
        <nav className="flex items-center gap-4">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-xs font-medium ${
                pathname === href ? "text-amber-900 underline underline-offset-2" : "text-amber-600 hover:text-amber-900"
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
      {children}
    </div>
  );
}
