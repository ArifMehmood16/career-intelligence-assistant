/**
 * Phase 12.9 — POST /api/messages SSE stream client.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { postMessageStream } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function sseBody(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;
  return new ReadableStream({
    pull(controller) {
      if (index >= chunks.length) {
        controller.close();
        return;
      }
      controller.enqueue(encoder.encode(chunks[index]));
      index += 1;
    },
  });
}

describe("postMessageStream", () => {
  it("POSTs with Accept text/event-stream and a stable clientRequestId", async () => {
    const events: string[] = [];
    stubFetch((_input, init) => {
      expect(init?.method).toBe("POST");
      const headers = new Headers(init?.headers);
      expect(headers.get("Accept")).toBe("text/event-stream");
      const body = JSON.parse(String(init?.body)) as {
        content: string;
        clientRequestId: string;
      };
      expect(body.content).toBe("What gaps?");
      expect(body.clientRequestId).toMatch(/^[0-9a-f-]{36}$/i);
      return new Response(
        sseBody([
          'event: meta\ndata: {"questionId":"q1","messageId":"m1","intent":"gaps","provider":"hermetic","model":"rules-v1","leftMachine":false}\n\n',
          'event: token\ndata: {"text":"Hello"}\n\n',
          'event: token\ndata: {"text":" world"}\n\n',
          'event: citations\ndata: {"citations":[{"id":"c1","label":"dbt","evidence":{"spanId":"s1","documentId":"cv-1","page":1,"paragraph":"Owned dbt.","highlight":"dbt"}}]}\n\n',
          'event: done\ndata: {"kind":"answer"}\n\n',
        ]),
        {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        },
      );
    });

    const result = await postMessageStream({
      content: "What gaps?",
      onEvent: (event) => events.push(event.type),
    });

    expect(events).toEqual(["meta", "token", "token", "citations", "done"]);
    expect(result.text).toBe("Hello world");
    expect(result.kind).toBe("answer");
    expect(result.messageId).toBe("m1");
    expect(result.citations).toHaveLength(1);
  });

  it("reuses the provided clientRequestId on retry", async () => {
    stubFetch((_input, init) => {
      const body = JSON.parse(String(init?.body)) as {
        clientRequestId: string;
      };
      expect(body.clientRequestId).toBe("fixed-client-request");
      return new Response(
        sseBody([
          'event: meta\ndata: {"questionId":"q1","messageId":"m1","intent":"gaps","provider":"hermetic","model":null,"leftMachine":false}\n\n',
          'event: done\ndata: {"kind":"insufficient"}\n\n',
        ]),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    });

    await postMessageStream({
      content: "retry me",
      clientRequestId: "fixed-client-request",
      onEvent: () => undefined,
    });
  });

  it("throws ApiError when the stream emits an error event", async () => {
    stubFetch(
      () =>
        new Response(
          sseBody([
            'event: error\ndata: {"code":"provider_failed","message":"Upstream failed."}\n\n',
          ]),
          { status: 200, headers: { "Content-Type": "text/event-stream" } },
        ),
    );

    await expect(
      postMessageStream({
        content: "fail",
        onEvent: () => undefined,
      }),
    ).rejects.toMatchObject({
      name: "ApiError",
      code: "provider_failed",
      message: "Upstream failed.",
    });
  });

  it("aborts when the signal is aborted", async () => {
    const controller = new AbortController();
    stubFetch((_input, init) => {
      expect(init?.signal).toBe(controller.signal);
      controller.abort();
      return new Response(
        sseBody([
          'event: meta\ndata: {"questionId":"q1","messageId":"m1","intent":"gaps","provider":"hermetic","model":null,"leftMachine":false}\n\n',
          'event: token\ndata: {"text":"partial"}\n\n',
        ]),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    });

    await expect(
      postMessageStream({
        content: "stop me",
        signal: controller.signal,
        onEvent: () => undefined,
      }),
    ).rejects.toThrow();
  });
});

function stubFetch(
  handler: (input: RequestInfo | URL, init?: RequestInit) => Response,
) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
      handler(input, init),
    ),
  );
}
