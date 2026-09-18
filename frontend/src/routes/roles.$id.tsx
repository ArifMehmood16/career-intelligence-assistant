import { createFileRoute } from "@tanstack/react-router";
import { RoleDetailContainer } from "@/components/role/RoleDetailContainer";

export const Route = createFileRoute("/roles/$id")({
  head: () => ({
    meta: [
      { title: "Role fit — CIA" },
      {
        name: "description",
        content:
          "Requirement-by-requirement fit for a single role, with CV evidence.",
      },
      { property: "og:title", content: "Role fit — CIA" },
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
