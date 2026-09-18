/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatView, STARTER_PROMPTS } from "./ChatView";
import type { ChatMessage } from "@/types";

const noops = {
  onDraftChange: vi.fn(),
  onSend: vi.fn(),
  onStop: vi.fn(),
  onCitation: vi.fn(),
  onRetry: vi.fn(),
};

describe("ChatView states", () => {
  it("shows loading and error states", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { rerender } = render(
      <ChatView
        state="loading"
        messages={[]}
        streamingId={null}
        streamingText=""
        draft=""
        sending={false}
        providerNameById={{}}
        {...noops}
        onRetry={onRetry}
      />,
    );
    expect(
      document.querySelectorAll("[class*='animate-pulse']").length,
    ).toBeGreaterThan(0);

    rerender(
      <ChatView
        state="error"
        messages={[]}
        streamingId={null}
        streamingText=""
        draft=""
        sending={false}
        providerNameById={{}}
        {...noops}
        onRetry={onRetry}
      />,
    );
    expect(
      screen.getByText(/conversation could not be loaded/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("shows starter prompts when empty and the insufficient-evidence state", () => {
    const { rerender } = render(
      <ChatView
        state="ready"
        messages={[]}
        streamingId={null}
        streamingText=""
        draft=""
        sending={false}
        providerNameById={{}}
        {...noops}
      />,
    );
    for (const prompt of STARTER_PROMPTS) {
      expect(screen.getByRole("button", { name: prompt })).toBeInTheDocument();
    }

    const insufficient: ChatMessage = {
      id: "a1",
      author: "assistant",
      content: "I could not find enough evidence.",
      kind: "insufficient",
      citations: [],
      model: "rules-v1",
      provider: "hermetic",
      leftMachine: false,
    };
    rerender(
      <ChatView
        state="ready"
        messages={[insufficient]}
        streamingId={null}
        streamingText=""
        draft=""
        sending={false}
        providerNameById={{ hermetic: "Hermetic" }}
        {...noops}
      />,
    );
    expect(screen.getByText("Not enough evidence")).toBeInTheDocument();
    expect(screen.getByText(/stayed local/i)).toBeInTheDocument();
  });
});
