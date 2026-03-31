// AppShell handles auth page layout (centered, no sidebar).
// This layout is a passthrough to avoid double-wrapping.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
