# MCP server

`career-assistant-mcp` lets an MCP client on the same machine, such as Claude
Desktop or Cursor, read one workspace through the tools the in-app Ask agent
uses. It does not change the web app's analysis, scores or answers. It is a second
way in, for another agent.

- **Read-only.** Eight tools, each marked `readOnlyHint`. Nothing can add a role,
  upload a document or generate a letter over MCP.
- **Local only.** stdio transport: the client starts the process. There is no network
  listener.
- **Off by default.** It serves only when `config/app.env` says so. The client's
  environment cannot switch it on.
- **Protocol.** It uses the official Python SDK, `mcp` 2.2, which speaks the
  2026-07-28 specification and still accepts clients on the 2025-11-25 handshake.

## Where the results go

Every result contains text from your CV, cover letters or job descriptions. Once the
client has it, the client and the model it uses decide where it goes. If that model
is hosted, the text leaves your machine, and this application's egress gate cannot
stop it: the gate governs the models this application calls, not another
application's. Every tool description, every result (`leftMachine: "decided by the
MCP client"`) and the server's instructions say so.

## Turn it on

1. Install or update the backend dependencies from the repository root. This
   installs the SDK and the `career-assistant-mcp` command:

   ```bash
   make setup
   ```

2. Find the id of the workspace you use in the browser:

   ```bash
   backend/.venv/bin/career-assistant-mcp --list-workspaces
   ```

   It prints each workspace id, its role count and whether it has a CV.

3. Add both switches to `config/app.env`:

   ```bash
   MCP_ENABLED=true
   MCP_WORKSPACE_ID=<the id from step 2>
   ```

4. Point the client at the command. For Claude Desktop, add this to
   `claude_desktop_config.json`, using absolute paths:

   ```json
   {
     "mcpServers": {
       "career-intelligence": {
         "command": "/path/to/career-intelligence-assistant/backend/.venv/bin/career-assistant-mcp"
       }
     }
   }
   ```

   PostgreSQL must be running. The server reads `DATABASE_URL` the way the API does.

To turn it off, set `MCP_ENABLED=false` or remove the entry from the client. Without
both switches the command prints the reason to stderr and exits with status 2.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `list_roles` | — | Analysed roles with band and score |
| `search_evidence` | `query`, `sources`, `role_id`, `k` | Verbatim chunks with ids, ranked |
| `get_role_analysis` | `role_id` | Each requirement with must-have and status |
| `explain_requirement` | `requirement_id` | Status and the verbatim quotes behind it |
| `get_gap_plan` | `role_id` | Gaps ordered by score impact |
| `compare_roles` | `role_id_a`, `role_id_b` | Shared requirements, those unique to each, the differentiator |
| `skill_experience` | `term` | Chunks naming the skill; `years` is null |
| `get_chunk` | `chunk_id` | One chunk's verbatim text and source |

Each tool publishes its input and output schemas, and every result is structured and
matches its schema. An unknown role or chunk, or input that fails validation, is an
error result that carries only an error code.

## What it does not do yet

- `search_evidence` ranks the workspace's spans by the words they share with the
  query. It does not call `hybrid_search()`, so it finds no synonyms and does not
  rank by meaning.
- `skill_experience` returns no years, because the knowledge graph is not wired to
  the tools yet.
- Roles analysed on pipeline v2 come back with their band and score, but with no
  requirements, because the tools still read the v1 analysis. Pipeline v1 is the
  default.
- Only roles whose analysis is ready are listed.
- Streamable HTTP and write tools are out of scope. Both need authentication, and
  the specification defines that with OAuth ([ADR 015](adr/015-agents-and-mcp-over-one-tool-registry.md)).
