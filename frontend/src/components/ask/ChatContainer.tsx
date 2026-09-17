import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getMessages, getProviders, sendMessage } from "@/api/client";
import { ChatView, type ChatViewState } from "@/components/ask/ChatView";
import { EvidencePanel } from "@/components/EvidencePanel";
import type { Citation } from "@/types";

const TOKEN_MS = 28;

export function ChatContainer() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [citation, setCitation] = useState<Citation | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const messagesQuery = useQuery({ queryKey: ["messages"], queryFn: getMessages });
  const providersQuery = useQuery({ queryKey: ["providers"], queryFn: getProviders });

  const stopStream = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setStreamingId(null);
    setStreamingText("");
  };

  useEffect(() => () => stopStream(), []);

  const send = useMutation({
    mutationFn: sendMessage,
    onSuccess: (next) => {
      queryClient.setQueryData(["messages"], next);
      const last = next[next.length - 1];
      if (!last || last.author !== "assistant") return;

      const tokens = last.content.split(/(\s+)/);
      let index = 0;
      setStreamingId(last.id);
      setStreamingText("");
      timerRef.current = setInterval(() => {
        index += 1;
        setStreamingText(tokens.slice(0, index).join(""));
        if (index >= tokens.length) stopStream();
      }, TOKEN_MS);
    },
  });

  const providerNameById = useMemo(
    () =>
      Object.fromEntries((providersQuery.data ?? []).map((item) => [item.id, item.name])),
    [providersQuery.data],
  );

  const state: ChatViewState = messagesQuery.isPending
    ? "loading"
    : messagesQuery.isError
      ? "error"
      : "ready";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ChatView
        state={state}
        messages={messagesQuery.data ?? []}
        streamingId={streamingId}
        streamingText={streamingText}
        draft={draft}
        sending={send.isPending}
        providerNameById={providerNameById}
        onDraftChange={setDraft}
        onSend={() => {
          const content = draft.trim();
          if (!content || send.isPending) return;
          setDraft("");
          send.mutate(content);
        }}
        onStop={stopStream}
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
        evidence={citation?.evidence ?? null}
        onOpenChange={setPanelOpen}
      />
    </div>
  );
}
