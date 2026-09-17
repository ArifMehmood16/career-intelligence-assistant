# Lovable prompt sequence

Replaces the single "brief to give Lovable" block in the frontend brief. The handover
checklist and screenshot list there still apply unchanged.

Five prompts, pasted in order. Wait for each build to finish, run the check line under
the prompt, then paste the next. Do not paste two at once — Lovable rewrites earlier
files when a prompt covers more than one screen.

If a check fails, fix it with a short follow-up message before moving on. Drift
compounds: a hex value that survives step 2 will be copied into every later component.

---

## Prompt 1 — Foundation and data layer

Builds no screens. This is deliberate: types, tokens and the data boundary set in one
place are what let the next four prompts stay consistent.

```text
Build the foundation for a career intelligence tool. A candidate uploads their CV and
adds job descriptions; the tool shows how well they match each role and lets them ask
questions about it. This step builds the design system, types, data layer and app
shell only. Routes exist but render a heading and nothing else.

HARD CONSTRAINTS — these hold for every later step too

- Frontend only. No Supabase, no auth, no backend, no edge functions, no database.
- TypeScript strict. No `any`.
- All data comes from `src/api/client.ts`. Components never import fixtures. No fetch
  calls anywhere else. This file is replaced with a real HTTP client later, so nothing
  outside it may know the data is fake.
- Every screen splits in two: a presentational component that takes props and holds no
  data fetching, and a container that calls the client and passes props down. Every
  state must be reachable by passing props alone.
- Design tokens are HSL custom properties in `index.css`, mapped in
  `tailwind.config.ts`. Components use semantic classes only: `bg-surface`,
  `text-muted-foreground`, `border-border`. No hex, no inline styles, no `bg-gray-100`,
  no `text-white`.
- Banned: gradients, glassmorphism, backdrop blur, emoji, hero sections, pill-shaped
  buttons, shadows larger than 2px, animated decorative backgrounds.
- No dependencies beyond react-router-dom, lucide-react and the shadcn/ui primitives
  actually used.

DESIGN TOKENS — use these exact values

Light:
  --background 0 0% 100%       --surface 240 5% 98%
  --foreground 240 10% 12%     --muted-foreground 240 4% 46%
  --border 240 6% 90%          --accent 221 70% 48%
Dark:
  --background 240 10% 6%      --surface 240 8% 10%
  --foreground 0 0% 96%        --muted-foreground 240 5% 62%
  --border 240 6% 18%          --accent 217 78% 60%
Status, never carried by colour alone:
  --met 152 45% 36%   --partial 38 72% 44%   --missing 240 4% 46%
Missing is neutral grey, not red. A gap is information, not an error.

Radius 6px throughout. The accent colour marks only: the active provider badge, focus
rings, and primary buttons.

Typography: Inter 400/500/600 from Google Fonts, -0.011em tracking on headings. IBM
Plex Mono for document excerpts, scores and model names. Base 14px. Tables 13px at
1.35 line height. `font-variant-numeric: tabular-nums` on every number.
Card padding 20px. Table row height 36px. Section gap 24px.

TYPES — put these in `src/types/index.ts` and use them everywhere

  CvDocument      { id; filename; pageCount: number; parsedAt: string }
  Evidence        { documentId; page: number; paragraph: string; highlight: string }
                  highlight must be an exact substring of paragraph
  Role            { id; title; company; fitScore: number; bandLabel: string;
                    counts: { met: number; partial: number; missing: number } }
  Requirement     { id; roleId; text; type: 'must' | 'desirable';
                    status: 'met' | 'partial' | 'missing'; evidence: Evidence | null }
  BreakdownRow    { id: 'must' | 'desirable' | 'recency'; label; value: number;
                    requirementIds: string[] }
  Citation        { id; label; evidence: Evidence }
  ChatMessage     { id; author: 'user' | 'assistant'; content;
                    kind: 'answer' | 'insufficient'; citations: Citation[];
                    model: string | null; provider: string | null }
  Provider        { id; name; kind: 'local' | 'hosted'; models: string[];
                    available: boolean; unavailableReason: string | null }
  ProviderChoice  { answerProviderId; answerModel; indexProviderId; indexModel }

DATA LAYER

`src/api/fixtures.ts` holds the placeholder data. `src/api/client.ts` exports async
functions that await a 400ms delay and return typed Promises:

  getCv, uploadCv, deleteCv, getRoles, getRole, getRequirements, getFitBreakdown,
  addRole, getMessages, sendMessage, getProviders, getProviderChoice, setProviderChoice

Fixture content:
- One parsed CV: "a-mehmood-cv.pdf", 3 pages.
- Three roles at clearly different fit levels, from invented companies: Northwind
  Analytics, Kestrel Systems, Halden Data Group.
- Eight to ten requirements per role, a mix of must and desirable, spread across all
  three statuses. Matched ones carry evidence with a realistic surrounding paragraph.
- A chat conversation of three messages, one of which has kind 'insufficient'.
- Four providers: a built-in offline mode and a local model server (kind 'local'),
  OpenAI and Anthropic (kind 'hosted'). Built-in offline mode is available; make the
  other three unavailable with these reasons verbatim:
    "No API key configured on the server."
    "External providers are turned off for this deployment."
    "Local model server not reachable at http://localhost:11434."

Never invent a scoring formula or a confidence percentage. Scores are plain numbers
sitting in the fixtures.

SHELL

Persistent top bar on every route: product name left, nav links (Workspace / Ask /
Settings) centre, active-provider badge and theme toggle right.

The badge is one shared component used everywhere a provider is shown:
  local  — outlined, neutral border, small filled square glyph
  hosted — solid accent fill, outward-arrow glyph
Tooltip gives provider and model name. The two must be distinguishable without colour.

Light and dark mode, toggle in the top bar, preference remembered.
Small footer link to /dev/states.

Routes registered now, each rendering only its page heading: /, /roles/:id, /ask,
/settings, /dev/states.
```

