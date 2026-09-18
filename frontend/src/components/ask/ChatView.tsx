import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { ChatMessage, Citation } from "@/types";

export type ChatViewState = "loading" | "error" | "ready";

export const STARTER_PROMPTS = [
  "What am I missing for this role?",
  "Compare my fit across all roles",
  "What will they probe in interview?",
] as const;

export interface ChatViewProps {
  state: ChatViewState;
  messages: ChatMessage[];
  /** Id of the assistant message currently being revealed, if any. */
  streamingId: string | null;
  /** Partial text shown while streaming. */
  streamingText: string;
  draft: string;
  sending: boolean;
  providerNameById: Record<string, string>;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  onCitation: (citation: Citation) => void;
  onRetry: () => void;
}

export function ChatView({
  state,
  messages,
  streamingId,
  streamingText,
  draft,
  sending,
  providerNameById,
  onDraftChange,
  onSend,
  onStop,
  onCitation,
  onRetry,
}: ChatViewProps) {
  const empty = state === "ready" && messages.length === 0;

  return (
    <div className="mx-auto flex h-full w-full max-w-[760px] flex-col">
      <div className="flex flex-1 flex-col gap-5 pb-4">
        {state === "loading" ? (
          <>
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-24 w-full" />
          </>
        ) : null}

        {state === "error" ? (
          <div className="card-surface space-y-3">
            <p>That conversation could not be loaded.</p>
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              Retry
            </Button>
          </div>
        ) : null}

        {state === "ready"
          ? messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                streaming={message.id === streamingId}
                streamingText={streamingText}
                providerNameById={providerNameById}
                onCitation={onCitation}
              />
            ))
          : null}
      </div>

      <div className="sticky bottom-0 space-y-3 border-t border-border bg-background pt-3 pb-4">
        {empty ? (
          <div className="flex flex-wrap gap-2">
            {STARTER_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => onDraftChange(prompt)}
                className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}

        <div className="flex items-end gap-2">
          <Textarea
            rows={2}
            value={draft}
            placeholder="Ask about your CV and the roles you saved"
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSend();
              }
            }}
          />
          {streamingId ? (
            <Button type="button" variant="outline" onClick={onStop}>
              Stop
            </Button>
          ) : (
            <Button
              type="button"
              onClick={onSend}
              disabled={sending || !draft.trim()}
            >
              Send
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  streaming,
  streamingText,
  providerNameById,
  onCitation,
}: {
  message: ChatMessage;
  streaming: boolean;
  streamingText: string;
  providerNameById: Record<string, string>;
  onCitation: (citation: Citation) => void;
}) {
  if (message.author === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-md border border-border bg-surface px-3 py-2">
          {message.content}
        </p>
      </div>
    );
  }

  const insufficient = message.kind === "insufficient";
  const body = streaming ? streamingText : message.content;

  return (
    <div
      className={
        insufficient
          ? "space-y-3 rounded-md border border-border border-l-2 bg-surface px-3 py-3"
          : "space-y-3 rounded-md border border-border bg-surface px-3 py-3"
      }
    >
      {insufficient ? (
        <p className="text-xs font-medium">Not enough evidence</p>
      ) : null}

      <p className="whitespace-pre-wrap">
        {body}
        {streaming ? (
          <span
            aria-hidden="true"
            className="ml-0.5 inline-block h-4 w-[7px] translate-y-[2px] bg-foreground"
          />
        ) : null}
      </p>

      {insufficient && !streaming ? (
        <p>
          Next step: add the detail to your CV, or ask about something the
          parsed document covers.
        </p>
      ) : null}

      {!streaming && message.citations.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {message.citations.map((citation) => (
            <button
              key={citation.id}
              type="button"
              onClick={() => onCitation(citation)}
              className="rounded-md border border-border bg-background px-2 py-1 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {citation.label}
            </button>
          ))}
        </div>
      ) : null}

      {!streaming && message.model ? (
        <p className="font-mono text-[11px] text-muted-foreground">
          {message.model}{" "}
          {message.provider
            ? (providerNameById[message.provider] ?? message.provider)
            : "unknown provider"}
        </p>
      ) : null}
    </div>
  );
}
