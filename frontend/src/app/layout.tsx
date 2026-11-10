// NOTICE: This file is protected under RCF-PL
import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { AuthProvider } from "@/providers/auth-provider";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/components/shell/ThemeProvider";

/* Fonts are vendored from @fontsource rather than fetched from Google at build
 * time. `next/font/google` downloads from fonts.gstatic.com while compiling, so
 * an offline host — or one bad request, which Turbopack then caches — fails the
 * build with "Can't resolve .../internal/font/google/font". Self-hosted files
 * keep the build reproducible and make no external requests at runtime. */
/* UI workhorse */
const inter = localFont({
  src: "../../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2",
  weight: "100 900",
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = localFont({
  src: "../../node_modules/@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2",
  weight: "100 800",
  variable: "--font-jetbrains",
  display: "swap",
});

/* Display faces — one per theme family */
const cormorant = localFont({
  src: [
    { path: "../../node_modules/@fontsource/cormorant-garamond/files/cormorant-garamond-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../node_modules/@fontsource/cormorant-garamond/files/cormorant-garamond-latin-500-italic.woff2", weight: "500", style: "italic" },
    { path: "../../node_modules/@fontsource/cormorant-garamond/files/cormorant-garamond-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../node_modules/@fontsource/cormorant-garamond/files/cormorant-garamond-latin-600-italic.woff2", weight: "600", style: "italic" },
  ],
  variable: "--font-cormorant",
  display: "swap",
});

const spectral = localFont({
  src: [
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-500-italic.woff2", weight: "500", style: "italic" },
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-600-italic.woff2", weight: "600", style: "italic" },
  ],
  variable: "--font-spectral",
  display: "swap",
});

const fraunces = localFont({
  src: [
    { path: "../../node_modules/@fontsource/fraunces/files/fraunces-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../node_modules/@fontsource/fraunces/files/fraunces-latin-600-normal.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AladdinAI",
  description: "Sovereign AI agents for sales, support, and operations.",
  icons: {
    icon: "/favicon.svg",
  },
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
      data-scroll-behavior="smooth"
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
