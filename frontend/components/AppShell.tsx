"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Sidebar from "@/components/layout/Sidebar";

const AUTH_PATHS = ["/login", "/signup", "/forgot-password", "/reset-password"];
const PUBLIC_PATHS = ["/share"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const isAuthPage = AUTH_PATHS.some((p) => pathname.startsWith(p));
  const isPublicPage = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  useEffect(() => {
    if (isLoading) return;
    if (isPublicPage) return;
    // Authenticated user on an auth page → send to app
    if (isAuthPage && user) router.replace("/dashboard");
    // Unauthenticated user on a protected page → send to login
    if (!isAuthPage && !user) router.replace("/login");
  }, [user, isLoading, isAuthPage, isPublicPage, router]);

  // Auth pages: centered layout, no sidebar, no auth wait needed
  if (isAuthPage) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
        {children}
      </div>
    );
  }

  // Public pages (e.g. shared simulation results): no auth, no sidebar
  if (isPublicPage) {
    return <>{children}</>;
  }

  // Protected pages: wait for auth check to avoid flash of wrong content
  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-50">
        <div className="w-5 h-5 border-2 border-zinc-300 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
