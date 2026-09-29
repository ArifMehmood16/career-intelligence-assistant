/**
 * PLAN 18.13 — Ask shows the tools the agent called for an answer.
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ChatMessage } from "@/types";

import { ChatView } from "./ChatView";
import { ToolSteps } from "./ToolSteps";

afterEach(() => {
  cleanup();
});

const STEPS = [
  {
    name: "search_evidence",
    arguments: { query: "dbt in production" },
    found: 2,
    failed: false,
  },
  { name: "get_chunk", arguments: { chunk_id: "c-9" }, found: 0, failed: true },
];

describe("ToolSteps", () => {
  it("lists each call with what it asked and what came back", async () => {
    render(<ToolSteps steps={STEPS} />);

    await userEvent.click(screen.getByText("Found using 2 tool calls"));
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Searched your documents");
    expect(items[0]).toHaveTextContent("query: dbt in production");
    expect(items[0]).toHaveTextContent("2 passages");
    expect(items[1]).toHaveTextContent("Opened a passage");
    expect(items[1]).toHaveTextContent("Nothing found");
  });

  it("renders nothing when the answer used no tools", () => {
    const { container } = render(<ToolSteps steps={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ChatView with tool steps", () => {
  it("shows the steps under the answer they produced", () => {
    const messages: ChatMessage[] = [
      {
        id: "a-1",
        author: "assistant",
        content: "The CV shows dbt in production.",
        kind: "answer",
        citations: [],
        model: "qwen2.5:7b",
        provider: "ollama",
        leftMachine: false,
        toolSteps: STEPS,
      },
    ];
    render(
      <ChatView
        state="ready"
        messages={messages}
        streamingId={null}
        streamingText=""
        draft=""
        sending={false}
        providerNameById={{}}
        onDraftChange={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onCitation={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("Found using 2 tool calls")).toBeInTheDocument();
  });
});
