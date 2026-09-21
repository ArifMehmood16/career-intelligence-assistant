import { createFileRoute } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import { ChatView } from "@/components/ask/ChatView";
import { EvidencePanel } from "@/components/EvidencePanel";
import { ProviderBadge } from "@/components/ProviderBadge";
import { BulletDraftPanel } from "@/components/role/BulletDraftPanel";
import { GapsPanel } from "@/components/role/GapsPanel";
import { LetterPanel } from "@/components/role/LetterPanel";
import { PreparePanel } from "@/components/role/PreparePanel";
import { RequirementTable } from "@/components/role/RequirementTable";
import { RoleDetailTabs } from "@/components/role/RoleDetailTabs";
import { ProviderSettings } from "@/components/settings/ProviderSettings";
import { ComparePanel } from "@/components/workspace/ComparePanel";
import { CoverLettersCard } from "@/components/workspace/CoverLettersCard";
import { CvCard } from "@/components/workspace/CvCard";
import { RankingPanel } from "@/components/workspace/RankingPanel";
import { RolesPanel } from "@/components/workspace/RolesPanel";
import { Button } from "@/components/ui/button";
import type {
  BulletDraft,
  ChatMessage,
  Comparison,
  CoverLetterDraft,
  CvDocument,
  Evidence,
  GapItem,
  InterviewPack,
  Provider,
  RankedRole,
  Requirement,
  Role,
  SupportingDocument,
} from "@/types";

