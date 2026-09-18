import { createFileRoute } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import { ChatView } from "@/components/ask/ChatView";
import { EvidencePanel } from "@/components/EvidencePanel";
import { ProviderBadge } from "@/components/ProviderBadge";
import { RequirementTable } from "@/components/role/RequirementTable";
import { ProviderSettings } from "@/components/settings/ProviderSettings";
import { CvCard } from "@/components/workspace/CvCard";
import { RolesPanel } from "@/components/workspace/RolesPanel";
import { Button } from "@/components/ui/button";
import type {
  ChatMessage,
  CvDocument,
  Evidence,
  Provider,
  Requirement,
  Role,
} from "@/types";

export const Route = createFileRoute("/dev/states")({
  head: () => ({
    meta: [
      { title: "Component states — CIA" },
      {
        name: "description",
        content: "Gallery of every component state rendered from props alone.",
      },
      {
        property: "og:title",
        content: "Component states — CIA",
      },
      {
        property: "og:description",
        content: "Gallery of every component state rendered from props alone.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: DevStatesPage,
});

const noop = () => undefined;

const sampleCv: CvDocument = {
  id: "cv-demo",
  filename: "a-mehmood-cv.pdf",
  pageCount: 3,
  parsedAt: "2026-09-12T09:41:00.000Z",
};

const sampleRoles: Role[] = [
  {
    id: "role-northwind",
    title: "Senior Data Analyst",
    company: "Northwind Analytics",
    fitScore: 82,
    bandLabel: "Strong match",
    counts: { met: 6, partial: 2, missing: 1 },
  },
  {
    id: "role-kestrel",
    title: "Analytics Engineer",
    company: "Kestrel Systems",
    fitScore: 61,
    bandLabel: "Partial match",
    counts: { met: 4, partial: 3, missing: 3 },
  },
  {
    id: "role-halden",
    title: "Machine Learning Engineer",
    company: "Halden Data Group",
    fitScore: 34,
    bandLabel: "Limited match",
    counts: { met: 2, partial: 2, missing: 5 },
  },
];

const matchedEvidence: Evidence = {
  documentId: "cv-demo",
  page: 1,
  paragraph:
    "Between 2021 and 2024 I owned the reporting layer for a retail analytics platform, writing and tuning complex SQL across a 4TB Postgres warehouse and cutting the nightly batch window from six hours to ninety minutes.",
  highlight: "writing and tuning complex SQL across a 4TB Postgres warehouse",
};

const sampleRequirements: Requirement[] = [
  {
    id: "req-missing",
    roleId: "role-kestrel",
    text: "Hands-on Terraform for infrastructure as code",
    type: "must",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-partial",
    roleId: "role-kestrel",
    text: "Owns a production dbt project end to end",
    type: "must",
    status: "partial",
    evidence: {
      documentId: "cv-demo",
      page: 2,
      paragraph:
        "Later I introduced dbt for a subset of the warehouse models, covering roughly a third of the reporting tables before I moved on.",
      highlight: "covering roughly a third of the reporting tables",
    },
  },
  {
    id: "req-met",
    roleId: "role-kestrel",
    text: "5+ years of advanced SQL in a production warehouse",
    type: "must",
    status: "met",
    evidence: matchedEvidence,
  },
];

const answeredMessage: ChatMessage = {
  id: "msg-answered",
  author: "assistant",
  content:
    "Two must-have requirements have no supporting evidence in the CV: infrastructure as code with Terraform, and full ownership of a production dbt project.",
  kind: "answer",
  citations: [
    {
      id: "cit-1",
      label: "CV p.2",
      evidence: {
        documentId: "cv-demo",
        page: 2,
        paragraph:
          "Later I introduced dbt for a subset of the warehouse models, covering roughly a third of the reporting tables before I moved on.",
        highlight: "covering roughly a third of the reporting tables",
      },
    },
    {
      id: "cit-2",
      label: "Senior Data Analyst — Northwind",
      evidence: matchedEvidence,
    },
  ],
  model: "built-in-offline",
  provider: "builtin",
};

const insufficientMessage: ChatMessage = {
  id: "msg-insufficient",
  author: "assistant",
  content:
    "The CV does not contain enough information to answer that. No salary expectations or compensation history appear in the parsed document.",
  kind: "insufficient",
  citations: [],
  model: "built-in-offline",
  provider: "builtin",
};

const streamingMessage: ChatMessage = {
  id: "msg-streaming",
  author: "assistant",
  content: "The strongest evidence for this role is the warehouse SQL work.",
  kind: "answer",
  citations: [],
  model: "built-in-offline",
  provider: "builtin",
};

const providerLocal: Provider = {
  id: "builtin",
  name: "Built-in offline mode",
  kind: "local",
  models: ["built-in-offline"],
  available: true,
  unavailableReason: null,
};

const providerLocalUnavailable: Provider = {
  id: "local-server",
  name: "Local model server",
  kind: "local",
  models: ["llama3.1:8b", "qwen2.5:14b"],
  available: false,
  unavailableReason:
    "Local model server not reachable at http://localhost:11434.",
};

const providerOpenAi: Provider = {
  id: "openai",
  name: "OpenAI",
  kind: "hosted",
  models: ["gpt-4.1", "gpt-4.1-mini"],
  available: false,
  unavailableReason: "No API key configured on the server.",
};

const providerAnthropic: Provider = {
  id: "anthropic",
  name: "Anthropic",
  kind: "hosted",
  models: ["claude-sonnet-4", "claude-haiku-4"],
  available: false,
  unavailableReason: "External providers are turned off for this deployment.",
};

const providerAnthropicAvailable: Provider = {
  ...providerAnthropic,
  available: true,
  unavailableReason: null,
};

const allProviders: Provider[] = [
  providerLocal,
  providerLocalUnavailable,
  providerOpenAi,
  providerAnthropic,
];

const providerNameById = Object.fromEntries(
  allProviders.map((provider) => [provider.id, provider.name]),
);

const chatNoops = {
  onDraftChange: noop,
  onSend: noop,
  onStop: noop,
  onCitation: noop,
  onRetry: noop,
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 border-b border-border pb-8">
      <h2 className="text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function DevStatesPage() {
  const [evidenceKind, setEvidenceKind] = useState<
    "matched" | "missing" | null
  >("matched");
  const [egressOpen, setEgressOpen] = useState(true);

  return (
    <div className="mx-auto max-w-[900px] space-y-8">
      <div>
        <h1 className="text-xl">Component states</h1>
        <p className="mt-1 text-muted-foreground">
          Every presentational component rendered from props alone. No data
          fetching.
        </p>
      </div>

      <Section title="CV card: empty">
        <CvCard
          state="empty"
          document={null}
          errorMessage={null}
          onUpload={noop}
          onReplace={noop}
          onDelete={noop}
          onRetry={noop}
        />
      </Section>

      <Section title="CV card: parsing">
        <CvCard
          state="parsing"
          document={null}
          errorMessage={null}
          onUpload={noop}
          onReplace={noop}
          onDelete={noop}
          onRetry={noop}
        />
      </Section>

      <Section title="CV card: parsed">
        <CvCard
          state="parsed"
          document={sampleCv}
          errorMessage={null}
          onUpload={noop}
          onReplace={noop}
          onDelete={noop}
          onRetry={noop}
        />
      </Section>

      <Section title="CV card: error">
        <CvCard
          state="error"
          document={null}
          errorMessage="That file type is not supported."
          onUpload={noop}
          onReplace={noop}
          onDelete={noop}
          onRetry={noop}
        />
      </Section>

      <Section title="Roles table: loading">
        <RolesPanel
          state="loading"
          roles={[]}
          sortKey="fit"
          sortDirection="desc"
          onSort={noop}
          onRetry={noop}
          addRoleSlot={null}
          layout="table"
        />
      </Section>

      <Section title="Roles table: empty">
        <RolesPanel
          state="empty"
          roles={[]}
          sortKey="fit"
          sortDirection="desc"
          onSort={noop}
          onRetry={noop}
          addRoleSlot={null}
          layout="table"
        />
      </Section>

      <Section title="Roles table: error">
        <RolesPanel
          state="error"
          roles={[]}
          sortKey="fit"
          sortDirection="desc"
          onSort={noop}
          onRetry={noop}
          addRoleSlot={null}
          layout="table"
        />
      </Section>

      <Section title="Roles table: populated">
        <RolesPanel
          state="ready"
          roles={sampleRoles}
          sortKey="fit"
          sortDirection="desc"
          onSort={noop}
          onRetry={noop}
          addRoleSlot={
            <Button type="button" size="sm">
              Add role
            </Button>
          }
          layout="table"
        />
      </Section>

      <Section title="Roles stacked cards: populated">
        <RolesPanel
          state="ready"
          roles={sampleRoles}
          sortKey="fit"
          sortDirection="desc"
          onSort={noop}
          onRetry={noop}
          addRoleSlot={
            <Button type="button" size="sm">
              Add role
            </Button>
          }
          layout="cards"
        />
      </Section>

      <Section title="Requirement table: all three status groups">
        <RequirementTable
          state="ready"
          requirements={sampleRequirements}
          collapsedGroups={[]}
          onToggleGroup={noop}
          onSelect={noop}
          onRetry={noop}
          layout="table"
        />
      </Section>

      <Section title="Requirement table: mobile card variant">
        <RequirementTable
          state="ready"
          requirements={sampleRequirements}
          collapsedGroups={[]}
          onToggleGroup={noop}
          onSelect={noop}
          onRetry={noop}
          layout="cards"
        />
      </Section>

      <Section title="Evidence panel: matched requirement">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setEvidenceKind("matched")}
        >
          Open matched evidence
        </Button>
      </Section>

      <Section title="Evidence panel: missing requirement">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setEvidenceKind("missing")}
        >
          Open missing evidence
        </Button>
      </Section>

      <EvidencePanel
        open={evidenceKind !== null}
        title={
          evidenceKind === "missing"
            ? "Hands-on Terraform for infrastructure as code"
            : "5+ years of advanced SQL in a production warehouse"
        }
        status={evidenceKind === "missing" ? "missing" : "met"}
        evidence={evidenceKind === "missing" ? null : matchedEvidence}
        onOpenChange={(open) => {
          if (!open) setEvidenceKind(null);
        }}
      />

      <Section title="Chat: empty with starter chips">
        <div className="h-[420px]">
          <ChatView
            state="ready"
            messages={[]}
            streamingId={null}
            streamingText=""
            draft=""
            sending={false}
            providerNameById={providerNameById}
            {...chatNoops}
          />
        </div>
      </Section>

      <Section title="Chat: streaming">
        <div className="h-[420px]">
          <ChatView
            state="ready"
            messages={[
              {
                id: "msg-user",
                author: "user",
                content: "Where is the strongest evidence for this role?",
                kind: "answer",
                citations: [],
                model: null,
                provider: null,
              },
              streamingMessage,
            ]}
            streamingId="msg-streaming"
            streamingText="The strongest evidence for this role"
            draft=""
            sending={false}
            providerNameById={providerNameById}
            {...chatNoops}
          />
        </div>
      </Section>

      <Section title="Chat: answered with citations">
        <div className="h-[420px]">
          <ChatView
            state="ready"
            messages={[
              {
                id: "msg-user-2",
                author: "user",
                content: "Where does my CV fall short for Kestrel?",
                kind: "answer",
                citations: [],
                model: null,
                provider: null,
              },
              answeredMessage,
            ]}
            streamingId={null}
            streamingText=""
            draft=""
            sending={false}
            providerNameById={providerNameById}
            {...chatNoops}
          />
        </div>
      </Section>

      <Section title="Chat: insufficient evidence">
        <div className="h-[320px]">
          <ChatView
            state="ready"
            messages={[insufficientMessage]}
            streamingId={null}
            streamingText=""
            draft=""
            sending={false}
            providerNameById={providerNameById}
            {...chatNoops}
          />
        </div>
      </Section>

      <Section title="Provider cards: available, selected, and each unavailable reason">
        <ProviderSettings
          state="ready"
          providers={allProviders}
          answerProviderId="builtin"
          answerModel="built-in-offline"
          indexProviderId="builtin"
          indexModel="built-in-offline"
          pendingProvider={null}
          onSelect={noop}
          onModelChange={noop}
          onConfirmHosted={noop}
          onCancelHosted={noop}
          onRetry={noop}
        />
      </Section>

      <Section title="Egress dialog: open">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setEgressOpen(true)}
        >
          Re-open egress dialog
        </Button>
        <ProviderSettings
          state="ready"
          providers={[providerLocal, providerAnthropicAvailable]}
          answerProviderId="builtin"
          answerModel="built-in-offline"
          indexProviderId="builtin"
          indexModel="built-in-offline"
          pendingProvider={egressOpen ? providerAnthropicAvailable : null}
          onSelect={noop}
          onModelChange={noop}
          onConfirmHosted={() => setEgressOpen(false)}
          onCancelHosted={() => setEgressOpen(false)}
          onRetry={noop}
        />
      </Section>

      <Section title="Provider badge: local">
        <ProviderBadge provider={providerLocal} model="built-in-offline" />
      </Section>

      <Section title="Provider badge: hosted">
        <ProviderBadge
          provider={providerAnthropicAvailable}
          model="claude-sonnet-4"
        />
      </Section>
    </div>
  );
}
