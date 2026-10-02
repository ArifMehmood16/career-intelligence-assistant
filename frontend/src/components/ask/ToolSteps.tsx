import type { ToolStep } from "@/types";

const TOOL_LABELS: Record<string, string> = {
  list_roles: "Listed your roles",
  search_evidence: "Searched your documents",
  get_role_analysis: "Read a role's analysis",
  explain_requirement: "Looked up a requirement",
  get_gap_plan: "Read a gap plan",
  compare_roles: "Compared two roles",
  skill_experience: "Looked up a skill",
  get_chunk: "Opened a passage",
};

function outcome(step: ToolStep): string {
  if (step.failed) return "Nothing found";
  if (step.found === 0) return "No passages";
  return step.found === 1 ? "1 passage" : `${step.found} passages`;
}

export interface ToolStepsProps {
  steps: ToolStep[];
}

/** The tools the agent called for this answer: what it asked, what came back. */
export function ToolSteps({ steps }: ToolStepsProps) {
  if (steps.length === 0) return null;
  const count =
    steps.length === 1 ? "1 tool call" : `${steps.length} tool calls`;
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">
        Found using {count}
      </summary>
      <ol className="mt-2 space-y-1.5 pl-1">
        {steps.map((step, index) => (
          <li key={`${step.name}-${index}`} className="space-y-0.5">
            <span className="block">
              {index + 1}. {TOOL_LABELS[step.name] ?? step.name}
              <span className="text-muted-foreground"> · {outcome(step)}</span>
            </span>
            {Object.entries(step.arguments).map(([key, value]) => (
              <span
                key={key}
                className="block pl-4 font-mono text-xs text-muted-foreground"
              >
                {key}: {value}
              </span>
            ))}
          </li>
        ))}
      </ol>
    </details>
  );
}
