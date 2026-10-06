/** @vitest-environment jsdom */
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatContainer } from "./ChatContainer";
import * as api from "@/api/client";
import type { ChatMessage } from "@/types";

afterEach(cleanup);

vi.mock("@/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof api>();
  return {
    ...original,
    getMessages: vi.fn(),
    getProviders: vi.fn(),
    postMessageStream: vi.fn(),
  };
});

function deferred<T = api.MessageStreamResult>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

const RESULT: api.MessageStreamResult = {
  messageId: "answer",
  questionId: "question",
  text: "Answer",
  kind: "answer",
  citations: [],
  provider: "hermetic",
  model: "rules",
  leftMachine: false,
  clientRequestId: "request",
  toolSteps: [],
};

async function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ChatContainer />
    </QueryClientProvider>,
  );
  await screen.findByPlaceholderText(
    "Ask about your CV and the roles you saved",
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument(),
  );
  return userEvent.setup();
}

async function send(user: ReturnType<typeof userEvent.setup>, content: string) {
  await user.type(screen.getByRole("textbox"), content);
  await user.click(screen.getByRole("button", { name: "Send" }));
}

describe("Ask request processing", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getMessages).mockResolvedValue([]);
    vi.mocked(api.getProviders).mockResolvedValue([]);
  });

  it("shows processing immediately while the first response is delayed", async () => {
    const pending = deferred();
    vi.mocked(api.postMessageStream).mockReturnValue(pending.promise);
    const user = await mount();
    await send(user, "What evidence supports Python?");
    expect(
      screen.getByRole("status", { name: "Question processing" }),
    ).toHaveTextContent("Processing your question");
    expect(api.postMessageStream).toHaveBeenCalledOnce();
    await act(async () => pending.resolve(RESULT));
    await waitFor(() =>
      expect(
        screen.queryByRole("status", { name: "Question processing" }),
      ).toBeNull(),
    );
  });

  it("clears processing and permits retry after a request fails", async () => {
    const pending = deferred();
    vi.mocked(api.postMessageStream).mockReturnValue(pending.promise);
    const user = await mount();
    await send(user, "Compare my fit");
    await act(async () => pending.reject(new Error("Network unavailable")));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(
      screen.queryByRole("status", { name: "Question processing" }),
    ).toBeNull();
    expect(screen.getByRole("button", { name: "Retry send" })).toBeEnabled();
  });

  it("shows receiving and history refresh phases until completion", async () => {
    const stream = deferred();
    const history = deferred<ChatMessage[]>();
    vi.mocked(api.postMessageStream).mockReturnValue(stream.promise);
    vi.mocked(api.getMessages)
      .mockResolvedValueOnce([])
      .mockReturnValueOnce(history.promise);
    const user = await mount();
    await send(user, "What does my experience show?");
    const { onEvent } = vi.mocked(api.postMessageStream).mock.calls[0]![0];
    act(() => {
      onEvent({
        type: "meta",
        questionId: "q",
        messageId: "a",
        intent: "fit",
        provider: "hermetic",
        model: "rules",
        leftMachine: false,
      });
      onEvent({ type: "token", text: "The evidence shows" });
    });
    expect(
      screen.getByRole("status", { name: "Question processing" }),
    ).toHaveTextContent("Receiving your answer");
    expect(
      screen.getByRole("status", { name: "Streaming answer" }),
    ).toHaveTextContent("The evidence shows");
    await act(async () => stream.resolve(RESULT));
    expect(
      screen.getByRole("status", { name: "Question processing" }),
    ).toHaveTextContent("Updating the conversation");
    await act(async () => history.resolve([]));
    expect(
      screen.queryByRole("status", { name: "Question processing" }),
    ).toBeNull();
  });

  it("stopping an old request cannot clear the next request's processing", async () => {
    const first = deferred();
    const second = deferred();
    vi.mocked(api.postMessageStream)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const user = await mount();
    await send(user, "First question");
    const oldSignal = vi.mocked(api.postMessageStream).mock.calls[0]![0].signal;
    await user.click(screen.getByRole("button", { name: "Stop" }));
    expect(oldSignal?.aborted).toBe(true);
    await send(user, "Second question");
    await act(async () =>
      first.reject(new DOMException("Stopped", "AbortError")),
    );
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(
      screen.getByRole("status", { name: "Question processing" }),
    ).toBeInTheDocument();
    await act(async () => second.resolve(RESULT));
  });
});
