import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a minimal self-contained server in .next/standalone for Docker images.
  // No effect on dev (`next dev`) or non-Docker workflows.
  output: "standalone",
  images: {
    unoptimized: true,
  },
  // API proxying is handled by src/app/api/[...path]/route.ts at runtime,
  // so BACKEND_INTERNAL_URL is read per-request (not baked in at build time).
};

export default nextConfig;
