/**
 * Catch-all API proxy — browser talks to /api/** on the Start origin;
 * this forwards to API_BASE_URL (server env only, never VITE_*).
 */
import { createFileRoute } from "@tanstack/react-router";

import {
  ProxyRejectedError,
  proxyToUpstream,
  resolveApiBaseUrl,
} from "@/server/api-proxy";

async function handle({
  request,
  params,
}: {
  request: Request;
  params: { _splat?: string };
}): Promise<Response> {
  try {
    const apiBaseUrl = resolveApiBaseUrl();
    const appOrigin = new URL(request.url).origin;
    const pathSuffix = params._splat ?? "";
    return await proxyToUpstream(request, {
      apiBaseUrl,
      pathSuffix,
      appOrigin,
    });
  } catch (error) {
    if (error instanceof ProxyRejectedError) {
      return Response.json(
        {
          error: {
            code: error.code,
            message: error.message,
            correlationId: request.headers.get("x-correlation-id") ?? "proxy",
          },
        },
        { status: error.status },
      );
    }
    throw error;
  }
}

export const Route = createFileRoute("/api/$")({
  server: {
    handlers: {
      GET: handle,
      HEAD: handle,
      POST: handle,
      PUT: handle,
      PATCH: handle,
      DELETE: handle,
      OPTIONS: handle,
    },
  },
});