export const Route = createFileRoute("/dev/states")({
  head: () => ({
    meta: [
      { title: "Component states — Career Intelligence" },
      {
        name: "description",
        content: "Gallery of every component state rendered from props alone.",
      },
      {
        property: "og:title",
        content: "Component states — Career Intelligence",
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
    status: "ready",
    updatedAt: "2026-09-12T10:00:00.000Z",
  },
  {
    id: "role-kestrel",
    title: "Analytics Engineer",
    company: "Kestrel Systems",
    fitScore: 61,
    bandLabel: "Partial match",
    counts: { met: 4, partial: 3, missing: 3 },
    status: "ready",
    updatedAt: "2026-09-12T10:05:00.000Z",
  },
  {
    id: "role-halden",
    title: "Machine Learning Engineer",
    company: "Halden Data Group",
    fitScore: 34,
    bandLabel: "Limited match",
    counts: { met: 2, partial: 2, missing: 5 },
    status: "ready",
    updatedAt: "2026-09-12T10:10:00.000Z",
  },
];

const matchedEvidence: Evidence = {
  spanId: "span-cv-demo-sql",
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
      spanId: "span-cv-demo-dbt",
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
        spanId: "span-cv-demo-dbt-2",
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
  leftMachine: false,
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
  leftMachine: false,
};

const streamingMessage: ChatMessage = {
  id: "msg-streaming",
  author: "assistant",
  content: "The strongest evidence for this role is the warehouse SQL work.",
  kind: "answer",
  citations: [],
  model: "built-in-offline",
  provider: "builtin",
  leftMachine: false,
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

const sampleGapItems: GapItem[] = [
  {
    requirementId: "req-missing",
    requirementText: "Hands-on Terraform for infrastructure as code",
    type: "must",
    status: "missing",
    reason: "no_related_claim",
    adjacentEvidence: null,
    scoreDelta: 12,
    action: "learn_it",
    canDraftBullet: false,
  },
  {
    requirementId: "req-partial",
    requirementText: "Owns a production dbt project end to end",
    type: "must",
    status: "partial",
    reason: "adjacent_claim_only",
    adjacentEvidence: matchedEvidence,
    scoreDelta: 9,
    action: "evidence_it",
    canDraftBullet: true,
  },
];

const sampleBulletDraft: BulletDraft = {
  id: "bullet-demo",
  version: 1,
  createdAt: "2026-09-18T12:00:00.000Z",
  requirementId: "req-partial",
  bullets: [
    {
      text: "- Introduced dbt for a subset of warehouse models covering a third of reporting tables.",
      spanIds: ["span-cv-demo-dbt"],
      evidence: [
        {
          spanId: "span-cv-demo-dbt",
          documentId: "cv-demo",
          page: 2,
          paragraph:
            "Later I introduced dbt for a subset of the warehouse models, covering roughly a third of the reporting tables before I moved on.",
          highlight: "covering roughly a third of the reporting tables",
        },
      ],
    },
  ],
  provenance: {
    provider: "hermetic",
    model: null,
    leftMachine: false,
    generatedAt: "2026-09-18T12:00:00.000Z",
    grounded: true,
    fallback: "template",
  },
};

const sampleInterviewPack: InterviewPack = {
  roleId: "role-kestrel",
  probes: [
    {
      requirementId: "req-met",
      question: "Walk me through your production SQL work.",
      status: "met",
    },
  ],
  leadWith: [
    {
      requirementId: "req-met",
      evidence: matchedEvidence,
      note: "Lead with the warehouse SQL story.",
    },
  ],
  thinAreas: [
    {
      requirementId: "req-missing",
      requirementText: "Hands-on Terraform for infrastructure as code",
      nearest: null,
    },
  ],
  askThem: [
    {
      question: "What does ownership of the analytics platform look like here?",
      requirementId: null,
    },
  ],
  provenance: {
    provider: "hermetic",
    model: null,
    leftMachine: false,
    generatedAt: "2026-09-18T12:00:00.000Z",
    grounded: true,
    fallback: "template",
  },
};

const sampleCoverLetter: CoverLetterDraft = {
  id: "cl-demo",
  version: 1,
  createdAt: "2026-09-18T12:00:00.000Z",
  roleId: "role-kestrel",
  paragraphs: [
    {
      text: "I am applying for the Analytics Engineer role at Kestrel Systems.",
      requirementIds: ["req-met"],
      spanIds: ["span-cv-demo-sql"],
    },
  ],
  omittedReason: null,
  provenance: {
    provider: "hermetic",
    model: null,
    leftMachine: false,
    generatedAt: "2026-09-18T12:00:00.000Z",
    grounded: true,
    fallback: "template",
  },
};

const sampleSupporting: SupportingDocument = {
  id: "sup-demo",
  kind: "cover_letter",
  filename: "previous-cover-letter.docx",
  mediaType:
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  byteLength: 2400,
  pageCount: 1,
  parsedAt: "2026-09-18T11:00:00.000Z",
  createdAt: "2026-09-18T11:00:00.000Z",
};

const sampleRanked: RankedRole[] = [
  {
    role: sampleRoles[0]!,
    rank: 1,
    tied: false,
    because: ["5+ years of advanced SQL in a production warehouse"],
  },
  {
    role: sampleRoles[1]!,
    rank: 2,
    tied: true,
    because: ["Owns a production dbt project end to end"],
  },
  {
    role: sampleRoles[2]!,
    rank: 2,
    tied: true,
    because: ["Hands-on Terraform for infrastructure as code"],
  },
];

const sampleComparison: Comparison = {
  a: sampleRoles[0]!,
  b: sampleRoles[1]!,
  shared: [
    {
      text: "Advanced SQL in a production warehouse",
      aStatus: "met",
      bStatus: "partial",
    },
  ],
  onlyInA: [sampleRequirements[2]!],
  onlyInB: [sampleRequirements[0]!],
  differentiator: "Advanced SQL in a production warehouse",
};

/** Section titles rendered on /dev/states — kept for the gallery smoke test. */
export const DEV_STATE_SECTION_TITLES = [
  "CV card: empty",
  "CV card: parsing",
  "CV card: parsed",
  "CV card: error",
  "Roles table: loading",
  "Roles table: empty",
  "Roles table: error",
  "Roles table: populated",
  "Roles stacked cards: populated",
  "Requirement table: all three status groups",
  "Requirement table: mobile card variant",
  "Evidence panel: matched requirement",
  "Evidence panel: missing requirement",
  "Chat: empty with starter chips",
  "Chat: streaming",
  "Chat: answered with citations",
  "Chat: insufficient evidence",
  "Provider cards: available, selected, and each unavailable reason",
  "Egress dialog: open",
  "Provider badge: local",
  "Provider badge: hosted",
  "Cover letters card: ready",
  "Role detail tabs",
  "Gaps panel: ready",
  "Gaps panel: empty",
  "Bullet draft: template fallback",
  "Prepare panel: ready",
  "Letter panel: refusal next step",
  "Letter panel: generated draft",
  "Ranking panel: ties",
  "Compare panel: ready",
] as const;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 border-b border-border pb-8">
      <h2 className="text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export function DevStatesPage() {
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
          onDelete={noop}
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
          onDelete={noop}
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
                kind: "question",
                citations: [],
                model: null,
                provider: null,
                leftMachine: false,
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
                kind: "question",
                citations: [],
                model: null,
                provider: null,
                leftMachine: false,
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
          pendingReindex={null}
          saveError={null}
          onSelect={noop}
          onModelChange={noop}
          onConfirmHosted={noop}
          onCancelHosted={noop}
          onConfirmReindex={noop}
          onCancelReindex={noop}
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
          pendingReindex={null}
          saveError={null}
          onSelect={noop}
          onModelChange={noop}
          onConfirmHosted={() => setEgressOpen(false)}
          onCancelHosted={() => setEgressOpen(false)}
          onConfirmReindex={noop}
          onCancelReindex={noop}
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

      <Section title="Cover letters card: ready">
        <CoverLettersCard
          state="ready"
          documents={[sampleSupporting]}
          errorMessage={null}
          uploading={false}
          onUpload={noop}
          onDelete={noop}
          onRetry={noop}
        />
      </Section>

      <Section title="Role detail tabs">
        <RoleDetailTabs
          value="fit"
          onValueChange={noop}
          fit={<p className="text-sm text-muted-foreground">Fit pane</p>}
          gaps={<p className="text-sm text-muted-foreground">Gaps pane</p>}
          prepare={
            <p className="text-sm text-muted-foreground">Prepare pane</p>
          }
          letter={<p className="text-sm text-muted-foreground">Letter pane</p>}
        />
      </Section>

      <Section title="Gaps panel: ready">
        <GapsPanel
          state="ready"
          currentScore={61}
          items={sampleGapItems}
          onRetry={noop}
          onSelectEvidence={noop}
          onDraftBullet={noop}
        />
      </Section>

      <Section title="Gaps panel: empty">
        <GapsPanel
          state="empty"
          currentScore={100}
          items={[]}
          onRetry={noop}
          onSelectEvidence={noop}
          onDraftBullet={noop}
        />
      </Section>

      <Section title="Bullet draft: template fallback">
        <BulletDraftPanel
          state="ready"
          draft={sampleBulletDraft}
          onRetry={noop}
          onCopy={noop}
          onCitation={noop}
          onDismiss={noop}
        />
      </Section>

      <Section title="Prepare panel: ready">
        <PreparePanel
          state="ready"
          pack={sampleInterviewPack}
          onRetry={noop}
          onSelectEvidence={noop}
          onExport={noop}
        />
      </Section>

      <Section title="Letter panel: refusal next step">
        <LetterPanel
          tone="plain"
          includeGapLine={false}
          generating={false}
          draft={null}
          versions={[]}
          refusal={{
            message:
              "Fewer than two must-have requirements are met. Use the gap plan instead.",
          }}
          supportingDocuments={[sampleSupporting]}
          onToneChange={noop}
          onIncludeGapLineChange={noop}
          onGenerate={noop}
          onSelectVersion={noop}
          onExport={noop}
          onCitation={noop}
          onOpenGaps={noop}
        />
      </Section>

      <Section title="Letter panel: generated draft">
        <LetterPanel
          tone="warm"
          includeGapLine={true}
          generating={false}
          draft={sampleCoverLetter}
          versions={[sampleCoverLetter]}
          refusal={null}
          supportingDocuments={[]}
          onToneChange={noop}
          onIncludeGapLineChange={noop}
          onGenerate={noop}
          onSelectVersion={noop}
          onExport={noop}
          onCitation={noop}
          onOpenGaps={noop}
        />
      </Section>

      <Section title="Ranking panel: ties">
        <RankingPanel state="ready" ranked={sampleRanked} onRetry={noop} />
      </Section>

      <Section title="Compare panel: ready">
        <ComparePanel
          roles={sampleRoles}
          roleAId={sampleRoles[0]!.id}
          roleBId={sampleRoles[1]!.id}
          state="ready"
          comparison={sampleComparison}
          onRoleAChange={noop}
          onRoleBChange={noop}
          onCompare={noop}
          onRetry={noop}
          onOpenGaps={noop}
        />
      </Section>
    </div>
  );
}
