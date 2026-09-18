import { createFileRoute } from "@tanstack/react-router";
import { ProviderSettingsContainer } from "@/components/settings/ProviderSettingsContainer";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — CIA" },
      {
        name: "description",
        content:
          "Choose the answering and indexing providers used for CV analysis.",
      },
      { property: "og:title", content: "Settings — CIA" },
      {
        property: "og:description",
        content:
          "Choose the answering and indexing providers used for CV analysis.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl">Settings</h1>
      <ProviderSettingsContainer />
    </div>
  );
}
