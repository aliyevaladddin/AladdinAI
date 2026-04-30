import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/providers/auth-provider";

export const metadata: Metadata = {
  title: "AladdinAI | SOVEREIGN_CMD",
  description: "AI Agent Orchestration Platform protected by RCF Protocol",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
      </head>
      <body className="h-full w-full bg-background text-on-background overflow-hidden flex flex-col bg-grid-pattern selection:bg-cyan-500/30">
        <AuthProvider>
          <div className="flex h-full w-full overflow-hidden">
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
