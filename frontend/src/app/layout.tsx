import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pattern Proof — Dark Pattern Audit",
  description: "Detect and report dark patterns on any website",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <header className="border-b border-zinc-800 px-6 py-4">
          <a href="/" className="text-xl font-bold tracking-tight">
            Pattern<span className="text-indigo-400">Proof</span>
          </a>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
