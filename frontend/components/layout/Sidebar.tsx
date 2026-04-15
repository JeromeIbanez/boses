"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, FolderOpen, BookMarked, LogOut, FileText, Puzzle, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";

const nav = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Projects", href: "/projects", icon: FolderOpen },
  { label: "Personas", href: "/personas", icon: BookMarked },
];

const bottomNav = [
  { label: "Integrations", href: "/integrations", icon: Puzzle },
  { label: "API Docs", href: "https://docs.temujintechnologies.com", icon: FileText, external: true },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <aside className="w-56 shrink-0 border-r border-zinc-200 bg-white flex flex-col h-screen sticky top-0">
      <div className="px-5 py-5 border-b border-zinc-200">
        <span className="font-semibold text-zinc-900 tracking-tight text-lg">Boses</span>
        <p className="text-xs text-zinc-400 mt-0.5">Market Simulation</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
              pathname.startsWith(href)
                ? "bg-indigo-50 text-indigo-700 font-medium"
                : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800"
            )}
          >
            <Icon size={16} strokeWidth={1.8} />
            {label}
          </Link>
        ))}
        {user?.is_boses_staff && (
          <div className="pt-3 mt-3 border-t border-zinc-100 space-y-0.5">
            <Link
              href="/boses-admin"
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                pathname.startsWith("/boses-admin")
                  ? "bg-amber-50 text-amber-800 font-medium"
                  : "text-amber-600 hover:bg-amber-50 hover:text-amber-800"
              )}
            >
              <ShieldCheck size={16} strokeWidth={1.8} />
              Boses Admin
            </Link>
          </div>
        )}
        <div className="pt-3 mt-3 border-t border-zinc-100 space-y-0.5">
          {bottomNav.map(({ label, href, icon: Icon, external }) =>
            external ? (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800"
              >
                <Icon size={16} strokeWidth={1.8} />
                {label}
              </a>
            ) : (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                  pathname.startsWith(href)
                    ? "bg-indigo-50 text-indigo-700 font-medium"
                    : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800"
                )}
              >
                <Icon size={16} strokeWidth={1.8} />
                {label}
              </Link>
            )
          )}
        </div>
      </nav>
      <div className="px-4 py-4 border-t border-zinc-200 space-y-2">
        {user && (
          <div className="px-1">
            <p className="text-xs font-medium text-zinc-700 truncate">{user.full_name || user.email}</p>
            <p className="text-xs text-zinc-400 truncate">{user.company.name}</p>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 w-full px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-700 hover:bg-zinc-50 transition-colors"
        >
          <LogOut size={13} strokeWidth={1.8} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
