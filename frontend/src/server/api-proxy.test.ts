/**
 * @vitest-environment node
 *
 * Phase 12.1 — spike proofs that the API proxy does not buffer SSE or uploads.
 */
import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";
import { AddressInfo } from "node:net";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ProxyRejectedError,
  assertSameOrigin,
  proxyToUpstream,
  resolveApiBaseUrl,
} from "./api-proxy";

const APP_ORIGIN = "http://localhost:3000";

function listen(
  handler: (req: IncomingMessage, res: ServerResponse) => void | Promise<void>,
): Promise<{ baseUrl: string; close: () => Promise<void> }> {
  const server = createServer((req, res) => {
    void Promise.resolve(handler(req, res)).catch((error: unknown) => {
      res.statusCode = 500;
      res.end(String(error));
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address() as AddressInfo;
      resolve({
        baseUrl: `http://127.0.0.1:${port}`,
        close: () =>
          new Promise((closeResolve, closeReject) => {
            server.close((err) => (err ? closeReject(err) : closeResolve()));
          }),
      });
    });
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("resolveApiBaseUrl", () => {
  it("requires a non-VITE server variable", () => {
    expect(resolveApiBaseUrl({ API_BASE_URL: "http://localhost:8000" })).toBe(
      "http://localhost:8000",
    );
    expect(() => resolveApiBaseUrl({})).toThrow(ProxyRejectedError);
    expect(() =>
      resolveApiBaseUrl({ API_BASE_URL: "VITE_http://bad" }),
    ).toThrow(/VITE_/);
  });
});

describe("assertSameOrigin", () => {
  it("rejects cross-origin mutations", () => {
    const request = new Request("http://localhost:3000/api/roles", {
      method: "POST",
      headers: { Origin: "https://evil.example" },
    });
    expect(() => assertSameOrigin(request, APP_ORIGIN)).toThrow(/Cross-origin/);
  });

  it("allows GET without Origin", () => {
    const request = new Request("http://localhost:3000/api/roles");
    expect(() => assertSameOrigin(request, APP_ORIGIN)).not.toThrow();
  });
});

describe("Phase 12.1 spike: SSE is not buffered", () => {
  it("delivers the first event before the upstream finishes", async () => {
    let upstreamFinished = false;
    const upstream = await listen(async (_req, res) => {
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      });
      res.write('event: meta\ndata: {"ok":true}\n\n');
      await sleep(150);
      res.write('event: done\ndata: {"kind":"answer"}\n\n');
      upstreamFinished = true;
      res.end();
    });

    try {
      const request = new Request(`${APP_ORIGIN}/api/messages`, {
        method: "GET",
      });
      const proxied = await proxyToUpstream(request, {
        apiBaseUrl: upstream.baseUrl,
        pathSuffix: "messages",
        appOrigin: APP_ORIGIN,
      });

      expect(proxied.headers.get("content-type")).toMatch(/text\/event-stream/);
      const reader = proxied.body!.getReader();
      const decoder = new TextDecoder();
      const first = await reader.read();
      const chunk = decoder.decode(first.value);
      expect(chunk).toContain("event: meta");
      expect(upstreamFinished).toBe(false);
      await reader.cancel();
    } finally {
      await upstream.close();
    }
  });
});

describe("Phase 12.1 spike: multipart upload is not buffered", () => {
  it("forwards the request body stream without reading it first", async () => {
    const seenBodies: unknown[] = [];
    const fetchImpl = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) => {
        seenBodies.push(init?.body ?? null);
        return new Response(null, { status: 204 });
      },
    );

    const payload = new Uint8Array(64 * 1024);
    payload.fill(7);
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(payload);
        controller.close();
      },
    });

    const request = new Request(`${APP_ORIGIN}/api/cv`, {
      method: "POST",
      headers: {
        Origin: APP_ORIGIN,
        "Content-Type": "multipart/form-data; boundary=spike",
      },
      body,
      // @ts-expect-error duplex is required for streaming bodies in undici
      duplex: "half",
    });

    const arrayBufferSpy = vi.spyOn(request, "arrayBuffer");
    const textSpy = vi.spyOn(request, "text");
    const jsonSpy = vi.spyOn(request, "json");

    await proxyToUpstream(request, {
      apiBaseUrl: "http://upstream.test",
      pathSuffix: "cv",
      appOrigin: APP_ORIGIN,
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(arrayBufferSpy).not.toHaveBeenCalled();
    expect(textSpy).not.toHaveBeenCalled();
    expect(jsonSpy).not.toHaveBeenCalled();
    expect(seenBodies[0]).toBeInstanceOf(ReadableStream);
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://upstream.test/api/cv",
      expect.objectContaining({ method: "POST", duplex: "half" }),
    );
  });

  it("streams a MAX_UPLOAD_BYTES-sized body so upstream reads before the client finishes", async () => {
    const maxUploadBytes = 256 * 1024; // representative chunk of the configured 10 MiB
    let upstreamBytes = 0;
    let upstreamSawFirstByte = false;
    let clientFinished = false;

    const upstream = await listen((req, res) => {
      req.on("data", (chunk: Buffer) => {
        if (!upstreamSawFirstByte && chunk.length > 0) {
          upstreamSawFirstByte = true;
        }
        upstreamBytes += chunk.length;
      });
      req.on("end", () => {
        res.writeHead(201, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ received: upstreamBytes }));
      });
    });

    try {
      const chunkSize = 16 * 1024;
      let sent = 0;
      const body = new ReadableStream<Uint8Array>({
        async pull(controller) {
          if (sent >= maxUploadBytes) {
            clientFinished = true;
            controller.close();
            return;
          }
          const next = Math.min(chunkSize, maxUploadBytes - sent);
          controller.enqueue(new Uint8Array(next).fill(1));
          sent += next;
          await sleep(5);
        },
      });

      const request = new Request(`${APP_ORIGIN}/api/cv`, {
        method: "POST",
        headers: {
          Origin: APP_ORIGIN,
          "Content-Type": "application/octet-stream",
          "Content-Length": String(maxUploadBytes),
        },
        body,
        // @ts-expect-error duplex is required for streaming bodies in undici
        duplex: "half",
      });

      const proxiedPromise = proxyToUpstream(request, {
        apiBaseUrl: upstream.baseUrl,
        pathSuffix: "cv",
        appOrigin: APP_ORIGIN,
      });

      // Wait until upstream has begun reading while the client is still sending.
      const deadline = Date.now() + 2000;
      while (!upstreamSawFirstByte && Date.now() < deadline) {
        await sleep(10);
      }
      expect(upstreamSawFirstByte).toBe(true);
      expect(clientFinished).toBe(false);

      const proxied = await proxiedPromise;
      expect(proxied.status).toBe(201);
      const payload = (await proxied.json()) as { received: number };
      expect(payload.received).toBe(maxUploadBytes);
      expect(clientFinished).toBe(true);
    } finally {
      await upstream.close();
    }
  });
});
