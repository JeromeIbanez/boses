"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Sidebar nav definition
// ---------------------------------------------------------------------------

type NavItem =
  | { label: string; href: string; kind: "anchor" }
  | { label: string; href: string; kind: "route" }
  | { kind: "divider" };

const NAV_ITEMS: NavItem[] = [
  { label: "Workspace",     href: "#workspace",     kind: "anchor" },
  { label: "Team",          href: "#team",           kind: "anchor" },
  { label: "Notifications", href: "#notifications",  kind: "anchor" },
  { label: "Password",      href: "#password",       kind: "anchor" },
  { label: "API Keys",      href: "#api-keys",       kind: "anchor" },
  { kind: "divider" },
  { label: "Billing",       href: "/settings/billing", kind: "route" },
  { label: "Integrations",  href: "/integrations",     kind: "route" },
  { kind: "divider" },
  { label: "Danger Zone",   href: "#danger-zone",    kind: "anchor" },
];

// IDs that IntersectionObserver watches (same order as NAV_ITEMS anchors)
const SECTION_IDS = ["workspace", "team", "notifications", "password", "api-keys", "billing", "danger-zone"];

// ---------------------------------------------------------------------------
// Sidebar component
// ---------------------------------------------------------------------------

function SettingsSidebar() {
  const pathname = usePathname();
  const [activeAnchor, setActiveAnchor] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Only run IntersectionObserver when we're on the main settings page
  const isMainPage = pathname === "/settings";

  useEffect(() => {
    if (!isMainPage) return;

    const handleIntersect: IntersectionObserverCallback = (entries) => {
      // Pick the topmost visible section
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible.length > 0) {
        setActiveAnchor(`#${visible[0].target.id}`);
      }
    };

    observerRef.current = new IntersectionObserver(handleIntersect, {
      rootMargin: "-10% 0px -60% 0px",
      threshold: 0,
    });

    SECTION_IDS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observerRef.current!.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, [isMainPage]);

  const isActive = (item: NavItem & { kind: "anchor" | "route" }) => {
    if (item.kind === "route") {
      return pathname.startsWith(item.href);
    }
    // Anchor links are only "active" on the main settings page
    if (!isMainPage) return false;
    return activeAnchor === item.href;
  };

  return (
    <aside className="w-44 shrink-0 sticky top-8 self-start">
      <nav className="space-y-0.5">
        {NAV_ITEMS.map((item, i) => {
          if (item.kind === "divider") {
            return <div key={i} className="my-2 border-t border-zinc-100" />;
          }

          const active = isActive(item);
          const isDanger = item.label === "Danger Zone";

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-lg px-2.5 py-1.5 text-sm transition-colors ${
                active
                  ? isDanger
                    ? "bg-red-50 text-red-600 font-medium"
                    : "bg-zinc-100 text-zinc-900 font-medium"
                  : isDanger
                  ? "text-red-500 hover:bg-red-50 hover:text-red-600"
                  : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-8 px-8 py-8">
      <SettingsSidebar />
      <main className="flex-1 min-w-0 max-w-3xl">
        {children}
      </main>
    </div>
  );
}
