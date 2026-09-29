# ADR 015 — A bounded agent and an MCP server over one tool registry

- Status: proposed
- Date: 2026-09-29
- Plan: 18.11–18.12
- Design: [architecture-v2.md §10–§11](../architecture-v2.md#10-agentic-ask)

## Context

v1 answers questions through a regular-expression intent router. Gaps, fit,
comparison and interview preparation are phrased from the stored analysis; anything
else falls through to scoped span retrieval. A question that needs two steps —
"which of my projects best shows platform engineering, and for which roles does that
matter?" — cannot be answered, because nothing can decide to search and then look up
an analysis.

The same capabilities would be useful outside the web app. A candidate working in
Claude Desktop or Cursor could ask the same cited questions, if the
application exposed them over the Model Context Protocol.

`PLAN.md` fixes orchestration as "direct use cases" and rejects LangChain and
LlamaIndex for visible control flow. That reason still holds.

## Decision

1. **One tool registry.** Each tool is defined once in the application layer: name,
   model-facing description, Pydantic input and output schemas, a read-only flag and
   a handler that calls an existing use case. Every tool is workspace-scoped. All
   tools are read-only in v2.
2. **Agentic Ask.** The intent router stays as a fast path for the four stored-analysis
   intents. Open questions go to an agent loop written as a use case over a new
   `ToolCallingPort`, with hermetic, Ollama, OpenAI and Anthropic adapters that pass
   one contract suite. The loop is bounded by `AGENT_MAX_STEPS`,
   `AGENT_MAX_TOOL_CALLS` and `AGENT_MAX_INPUT_TOKENS`.
3. **The answer is structured and validated.** The final answer is JSON with text and
   citations. A citation is valid only if its chunk was returned by a tool call in the
   same turn and its quote appears verbatim in that chunk. The v1 groundedness check
   still runs. One repair; then an honest refusal that shows what was found.
4. **A provider without tool calling does not get the agent.** The capability
   descriptor decides, and open questions fall back to the v1 retrieval path. The
   application never branches on a provider's name.
5. **An MCP server is a second driving adapter.** It exposes the same registry as MCP
   tools with output schemas, structured results and `readOnlyHint`, targeting the
   2026-07-28 specification with 2025-11-25 compatibility. Transport is stdio only. The MCP SDK is imported only in
   the adapter, and the architecture guard enforces it.
6. **MCP is off by default.** `MCP_ENABLED` and the one workspace served are read
   from the server's configuration file, not from the environment the client
   launches the process with, because the client controls that environment. Every
   tool description and every tool result states that the MCP client decides where
   the results go, because this application's egress gate cannot govern another
   application's model, and a client need not fetch the server's instructions.
7. **Matching stays a workflow.** Its only agentic step is the judge's bounded
   request for one rewritten search ([ADR 014](014-model-judges-domain-aggregates.md)).

This amends the "Orchestration: direct use cases" row of `PLAN.md`'s fixed
technical direction: the agent loop is a direct use case, and still no agent
framework is used.

## Consequences

- Multi-step questions become answerable, with citations the server can check.
- The agent and external MCP clients get identical behaviour from identical tools;
  a tool fix lands in both.
- A new trust boundary: document text returned by a tool can try to steer the agent.
  Read-only, workspace-scoped tools, untrusted delimiting, budgets and an injection
  probe in the agent test suite bound it. `docs/threat-model.md` is updated when
  18.11 and 18.12 are built.
- A new egress path the application does not control: an MCP client's model sees
  every tool result. That is why the server is off by default and says so in every
  tool description.
- One more port and four more adapters to keep passing a contract suite.

## Rejected alternatives

- **LangGraph, LangChain or LlamaIndex for the agent.** Faster to start, but the step
  budget, the egress gate and the citation rule would sit inside someone else's
  control flow, and a hermetic fixture could not drive it as simply.
- **Replace the intent router entirely.** The four stored-analysis intents are cheap,
  deterministic and tested. An agent adds cost and variance there for no gain.
- **Write tools over MCP now.** Adding a role or generating a letter from an external
  client needs a mid-call confirmation. That waits until it can be tested.
- **Streamable HTTP transport now.** A network listener needs authentication, which
  the specification defines with OAuth, and that belongs with the authentication
  decision, not with this phase.
- **Separate tool definitions for the agent and for MCP.** Two definitions drift.
