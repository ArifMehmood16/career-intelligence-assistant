/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProviderSettings } from "./ProviderSettings";
import type { Provider } from "@/types";

const localAvailable: Provider = {
  id: "hermetic",
  name: "Hermetic",
  kind: "local",
  models: ["rules-v1"],
  available: true,
  unavailableReason: null,
};

const localDown: Provider = {
  id: "ollama",
  name: "Local model server",
  kind: "local",
  models: ["llama3.1:8b"],
  available: false,
  unavailableReason:
    "Local model server not reachable at http://localhost:11434.",
};

const hosted: Provider = {
  id: "openai",
  name: "OpenAI",
  kind: "hosted",
  models: ["gpt-4.1-mini"],
  available: true,
  unavailableReason: null,
};

const baseProps = {
  state: "ready" as const,
  providers: [localAvailable, localDown, hosted],
  answerProviderId: "hermetic",
  answerModel: "rules-v1",
  indexProviderId: "hermetic",
  indexModel: "rules-v1",
  pendingProvider: null,
  pendingReindex: null,
  saveError: null,
  onSelect: vi.fn(),
  onModelChange: vi.fn(),
  onConfirmHosted: vi.fn(),
  onCancelHosted: vi.fn(),
  onConfirmReindex: vi.fn(),
  onCancelReindex: vi.fn(),
  onRetry: vi.fn(),
};

describe("ProviderSettings", () => {
  it("shows real unavailable reasons for providers that are down", () => {
    render(<ProviderSettings {...baseProps} />);
    expect(
      screen.getAllByText(
        "Local model server not reachable at http://localhost:11434.",
      ).length,
    ).toBeGreaterThan(0);
  });

  it("asks for hosted confirmation before egress", () => {
    render(<ProviderSettings {...baseProps} pendingProvider={hosted} />);
    expect(
      screen.getByRole("heading", { name: /Send your documents to OpenAI/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/leave this machine/i)).toBeInTheDocument();
  });

  it("warns that changing the index model triggers a re-index", async () => {
    const user = userEvent.setup();
    const onConfirmReindex = vi.fn();

    render(
      <ProviderSettings
        {...baseProps}
        pendingReindex={{
          kind: "index",
          providerId: "hermetic",
          model: "lexical-hash-v1",
        }}
        onConfirmReindex={onConfirmReindex}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /Start a re-index/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/invalidates existing embeddings/i),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /continue re-index/i }),
    );
    expect(onConfirmReindex).toHaveBeenCalled();
  });
});
