/**
 * Phase 12.6 — multipart CV upload and supporting cover-letter client.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  deleteCoverLetter,
  getCoverLetters,
  uploadCoverLetter,
  uploadCv,
} from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
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

describe("uploadCv", () => {
  it("posts the file as multipart form-data without forcing JSON Content-Type", async () => {
    const file = new File(["Curriculum vitae text."], "cv.txt", {
      type: "text/plain",
    });

    stubFetch((_input, init) => {
      expect(init?.method).toBe("POST");
      expect(init?.body).toBeInstanceOf(FormData);
      const form = init?.body as FormData;
      const part = form.get("file");
      expect(part).toBeInstanceOf(File);
      expect((part as File).name).toBe("cv.txt");
      const headers = new Headers(init?.headers);
      expect(headers.get("Content-Type")).toBeNull();
      return Response.json(
        {
          id: "cv-1",
          filename: "cv.txt",
          pageCount: 1,
          parsedAt: "2026-09-18T12:00:00Z",
          reanalysis: { jobIds: [] },
        },
        { status: 201 },
      );
    });

    await expect(uploadCv(file)).resolves.toEqual({
      id: "cv-1",
      filename: "cv.txt",
      pageCount: 1,
      parsedAt: "2026-09-18T12:00:00Z",
    });
  });

  it("surfaces ApiError.message from rejection envelopes", async () => {
    stubFetch(
      () =>
        new Response(
          JSON.stringify({
            error: {
              code: "document_unsupported",
              message: "Only PDF, DOCX and plain text documents are accepted.",
              correlationId: "corr-up",
            },
          }),
          { status: 415 },
        ),
    );

    await expect(
      uploadCv(new File(["x"], "x.bin", { type: "application/octet-stream" })),
    ).rejects.toMatchObject({
      name: "ApiError",
      code: "document_unsupported",
      message: "Only PDF, DOCX and plain text documents are accepted.",
      correlationId: "corr-up",
      status: 415,
    } satisfies Partial<ApiError>);
  });
});

describe("cover letters", () => {
  it("lists supporting cover letters", async () => {
    stubFetch(() =>
      Response.json([
        {
          id: "cl-1",
          kind: "cover_letter",
          filename: "letter.txt",
          mediaType: "text/plain",
          byteLength: 12,
          pageCount: 1,
          parsedAt: "2026-09-18T12:00:00Z",
          createdAt: "2026-09-18T12:00:00Z",
        },
      ]),
    );

    await expect(getCoverLetters()).resolves.toEqual([
      {
        id: "cl-1",
        kind: "cover_letter",
        filename: "letter.txt",
        mediaType: "text/plain",
        byteLength: 12,
        pageCount: 1,
        parsedAt: "2026-09-18T12:00:00Z",
        createdAt: "2026-09-18T12:00:00Z",
      },
    ]);
  });

  it("uploads a cover letter as multipart and deletes by id", async () => {
    const file = new File(["Dear hiring manager."], "letter.txt", {
      type: "text/plain",
    });

    stubFetch((input, init) => {
      const path = String(input);
      if (path === "/api/cover-letters" && init?.method === "POST") {
        expect(init.body).toBeInstanceOf(FormData);
        return Response.json(
          {
            id: "cl-2",
            kind: "cover_letter",
            filename: "letter.txt",
            mediaType: "text/plain",
            byteLength: 20,
            pageCount: 1,
            parsedAt: "2026-09-18T12:01:00Z",
            createdAt: "2026-09-18T12:01:00Z",
          },
          { status: 201 },
        );
      }
      if (path === "/api/cover-letters/cl-2" && init?.method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      throw new Error(`unexpected ${init?.method} ${path}`);
    });

    await expect(uploadCoverLetter(file)).resolves.toMatchObject({
      id: "cl-2",
      kind: "cover_letter",
    });
    await expect(deleteCoverLetter("cl-2")).resolves.toBeUndefined();
  });
});
