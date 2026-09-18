import { createFileRoute } from "@tanstack/react-router";
import { RoleDetailContainer } from "@/components/role/RoleDetailContainer";
import {
  isRoleDetailTabId,
  type RoleDetailTabId,
} from "@/components/role/role-detail-tabs";

type RoleSearch = {
  tab?: RoleDetailTabId;
};

export const Route = createFileRoute("/roles/$id")({
  validateSearch: (search: Record<string, unknown>): RoleSearch => {
    const raw = search["tab"];
    if (typeof raw === "string" && isRoleDetailTabId(raw)) {
      return { tab: raw };
    }
    return {};
  },
  head: () => ({
    meta: [
      { title: "Role fit — Career Intelligence" },
      {
        name: "description",
        content:
          "Requirement-by-requirement fit for a single role, with CV evidence.",
      },
      { property: "og:title", content: "Role fit — Career Intelligence" },
      {
        property: "og:description",
        content:
          "Requirement-by-requirement fit for a single role, with CV evidence.",
      },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: RolePage,
});

function RolePage() {
  const { id } = Route.useParams();
  return <RoleDetailContainer roleId={id} />;
}