**Check before moving on:** `src/api/client.ts` exists and every function returns a
typed Promise; both themes render correctly; no hex values in any file.

---



## Prompt 2 — Workspace

```text
Continue the existing project. Do not restyle or rewrite anything from step 1. Data
only through src/api/client.ts. Semantic tokens only, no hex. Presentational component
plus container for each piece.

Build the / route: the Workspace.

Two columns. CV card fixed 380px on the left, roles panel filling the rest. Stacks to
one column below 900px.

CV CARD — four states, all driven by props
- empty: dropzone, "Upload your CV. PDF or DOCX, up to 10MB", browse button
- parsing: skeleton matching the parsed layout, "Parsing…"
- parsed: filename, page count, parsed timestamp, Replace and Delete actions
- error: plain message and a Retry button

ROLES PANEL
Table at 900px and above, stacked cards below. Columns:
  Role     title, with company underneath in muted text
  Fit      score out of 100 in mono, band label beside it
  Met / Partial / Missing   three separate numeric columns
Sorted by fit descending. Headers sortable. Whole row is a link to /roles/:id, keyboard
reachable, with a visible focus ring.

Real semantic table markup: thead, th with scope, tbody. Not a grid of divs.

States: skeleton rows while loading, empty state, error state with retry.

"Add role" button opens a dialog with two tabs, Upload file and Paste text. It writes
through the client and the list updates.

Before a CV exists, the roles panel is inert and reads: "Add your CV first. Fit scores
need something to compare against."
```

**Check before moving on:** the roles table is real `<table>` markup; row click and
keyboard Enter both navigate; nothing in the page imports from `fixtures.ts`.

---



## Prompt 3 — Fit detail and the evidence panel

The evidence panel is built here and reused in step 4. Build it as a standalone shared
component now or you will end up with two divergent copies.

```text
Continue the existing project. Do not restyle or rewrite anything from earlier steps.
Data only through src/api/client.ts. Semantic tokens only, no hex.

Build the /roles/:id route and one shared evidence panel component.

EVIDENCE PANEL — build this first, at src/components/EvidencePanel.tsx
It takes a title, a status and an Evidence object as props. It will be used by the
requirement table in this step and by chat citation chips in the next one, so it must
know nothing about either.
Right-hand panel 420px on desktop, bottom sheet below 768px.
Shows the requirement or claim, the status, then the supporting CV text: the full
surrounding paragraph in mono, with the highlight span marked using a background token
and a left rule. Page number shown.
Rendered as escaped text. Never dangerouslySetInnerHTML.
On open, focus moves to the panel heading. Escape closes and returns focus to the
element that opened it. Focus is trapped while open.

FIT DETAIL PAGE
Sticky header: back link to Workspace, role title, company, score in mono.

Breakdown block: three rows from getFitBreakdown — must-have coverage, desirable
coverage, recency. Each row shows its label, its value, a 4px bar, and a chevron that
expands to list the requirements that produced it. Values come from the fixture; do not
compute them.

Requirement table grouped by status, Missing first, then Partial, then Met. Group
headers carry a count and collapse. Missing is expanded by default and the other two
are collapsed — the gaps are the point of this screen.
Columns: Requirement, Type, Status, Evidence.
  Type    small square-cornered outline badge, "Must" or "Desirable"
  Status  glyph plus word, always both: filled disc = met, half disc = partial,
          hollow ring = missing
  Evidence  first ~80 characters, muted, em dash when there is none
Row click opens the evidence panel. Rows with no evidence still open the panel and show
what is missing instead.

Below 768px the table becomes stacked cards, requirement text as the card title.

Loading skeleton, empty state and error state with retry for both the breakdown and the
table.
```

