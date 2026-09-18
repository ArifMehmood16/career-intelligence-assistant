import { createFileRoute } from "@tanstack/react-router";
import { ComparePanelContainer } from "@/components/workspace/ComparePanelContainer";
import { CoverLettersCardContainer } from "@/components/workspace/CoverLettersCardContainer";
import { CvCardContainer } from "@/components/workspace/CvCardContainer";
import { RankingPanelContainer } from "@/components/workspace/RankingPanelContainer";
import { RolesPanelContainer } from "@/components/workspace/RolesPanelContainer";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Workspace — Career Intelligence" },
      {
        name: "description",
        content:
          "Match your CV against saved job descriptions and see where the evidence sits.",
      },
      { property: "og:title", content: "Workspace — Career Intelligence" },
      {
        property: "og:description",
        content:
          "Match your CV against saved job descriptions and see where the evidence sits.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: WorkspacePage,
});

function WorkspacePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl">Workspace</h1>
      <div className="flex flex-col gap-6 min-[900px]:flex-row min-[900px]:items-start">
        <div className="space-y-6 min-[900px]:w-[380px] min-[900px]:shrink-0">
          <CvCardContainer />
          <CoverLettersCardContainer />
        </div>
        <div className="min-w-0 flex-1 space-y-6">
          <RolesPanelContainer />
          <RankingPanelContainer />
          <ComparePanelContainer />
        </div>
      </div>
    </div>
  );
}
