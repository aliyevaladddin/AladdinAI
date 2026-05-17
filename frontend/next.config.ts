import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a minimal self-contained server in .next/standalone for Docker images.
  // No effect on dev (`next dev`) or non-Docker workflows.
  output: "standalone",
  images: {
    unoptimized: true,
  },
  async rewrites() {
    // Server-side proxy target. In Docker this is the backend service hostname;
    // for local dev it falls back to localhost. The browser-facing
    // NEXT_PUBLIC_API_URL is unrelated and stays as it is.
    const target = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
