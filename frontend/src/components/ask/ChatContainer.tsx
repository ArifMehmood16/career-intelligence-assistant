import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  deleteMessages,
  getMessages,
  getProviders,
  getSpan,
  postMessageStream,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import {
  ChatView,
  type ChatProcessingPhase,
  type ChatViewState,
} from "@/components/ask/ChatView";
import { EvidencePanel } from "@/components/EvidencePanel";
import type { ChatMessage, Citation, ToolStep } from "@/types";

export function ChatContainer() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState("");
  // Tool steps are sent with a fresh answer and not stored, so the page keeps
  // them for this session after history is refetched.
  const [toolSteps, setToolSteps] = useState<Record<string, ToolStep[]>>({});
  const [sending, setSending] = useState(false);
  const [processingPhase, setProcessingPhase] =
    useState<ChatProcessingPhase>("processing");
  const [sendError, setSendError] = useState<string | null>(null);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [lastClientRequestId, setLastClientRequestId] = useState<string | null>(
    null,
  );
  const [lastFailedContent, setLastFailedContent] = useState<string | null>(
    null,
  );
  const abortRef = useRef<AbortController | null>(null);

  const messagesQuery = useQuery({
    queryKey: ["messages"],
    queryFn: getMessages,
  });
  const providersQuery = useQuery({
    queryKey: ["providers"],
    queryFn: getProviders,
  });

  const spanId = citation?.evidence?.spanId ?? null;
  const spanQuery = useQuery({
    queryKey: ["span", spanId],
    queryFn: () => getSpan(spanId!),
    enabled: panelOpen && Boolean(spanId),
    retry: false,
  });

  const clearHistory = useMutation({
    mutationFn: deleteMessages,
    onSuccess: () => {
      queryClient.setQueryData(["messages"], []);
    },
  });

  const stopStream = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreamingId(null);
    setStreamingText("");
    setSending(false);
  };

  useEffect(() => () => abortRef.current?.abort(), []);

  const runStream = async (content: string, clientRequestId?: string) => {
    if (abortRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    const isCurrent = () =>
      abortRef.current === controller && !controller.signal.aborted;
    setSending(true);
    setProcessingPhase("processing");
    setSendError(null);
    const requestId = clientRequestId ?? crypto.randomUUID();
    setLastClientRequestId(requestId);
    setLastFailedContent(content);

    const optimisticUser: ChatMessage = {
      id: `local-user-${requestId}`,
      author: "user",
      content,
      kind: "question",
      citations: [],
      model: null,
      provider: null,
      leftMachine: false,
    };
    queryClient.setQueryData<ChatMessage[]>(["messages"], (current) => [
      ...(current ?? []),
      optimisticUser,
    ]);

    let answerId: string | null = null;

    try {
      await postMessageStream({
        content,
        clientRequestId: requestId,
        signal: controller.signal,
        onEvent: (event) => {
          if (!isCurrent()) return;
          if (event.type === "meta") {
            setProcessingPhase("answering");
            answerId = event.messageId;
            setStreamingId(event.messageId);
            setStreamingText("");
            const placeholder: ChatMessage = {
              id: event.messageId,
              author: "assistant",
              content: "",
              kind: "answer",
              citations: [],
              model: event.model,
              provider: event.provider,
              leftMachine: event.leftMachine,
            };
            queryClient.setQueryData<ChatMessage[]>(["messages"], (current) => {
              const withoutDupes = (current ?? []).filter(
                (row) =>
                  row.id !== optimisticUser.id && row.id !== event.messageId,
              );
              return [...withoutDupes, optimisticUser, placeholder];
            });
          }
          if (event.type === "tools") {
            const id = answerId;
            if (id !== null) {
              setToolSteps((current) => ({ ...current, [id]: event.steps }));
            }
          }
          if (event.type === "token") {
            setStreamingText((text) => text + event.text);
          }
        },
      });

      if (!isCurrent()) return;
      setProcessingPhase("saving");
      const history = await getMessages();
      if (!isCurrent()) return;
      queryClient.setQueryData(["messages"], history);
      setLastFailedContent(null);
      setSendError(null);
    } catch (error) {
      if (!isCurrent()) return;
      if (error instanceof DOMException && error.name === "AbortError") {
        void queryClient.invalidateQueries({ queryKey: ["messages"] });
      } else if (error instanceof ApiError) {
        setSendError(formatDescribedError(describeApiError(error)));
        void queryClient.invalidateQueries({ queryKey: ["messages"] });
      } else if (error instanceof Error) {
        setSendError(formatDescribedError(describeApiError(error)));
        void queryClient.invalidateQueries({ queryKey: ["messages"] });
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setStreamingId(null);
        setStreamingText("");
        setSending(false);
      }
    }
  };

  const providerNameById = useMemo(
    () =>
      Object.fromEntries(
        (providersQuery.data ?? []).map((item) => [item.id, item.name]),
      ),
    [providersQuery.data],
  );

  const messages = useMemo(
    () =>
      (messagesQuery.data ?? []).map((message): ChatMessage => {
        const steps = toolSteps[message.id];
        return steps ? { ...message, toolSteps: steps } : message;
      }),
    [messagesQuery.data, toolSteps],
  );

  const state: ChatViewState = messagesQuery.isPending
    ? "loading"
    : messagesQuery.isError
      ? "error"
      : "ready";

  const resolveState =
    !panelOpen || !spanId
      ? "ready"
      : spanQuery.isPending
        ? "loading"
        : spanQuery.isError
          ? "error"
          : "ready";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ChatView
        state={state}
        messages={messages}
        streamingId={streamingId}
        streamingText={streamingText}
        draft={draft}
        sending={sending}
        processingPhase={processingPhase}
        sendError={sendError}
        canClear={(messagesQuery.data?.length ?? 0) > 0 && !sending}
        providerNameById={providerNameById}
        onDraftChange={setDraft}
        onSend={() => {
          const content = draft.trim();
          if (!content || sending) return;
          setDraft("");
          void runStream(content);
        }}
        onRetrySend={() => {
          if (!lastFailedContent || !lastClientRequestId || sending) return;
          void runStream(lastFailedContent, lastClientRequestId);
        }}
        onStop={stopStream}
        onClear={() => clearHistory.mutate()}
        onCitation={(next) => {
          setCitation(next);
          setPanelOpen(true);
        }}
        onRetry={() => {
          void messagesQuery.refetch();
        }}
      />

      <EvidencePanel
        open={panelOpen}
        title={citation?.label ?? ""}
        status={null}
        evidence={
          spanId ? (spanQuery.data ?? null) : (citation?.evidence ?? null)
        }
        resolveState={resolveState}
        resolveError={
          spanQuery.error != null
            ? formatDescribedError(describeApiError(spanQuery.error))
            : null
        }
        onOpenChange={setPanelOpen}
      />
    </div>
  );
}
