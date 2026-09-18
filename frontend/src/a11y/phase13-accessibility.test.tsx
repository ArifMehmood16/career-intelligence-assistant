/**
 * @vitest-environment jsdom
 *
 * Phase 13.9 — keyboard path, labels, and live regions for progress.
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatView } from "@/components/ask/ChatView";
import { GapsPanel } from "@/components/role/GapsPanel";
import { RoleDetailTabs } from "@/components/role/RoleDetailTabs";
import { CvCard } from "@/components/workspace/CvCard";
import { RolesPanel } from "@/components/workspace/RolesPanel";
import type { GapItem, Role } from "@/types";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    ...props
  }: {
    children: React.ReactNode;
    to: string;
    className?: string;
  }) => (
    <a href={props.to} className={props.className}>
      {children}
    </a>
  ),
  useNavigate: () => vi.fn(),
}));

afterEach(() => {
  cleanup();
});

const gap: GapItem = {
  requirementId: "req-1",
  requirementText: "Production dbt",
  type: "must",
  status: "partial",
  reason: "adjacent_claim_only",
  adjacentEvidence: {
    spanId: "span-1",
    documentId: "doc-1",
    page: 1,
    paragraph: "Introduced dbt models.",
    highlight: "dbt models",
  },
  scoreDelta: 9,
  action: "evidence_it",
  canDraftBullet: true,
};

const analysingRole: Role = {
  id: "role-a",
  title: "Analytics Engineer",
  company: "Acme",
  fitScore: 0,
  bandLabel: "Not scored yet",
  counts: { met: 0, partial: 0, missing: 0 },
  status: "analysing",
  updatedAt: "2026-09-18T12:00:00Z",
};

describe("Phase 13.9 accessibility", () => {
  it("keeps a keyboard path through role tabs and draft controls", async () => {
    const user = userEvent.setup();
    const onDraft = vi.fn();
    const { container } = render(
      <div>
        <RoleDetailTabs
          value="gaps"
          onValueChange={vi.fn()}
          fit={<p>Fit</p>}
          gaps={
            <GapsPanel
              state="ready"
              currentScore={61}
              items={[gap]}
              onRetry={vi.fn()}
              onSelectEvidence={vi.fn()}
              onDraftBullet={onDraft}
            />
          }
          prepare={<p>Prepare</p>}
          letter={<p>Letter</p>}
        />
      </div>,
    );

    const tablist = within(container).getByRole("tablist", {
      name: "Role detail sections",
    });
    const gapsTab = within(tablist).getByRole("tab", { name: "Gaps" });
    gapsTab.focus();
    expect(gapsTab).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    expect(within(tablist).getByRole("tab", { name: "Prepare" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: /draft a bullet/i }));
    expect(onDraft).toHaveBeenCalled();
  });

  it("labels upload and announces parsing and analysing progress", () => {
    const { rerender, unmount } = render(
      <CvCard
        state="empty"
        document={null}
        errorMessage={null}
        onUpload={vi.fn()}
        onReplace={vi.fn()}
        onDelete={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /browse/i })).toBeInTheDocument();

    rerender(
      <CvCard
        state="parsing"
        document={null}
        errorMessage={null}
        onUpload={vi.fn()}
        onReplace={vi.fn()}
        onDelete={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByRole("status")).toHaveTextContent(/parsing/i);
    unmount();

    render(
      <RolesPanel
        state="ready"
        roles={[analysingRole]}
        sortKey="fit"
        sortDirection="desc"
        onSort={vi.fn()}
        onRetry={vi.fn()}
        addRoleSlot={null}
        layout="table"
      />,
    );
    const analysing = screen
      .getAllByRole("status")
      .find((el) => /analysing/i.test(el.textContent ?? ""));
    expect(analysing).toBeDefined();
    expect(analysing).toHaveAttribute("aria-live", "polite");
  });

  it("exposes a live region while chat answers stream", () => {
    render(
      <ChatView
        state="ready"
        messages={[
          {
            id: "u1",
            author: "user",
            content: "Where is the SQL evidence?",
            kind: "question",
            citations: [],
            model: null,
            provider: null,
            leftMachine: false,
          },
          {
            id: "a1",
            author: "assistant",
            content: "",
            kind: "answer",
            citations: [],
            model: "built-in-offline",
            provider: "hermetic",
            leftMachine: false,
          },
        ]}
        streamingId="a1"
        streamingText="The CV mentions"
        draft=""
        sending={false}
        providerNameById={{ hermetic: "Hermetic" }}
        onDraftChange={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onCitation={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    const live = screen.getByRole("status", { name: /streaming answer/i });
    expect(live).toHaveAttribute("aria-live", "polite");
    expect(live).toHaveTextContent(/The CV mentions/);
  });
});
