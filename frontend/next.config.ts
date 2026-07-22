// NOTICE: This file is protected under RCF-PL
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a minimal self-contained server in .next/standalone for Docker images.
  // No effect on dev (`next dev`) or non-Docker workflows.
  output: "standalone",
  images: {
    unoptimized: true,
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts", "@base-ui/react"],
  },
  // API proxying is handled by src/app/api/[...path]/route.ts at runtime,
  // so BACKEND_INTERNAL_URL is read per-request (not baked in at build time).

  // react-markdown v10+ and its entire unified/remark/rehype ecosystem are
  // ESM-only packages. transpilePackages tells Next.js to run them through
  // its own Webpack/SWC bundler so they resolve correctly in both SSR and client.
  transpilePackages: [
    "react-markdown",
    "remark-parse",
    "remark-rehype",
    "unified",
    "bail",
    "is-plain-obj",
    "trough",
    "vfile",
    "vfile-message",
    "unist-util-stringify-position",
    "mdast-util-from-markdown",
    "mdast-util-to-hast",
    "mdast-util-to-string",
    "mdast-util-definitions",
    "micromark",
    "micromark-util-combine-extensions",
    "micromark-util-chunked",
    "micromark-util-decode-string",
    "micromark-util-decode-numeric-character-reference",
    "micromark-util-character",
    "micromark-util-sanitize-uri",
    "micromark-util-html-tag-name",
    "micromark-util-classify-character",
    "micromark-util-resolve-all",
    "micromark-util-subtokenize",
    "micromark-util-normalize-identifier",
    "micromark-core-commonmark",
    "decode-named-character-reference",
    "character-entities",
    "hast-util-to-jsx-runtime",
    "hast-util-whitespace",
    "hast-util-to-html",
    "hast-util-raw",
    "hast-util-from-parse5",
    "hast-util-is-element",
    "hastscript",
    "property-information",
    "space-separated-tokens",
    "comma-separated-tokens",
    "unist-util-is",
    "unist-util-visit",
    "unist-util-visit-parents",
    "unist-util-position",
    "unist-util-generated",
    "unist-util-remove-position",
    "trim-lines",
    "ccount",
    "html-void-elements",
    "web-namespaces",
    "zwitch",
    "stringify-entities",
  ],
};

export default nextConfig;
