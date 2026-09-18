import { createFileRoute } from "@tanstack/react-router";
import { ChatContainer } from "@/components/ask/ChatContainer";

export const Route = createFileRoute("/ask")({
  head: () => ({
    meta: [
      { title: "Ask — CIA" },
      {
        name: "description",
        content:
          "Ask questions about your CV and role fit, answered with citations.",
      },
      { property: "og:title", content: "Ask — CIA" },
      {
        property: "og:description",
        content:
          "Ask questions about your CV and role fit, answered with citations.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AskPage,
});

function AskPage() {
  return (
    <div className="flex min-h-[calc(100vh-8.5rem)] flex-col gap-6">
      <h1 className="text-xl">Ask</h1>
      <div className="flex min-h-0 flex-1 flex-col">
        <ChatContainer />
      </div>
    </div>
  );
}
