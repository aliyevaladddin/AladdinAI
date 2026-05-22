import type { Metadata } from "next";
import {
  Inter,
  JetBrains_Mono,
  Cormorant_Garamond,
  Spectral,
  Fraunces,
} from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/providers/auth-provider";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/components/shell/ThemeProvider";

/* UI workhorse */
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

/* Display faces — one per theme family */
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600"],
  style: ["normal", "italic"],
  variable: "--font-cormorant",
  display: "swap",
});

const spectral = Spectral({
  subsets: ["latin"],
  weight: ["500", "600"],
  style: ["normal", "italic"],
  variable: "--font-spectral",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AladdinAI",
  description: "Sovereign AI agents for sales, support, and operations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const fontClasses = [
    inter.variable,
    jetbrainsMono.variable,
    cormorant.variable,
    spectral.variable,
    fraunces.variable,
  ].join(" ");

  return (
    <html
      lang="en"
      className={`${fontClasses} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Apply persisted theme before paint to avoid a flash of the default. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="h-full w-full">
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
