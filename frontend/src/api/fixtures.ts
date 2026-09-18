import type {
  BreakdownRow,
  ChatMessage,
  CvDocument,
  Provider,
  ProviderChoice,
  Requirement,
  Role,
} from "@/types";

export const cvFixture: CvDocument = {
  id: "cv-1",
  filename: "a-mehmood-cv.pdf",
  pageCount: 3,
  parsedAt: "2026-09-12T09:41:00.000Z",
};

export const rolesFixture: Role[] = [
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

const P = {
  sql: "Between 2021 and 2024 I owned the reporting layer for a retail analytics platform, writing and tuning complex SQL across a 4TB Postgres warehouse and cutting the nightly batch window from six hours to ninety minutes.",
  python:
    "Day to day I worked in Python, building pandas pipelines and small internal libraries that standardised how the team cleaned and validated incoming supplier feeds before loading.",
  dashboards:
    "I designed and maintained twenty two production dashboards used by the commercial and supply chain teams, running fortnightly sessions with stakeholders to keep the metric definitions honest.",
  leadership:
    "I mentored two junior analysts through their first year, reviewing their queries and pairing with them weekly, and I ran the internal analytics guild for eighteen months.",
  dbt: "Later I introduced dbt for a subset of the warehouse models, covering roughly a third of the reporting tables before I moved on, with tests on the primary keys and freshness checks on the sources.",
  cloud:
    "Most of this ran on AWS, mainly S3, Redshift and scheduled jobs on ECS, with infrastructure defined by a platform team that I worked alongside rather than owned.",
  stats:
    "My degree was in Economics with a heavy statistics component, and I have since applied regression and time series forecasting to demand planning problems in a commercial setting.",
  viz: "I have presented findings to the executive team quarterly, translating model output into plain recommendations with an explicit note on where the numbers were weakest.",
};

const ev = (page: number, paragraph: string, highlight: string) => ({
  spanId: `span-${cvFixture.id}-${page}-${highlight.slice(0, 12)}`,
  documentId: cvFixture.id,
  page,
  paragraph,
  highlight,
});

export const requirementsFixture: Requirement[] = [
  // Northwind Analytics
  {
    id: "req-nw-1",
    roleId: "role-northwind",
    text: "5+ years of advanced SQL in a production warehouse",
    type: "must",
    status: "met",
    evidence: ev(
      1,
      P.sql,
      "writing and tuning complex SQL across a 4TB Postgres warehouse",
    ),
  },
  {
    id: "req-nw-2",
    roleId: "role-northwind",
    text: "Python for data manipulation and pipeline work",
    type: "must",
    status: "met",
    evidence: ev(
      1,
      P.python,
      "building pandas pipelines and small internal libraries",
    ),
  },
  {
    id: "req-nw-3",
    roleId: "role-northwind",
    text: "Owns BI dashboards used by non-technical stakeholders",
    type: "must",
    status: "met",
    evidence: ev(2, P.dashboards, "twenty two production dashboards"),
  },
  {
    id: "req-nw-4",
    roleId: "role-northwind",
    text: "Experience mentoring junior analysts",
    type: "desirable",
    status: "met",
    evidence: ev(
      2,
      P.leadership,
      "I mentored two junior analysts through their first year",
    ),
  },
  {
    id: "req-nw-5",
    roleId: "role-northwind",
    text: "Statistical forecasting applied to commercial problems",
    type: "desirable",
    status: "met",
    evidence: ev(
      3,
      P.stats,
      "regression and time series forecasting to demand planning problems",
    ),
  },
  {
    id: "req-nw-6",
    roleId: "role-northwind",
    text: "Comfortable presenting to executive audiences",
    type: "desirable",
    status: "met",
    evidence: ev(
      3,
      P.viz,
      "presented findings to the executive team quarterly",
    ),
  },
  {
    id: "req-nw-7",
    roleId: "role-northwind",
    text: "dbt model ownership across the warehouse",
    type: "must",
    status: "partial",
    evidence: ev(2, P.dbt, "covering roughly a third of the reporting tables"),
  },
  {
    id: "req-nw-8",
    roleId: "role-northwind",
    text: "Working knowledge of a major cloud platform",
    type: "desirable",
    status: "partial",
    evidence: ev(2, P.cloud, "mainly S3, Redshift and scheduled jobs on ECS"),
  },
  {
    id: "req-nw-9",
    roleId: "role-northwind",
    text: "Retail pricing and promotions domain exposure",
    type: "desirable",
    status: "missing",
    evidence: null,
  },

  // Kestrel Systems
  {
    id: "req-ks-1",
    roleId: "role-kestrel",
    text: "Production dbt project ownership end to end",
    type: "must",
    status: "partial",
    evidence: ev(
      2,
      P.dbt,
      "I introduced dbt for a subset of the warehouse models",
    ),
  },
  {
    id: "req-ks-2",
    roleId: "role-kestrel",
    text: "Advanced SQL and query performance tuning",
    type: "must",
    status: "met",
    evidence: ev(
      1,
      P.sql,
      "cutting the nightly batch window from six hours to ninety minutes",
    ),
  },
  {
    id: "req-ks-3",
    roleId: "role-kestrel",
    text: "Python engineering beyond notebooks",
    type: "must",
    status: "met",
    evidence: ev(1, P.python, "small internal libraries"),
  },
  {
    id: "req-ks-4",
    roleId: "role-kestrel",
    text: "Data quality testing and source freshness checks",
    type: "desirable",
    status: "met",
    evidence: ev(
      2,
      P.dbt,
      "tests on the primary keys and freshness checks on the sources",
    ),
  },
  {
    id: "req-ks-5",
    roleId: "role-kestrel",
    text: "Stakeholder-facing metric definition work",
    type: "desirable",
    status: "met",
    evidence: ev(2, P.dashboards, "keep the metric definitions honest"),
  },
  {
    id: "req-ks-6",
    roleId: "role-kestrel",
    text: "Cloud warehouse administration",
    type: "desirable",
    status: "partial",
    evidence: ev(
      2,
      P.cloud,
      "a platform team that I worked alongside rather than owned",
    ),
  },
  {
    id: "req-ks-7",
    roleId: "role-kestrel",
    text: "Airflow or Dagster orchestration in production",
    type: "must",
    status: "partial",
    evidence: ev(2, P.cloud, "scheduled jobs on ECS"),
  },
  {
    id: "req-ks-8",
    roleId: "role-kestrel",
    text: "Terraform or equivalent infrastructure as code",
    type: "must",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-ks-9",
    roleId: "role-kestrel",
    text: "Streaming ingestion with Kafka",
    type: "desirable",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-ks-10",
    roleId: "role-kestrel",
    text: "On-call rotation for data platform incidents",
    type: "desirable",
    status: "missing",
    evidence: null,
  },

  // Halden Data Group
  {
    id: "req-hd-1",
    roleId: "role-halden",
    text: "Applied statistics and modelling background",
    type: "must",
    status: "met",
    evidence: ev(3, P.stats, "a heavy statistics component"),
  },
  {
    id: "req-hd-2",
    roleId: "role-halden",
    text: "Strong Python fundamentals",
    type: "must",
    status: "met",
    evidence: ev(1, P.python, "Day to day I worked in Python"),
  },
  {
    id: "req-hd-3",
    roleId: "role-halden",
    text: "Forecasting models shipped to users",
    type: "desirable",
    status: "partial",
    evidence: ev(
      3,
      P.stats,
      "time series forecasting to demand planning problems",
    ),
  },
  {
    id: "req-hd-4",
    roleId: "role-halden",
    text: "Model deployment on cloud infrastructure",
    type: "must",
    status: "partial",
    evidence: ev(2, P.cloud, "Most of this ran on AWS"),
  },
  {
    id: "req-hd-5",
    roleId: "role-halden",
    text: "Deep learning frameworks such as PyTorch",
    type: "must",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-hd-6",
    roleId: "role-halden",
    text: "MLOps tooling and experiment tracking",
    type: "must",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-hd-7",
    roleId: "role-halden",
    text: "Feature store design",
    type: "desirable",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-hd-8",
    roleId: "role-halden",
    text: "Published research or conference talks",
    type: "desirable",
    status: "missing",
    evidence: null,
  },
  {
    id: "req-hd-9",
    roleId: "role-halden",
    text: "Experience with large language model evaluation",
    type: "desirable",
    status: "missing",
    evidence: null,
  },
];

export const breakdownFixture: Record<string, BreakdownRow[]> = {
  "role-northwind": [
    {
      id: "must",
      label: "Must-have coverage",
      value: 78,
      requirementIds: ["req-nw-1", "req-nw-2", "req-nw-3", "req-nw-7"],
    },
    {
      id: "desirable",
      label: "Desirable coverage",
      value: 80,
      requirementIds: [
        "req-nw-4",
        "req-nw-5",
        "req-nw-6",
        "req-nw-8",
        "req-nw-9",
      ],
    },
    {
      id: "recency",
      label: "Recency of evidence",
      value: 90,
      requirementIds: ["req-nw-1", "req-nw-2"],
    },
  ],
  "role-kestrel": [
    {
      id: "must",
      label: "Must-have coverage",
      value: 55,
      requirementIds: [
        "req-ks-1",
        "req-ks-2",
        "req-ks-3",
        "req-ks-7",
        "req-ks-8",
      ],
    },
    {
      id: "desirable",
      label: "Desirable coverage",
      value: 50,
      requirementIds: [
        "req-ks-4",
        "req-ks-5",
        "req-ks-6",
        "req-ks-9",
        "req-ks-10",
      ],
    },
    {
      id: "recency",
      label: "Recency of evidence",
      value: 72,
      requirementIds: ["req-ks-1", "req-ks-4"],
    },
  ],
  "role-halden": [
    {
      id: "must",
      label: "Must-have coverage",
      value: 30,
      requirementIds: [
        "req-hd-1",
        "req-hd-2",
        "req-hd-4",
        "req-hd-5",
        "req-hd-6",
      ],
    },
    {
      id: "desirable",
      label: "Desirable coverage",
      value: 22,
      requirementIds: ["req-hd-3", "req-hd-7", "req-hd-8", "req-hd-9"],
    },
    {
      id: "recency",
      label: "Recency of evidence",
      value: 48,
      requirementIds: ["req-hd-3"],
    },
  ],
};

export const messagesFixture: ChatMessage[] = [
  {
    id: "msg-1",
    author: "user",
    content:
      "Where does my CV fall short for the Kestrel Systems analytics engineer role?",
    kind: "question",
    citations: [],
    model: null,
    provider: null,
    leftMachine: false,
  },
  {
    id: "msg-2",
    author: "assistant",
    content:
      "Two must-have requirements have no supporting evidence in the CV: infrastructure as code with Terraform, and full ownership of a production dbt project. The dbt work is present but limited in scope.",
    kind: "answer",
    citations: [
      {
        id: "cit-1",
        label: "CV page 2, dbt adoption",
        evidence: ev(
          2,
          P.dbt,
          "covering roughly a third of the reporting tables",
        ),
      },
      {
        id: "cit-2",
        label: "CV page 2, infrastructure",
        evidence: ev(
          2,
          P.cloud,
          "a platform team that I worked alongside rather than owned",
        ),
      },
    ],
    model: "built-in-offline",
    provider: "builtin",
    leftMachine: false,
  },
  {
    id: "msg-3",
    author: "assistant",
    content:
      "The CV does not contain enough information to answer that. No salary expectations or compensation history appear in the parsed document.",
    kind: "insufficient",
    citations: [],
    model: "built-in-offline",
    provider: "builtin",
    leftMachine: false,
  },
];

export const providersFixture: Provider[] = [
  {
    id: "builtin",
    name: "Built-in offline mode",
    kind: "local",
    models: ["built-in-offline"],
    available: true,
    unavailableReason: null,
  },
  {
    id: "local-server",
    name: "Local model server",
    kind: "local",
    models: ["llama3.1:8b", "qwen2.5:14b"],
    available: false,
    unavailableReason:
      "Local model server not reachable at http://localhost:11434.",
  },
  {
    id: "openai",
    name: "OpenAI",
    kind: "hosted",
    models: ["gpt-4.1", "gpt-4.1-mini"],
    available: false,
    unavailableReason: "No API key configured on the server.",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    kind: "hosted",
    models: ["claude-sonnet-4", "claude-haiku-4"],
    available: false,
    unavailableReason: "External providers are turned off for this deployment.",
  },
];

export const providerChoiceFixture: ProviderChoice = {
  answerProviderId: "builtin",
  answerModel: "built-in-offline",
  indexProviderId: "builtin",
  indexModel: "built-in-offline",
};
