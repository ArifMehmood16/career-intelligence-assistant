/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LetterPanel } from "./LetterPanel";
import type { CoverLetterDraft, SupportingDocument } from "@/types";

afterEach(() => {
  cleanup();
});

const draft: CoverLetterDraft = {
  id: "cl-1",
  version: 1,
  createdAt: "2026-09-18T12:00:00Z",
  roleId: "role-1",
  paragraphs: [
    {
      text: "I am writing about the Analytics Engineer role at Northwind.",
      requirementIds: ["req-1"],
      spanIds: ["span-1"],
    },
    {
      text: "I led production dbt models for finance reporting.",
      requirementIds: ["req-1"],
      spanIds: ["span-1"],
    },
  ],
  omittedReason: null,
  provenance: {
    provider: "hermetic",
    model: null,
    leftMachine: false,
    generatedAt: "2026-09-18T12:00:00Z",
    grounded: true,
    fallback: "template",
  },
};

const supporting: SupportingDocument = {
  id: "sup-1",
  kind: "cover_letter",
  filename: "previous-cover-letter.docx",
  mediaType:
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  byteLength: 1200,
  pageCount: 1,
  parsedAt: "2026-09-18T11:00:00Z",
  createdAt: "2026-09-18T11:00:00Z",
};

describe("LetterPanel", () => {
  it("renders tone and gap controls and generates a draft", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();
    const onToneChange = vi.fn();
    const onIncludeGapLineChange = vi.fn();

    render(
      <LetterPanel
        tone="plain"
        includeGapLine={false}
        generating={false}
        draft={null}
        versions={[]}
        refusal={null}
        supportingDocuments={[supporting]}
        onToneChange={onToneChange}
        onIncludeGapLineChange={onIncludeGapLineChange}
        onGenerate={onGenerate}
        onSelectVersion={vi.fn()}
        onExport={vi.fn()}
        onCitation={vi.fn()}
        onOpenGaps={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("radio", { name: /warm/i }));
    expect(onToneChange).toHaveBeenCalledWith("warm");

    await user.click(
      screen.getByRole("checkbox", { name: /honest line about/i }),
    );
    expect(onIncludeGapLineChange).toHaveBeenCalledWith(true);

    await user.click(screen.getByRole("button", { name: /generate letter/i }));
    expect(onGenerate).toHaveBeenCalled();

    expect(screen.getByText(/previous-cover-letter\.docx/)).toBeInTheDocument();
    expect(
      screen.getByText(/supporting documents, never as generated versions/i),
    ).toBeInTheDocument();
  });

  it("shows refusal as a next step toward Gaps, not as a raw error", async () => {
    const user = userEvent.setup();
    const onOpenGaps = vi.fn();

    render(
      <LetterPanel
        tone="plain"
        includeGapLine={false}
        generating={false}
        draft={null}
        versions={[]}
        refusal={{
          message:
            "Fewer than two must-have requirements are met. Use the gap plan instead.",
        }}
        supportingDocuments={[]}
        onToneChange={vi.fn()}
        onIncludeGapLineChange={vi.fn()}
        onGenerate={vi.fn()}
        onSelectVersion={vi.fn()}
        onExport={vi.fn()}
        onCitation={vi.fn()}
        onOpenGaps={onOpenGaps}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      /fewer than two must-have/i,
    );
    expect(screen.queryByText(/could not be created/i)).toBeNull();
    await user.click(screen.getByRole("button", { name: /open gaps/i }));
    expect(onOpenGaps).toHaveBeenCalled();
  });

  it("renders paragraphs, citation chips, versions, and export", async () => {
    const user = userEvent.setup();
    const onCitation = vi.fn();
    const onSelectVersion = vi.fn();
    const onExport = vi.fn();
    const v2 = { ...draft, id: "cl-2", version: 2 };

    render(
      <LetterPanel
        tone="warm"
        includeGapLine={true}
        generating={false}
        draft={v2}
        versions={[draft, v2]}
        refusal={null}
        supportingDocuments={[]}
        onToneChange={vi.fn()}
        onIncludeGapLineChange={vi.fn()}
        onGenerate={vi.fn()}
        onSelectVersion={onSelectVersion}
        onExport={onExport}
        onCitation={onCitation}
        onOpenGaps={vi.fn()}
      />,
    );

    expect(screen.getByText(/led production dbt models/i)).toBeInTheDocument();

    const body = screen.getByRole("region", { name: /generated letter/i });
    await user.click(
      within(body).getAllByRole("button", { name: /span-1/i })[0]!,
    );
    expect(onCitation).toHaveBeenCalledWith("span-1");

    await user.click(screen.getByRole("button", { name: /version 1/i }));
    expect(onSelectVersion).toHaveBeenCalledWith(draft);

    await user.click(screen.getByRole("button", { name: /export markdown/i }));
    expect(onExport).toHaveBeenCalledWith(v2);
  });

  it("does not treat a failed generated-letter query as empty history", async () => {
    const user = userEvent.setup();
    const onRetryGenerated = vi.fn();

    render(
      <LetterPanel
        tone="plain"
        includeGapLine={false}
        generating={false}
        draft={null}
        versions={[]}
        refusal={null}
        supportingDocuments={[]}
        generatedState="error"
        onRetryGenerated={onRetryGenerated}
        onToneChange={vi.fn()}
        onIncludeGapLineChange={vi.fn()}
        onGenerate={vi.fn()}
        onSelectVersion={vi.fn()}
        onExport={vi.fn()}
        onCitation={vi.fn()}
        onOpenGaps={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/generated letters could not be loaded/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/version history/i)).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /retry generated letters/i }),
    );
    expect(onRetryGenerated).toHaveBeenCalled();
  });

  it("does not treat a failed supporting-letter query as an empty upload list", async () => {
    const user = userEvent.setup();
    const onRetrySupporting = vi.fn();

    render(
      <LetterPanel
        tone="plain"
        includeGapLine={false}
        generating={false}
        draft={null}
        versions={[]}
        refusal={null}
        supportingDocuments={[]}
        supportingState="error"
        onRetrySupporting={onRetrySupporting}
        onToneChange={vi.fn()}
        onIncludeGapLineChange={vi.fn()}
        onGenerate={vi.fn()}
        onSelectVersion={vi.fn()}
        onExport={vi.fn()}
        onCitation={vi.fn()}
        onOpenGaps={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/supporting letters could not be loaded/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/no supporting cover letters uploaded/i),
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /retry supporting letters/i }),
    );
    expect(onRetrySupporting).toHaveBeenCalled();
  });
});