**Check before moving on:** `EvidencePanel` takes only props, no data fetching; Escape
returns focus to the row that opened it; the requirement table degrades to cards at
390px.

---



## Prompt 4 — Ask and Settings

```text
Continue the existing project. Do not restyle or rewrite anything from earlier steps.
Reuse the existing EvidencePanel component; do not create a second one. Data only
through src/api/client.ts. Semantic tokens only, no hex.

Build two routes.

/ask
Single centred column, maximum 760px. Message list above, composer pinned to the
bottom.
When there are no messages, three starter chips sit above the composer: "What am I
missing for this role?", "Compare my fit across all roles", "What will they probe in
interview?".
Assistant answers render token by token with a block caret and a Stop button while
streaming.
Under each answer, a row of citation chips labelled by source, for example "CV p.2" or
"Senior Data Engineer — Northwind". Clicking a chip opens the existing EvidencePanel
with that citation's evidence.
Answer footer in mono at 11px, muted: model name then provider name.
An answer with kind 'insufficient' uses the same bubble with a 2px neutral left rule, a
small label "Not enough evidence", the explanation in ordinary prose, and one suggested
next step. No red, no warning triangle, no error styling. It must read as a deliberate
answer, not a failure.

/settings
Single column, maximum 720px. Two independent selectors: "Answer model" and "Index
model". Each is a radio list of provider cards, not a dropdown, so every reason stays
on screen.
Provider card: name, model select, local/hosted badge reusing the shell badge
component, and a status line.
Unavailable providers are shown, never hidden. The radio is disabled, the reason is
normal-weight body text rather than greyed out, and it is wired to the radio with
aria-describedby.
Choosing a hosted provider opens an AlertDialog before anything is applied:
  Title: "Send your documents to Anthropic?"
  Body:  "Your CV and job descriptions will be sent to Anthropic to generate answers.
          They leave this machine. This is a normal way to run the tool. Choose it only
          if you are comfortable with that."
  Buttons: "Cancel" and "Use Anthropic"
Neutral styling, not destructive red. Substitute the provider name as appropriate.
Cancelling leaves the previous choice in place. Only the confirm button calls
setProviderChoice, and the shell badge updates from that.
Never render an API key field, masked or otherwise.
```

**Check before moving on:** only one `EvidencePanel` file exists; cancelling the egress
dialog leaves the old provider selected; the insufficient-evidence answer uses no red.

---



## Prompt 5 — State gallery and audit

```text
Continue the existing project. Two tasks.

1. Build /dev/states
A plain vertical list rendering every presentational component in every state by
passing props directly. No data fetching on this route. Each entry has a heading.
  CV card: empty, parsing, parsed, error
  Roles table: loading, empty, error, populated
  Roles stacked cards: populated
  Requirement table: all three status groups, and the mobile card variant
  Evidence panel: matched requirement, missing requirement
  Chat: empty with starter chips, streaming, answered with citations, insufficient
        evidence
  Provider cards: available, selected, and one for each unavailable reason
  Egress dialog: open
  Provider badge: local and hosted
This route exists so every state can be reviewed and screenshotted without editing
code. If any component cannot be rendered here from props alone, refactor it so it can.

2. Audit the whole project and fix what fails
  - No file outside src/api imports from fixtures.ts
  - No `any`, no ts-ignore; tsc passes clean
  - No hex colours, no inline styles, no bg-gray / text-white style classes
  - Exactly one EvidencePanel component
  - Every interactive element reachable by keyboard with a visible 2px accent focus
    ring; no outline: none anywhere
  - Every status conveyed by text and glyph, not colour alone
  - Unused dependencies removed from package.json
  - Layout correct at 390px on every route
Report what you changed.
```

**Check:** `/dev/states` renders every entry listed; `tsc` is clean; `package.json` has
nothing unused.

---



## After the last prompt

Export to GitHub, then port into `frontend/` against the handover checklist in the
frontend brief. The port is mostly one file: `src/api/client.ts` becomes the real typed
HTTP client and everything above it stays as built. Screenshots come from
`/dev/states` plus the live app.