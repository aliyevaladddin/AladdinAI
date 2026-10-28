// NOTICE: This file is protected under RCF-PL
/**
 * Runtime reverse proxy for all /api/* requests → backend.
 *
 * next.config.ts `rewrites()` is evaluated at build time, so
 * BACKEND_INTERNAL_URL injected by Render at runtime never reaches it.
 * A Route Handler runs per-request and reads env vars at runtime.
 */
import { NextRequest, NextResponse } from "next/server";


function getBackendUrl(): string {
  const explicitInternal = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL;
  let url = explicitInternal || "";
  if (!url) {
    const publicApi = (process.env.NEXT_PUBLIC_API_URL || "").trim();
    if (publicApi.startsWith("http://") || publicApi.startsWith("https://")) {
      url = publicApi.replace(/\/api\/?$/, "");
    } else {
      url = "http://127.0.0.1:8000";
    }
  }
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    url = `https://${url}`;
  }
  // Prefer IPv4 loopback over "localhost" in Node fetch to avoid ::1 ECONNREFUSED
  // when uvicorn binds 0.0.0.0 (IPv4) only.
  url = url.replace(/^http:\/\/localhost(?=[:/]|$)/i, "http://127.0.0.1");
  // Remove trailing slash
  return url.replace(/\/$/, "");
}


async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  try {
    const { path } = await params;
    const backend = getBackendUrl();
    const targetPath = path.join("/");

    // Preserve query string
    const search = req.nextUrl.search ?? "";
    const targetUrl = `${backend}/api/${targetPath}${search}`;

    // Forward headers, excluding host (which must match the target)
    const headers = new Headers(req.headers);
    headers.delete("host");

    let body: BodyInit | null = null;
    const method = req.method.toUpperCase();
    if (!["GET", "HEAD"].includes(method)) {
      try {
        body = await req.arrayBuffer();
      } catch (bodyErr) {
        console.warn("[api-proxy] Could not read request body for %s %s:", method, targetUrl, bodyErr);
      }
    }

    const upstream = await fetch(targetUrl, {
      method,
      headers,
      body: body ?? undefined,
      // @ts-expect-error — Node 18+ fetch supports this, not in TS types yet
      duplex: "half",
    });

    const resHeaders = new Headers(upstream.headers);
    // Don't forward encoding and length headers — Next.js handles that
    resHeaders.delete("content-encoding");
    resHeaders.delete("transfer-encoding");
    resHeaders.delete("content-length");

    const contentType = upstream.headers.get("content-type") || "";
    if (contentType.includes("text/event-stream") && upstream.body) {
      resHeaders.set("Cache-Control", "no-cache, no-transform");
      resHeaders.set("X-Accel-Buffering", "no");
      return new NextResponse(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: resHeaders,
      });
    }

    // Read body fully in-memory to prevent stream truncation issues
    const resBody = await upstream.arrayBuffer();

    return new NextResponse(resBody, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: resHeaders,
    });
  } catch (err) {
    console.error(`[api-proxy] Critical proxy failure:`, err);
    return NextResponse.json(
      { detail: "Internal proxy error", error: String(err) },
      { status: 502 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
