/**
 * Phase 12.1 spike — prove SSE and multipart bodies pass a Node fetch proxy
 * without buffering. Used by the /api/$ catch-all once the spike passes.
 */
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

export class ProxyRejectedError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ProxyRejectedError";
    this.code = code;
    this.status = status;
  }
}

export function resolveApiBaseUrl(
  env: NodeJS.ProcessEnv = process.env,
): string {
  const raw = env["API_BASE_URL"]?.trim();
  if (!raw) {
    throw new ProxyRejectedError(
      "misconfigured",
      "API_BASE_URL is not set on the server.",
      500,
    );
  }
  if (raw.startsWith("VITE_")) {
    throw new ProxyRejectedError(
      "misconfigured",
      "API_BASE_URL must not be a VITE_* value.",
      500,
    );
  }
  return raw.replace(/\/$/, "");
}

export function assertSameOrigin(request: Request, appOrigin: string): void {
  if (request.method === "GET" || request.method === "HEAD") {
    return;
  }
  const origin = request.headers.get("origin");
  if (!origin || origin !== appOrigin) {
    throw new ProxyRejectedError(
      "csrf_rejected",
      "Cross-origin mutation rejected.",
      403,
    );
  }
}

function filterRequestHeaders(headers: Headers): Headers {
  const out = new Headers();
  headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) {
      return;
    }
    out.set(key, value);
  });
  return out;
}

function filterResponseHeaders(headers: Headers): Headers {
  const out = new Headers();
  headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) {
      return;
    }
    out.set(key, value);
  });
  return out;
}

export type FetchLike = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;

/**
 * Forward a browser request to the FastAPI origin without buffering the body
 * or the response stream.
 */
export async function proxyToUpstream(
  request: Request,
  options: {
    apiBaseUrl: string;
    pathSuffix: string;
    appOrigin: string;
    fetchImpl?: FetchLike;
  },
): Promise<Response> {
  const { apiBaseUrl, pathSuffix, appOrigin, fetchImpl = fetch } = options;
  assertSameOrigin(request, appOrigin);

  const suffix = pathSuffix.replace(/^\//, "");
  const target = `${apiBaseUrl.replace(/\/$/, "")}/api/${suffix}${
    new URL(request.url).search
  }`;

  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers: filterRequestHeaders(request.headers),
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    // Pass the body through as a stream — never arrayBuffer()/text().
    init.body = request.body;
    init.duplex = "half";
  }

  const upstream = await fetchImpl(target, init);
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: filterResponseHeaders(upstream.headers),
  });
}
