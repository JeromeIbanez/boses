import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import Providers from "@/components/Providers";

export const metadata: Metadata = {
  title: "Boses — Market Simulation",
  description: "Simulate how real people would react to your product launch",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden bg-zinc-50">
        <Providers>
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
