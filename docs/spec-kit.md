# GitHub Spec Kit in this existing project

Adopted 2026-10-02 from GitHub Spec Kit **v1.0.13** (upstream commit
`f1a548a39dba4e5e8600de1d2e0d3ff0c468d2a9`). This is a development workflow;
it adds no dependency to the running career assistant, container or model pipeline.

The official [existing-project guide](https://github.github.io/spec-kit/guides/existing-projects.html)
recommends initialization in place, capturing existing guardrails and starting with
one bounded change. We followed that approach. Application source, database,
provider settings and original uploads are untouched by this adoption.

## What is already included

- `.agents/skills/speckit-*/SKILL.md`: ten official Codex skills.
- `.specify/scripts/`, `templates/` and `workflows/`: pinned upstream infrastructure.
- `.specify/memory/constitution.md`: constitution **1.0.0**, derived from the accepted
  current architecture, evidence/privacy boundaries and human delivery instructions.
- `.specify/integration.json` and manifests: integration/version and managed-file hashes.
- `.specify/UPSTREAM_LICENSE.txt`: upstream MIT license; the application license remains
  in the repository's root `LICENSE`.

No automatic Git extension is installed. The existing branch/commit policy remains
in AGENTS.md. Generated specs use a local feature pointer, which is ignored by Git;
feature directories are independent of the Git branch name.

## Your next steps

1. Open **career-intelligence-assistant** itself as the Codex project, rather than
   only its parent portfolio folder. The repository root on this machine is
   `/Users/mehmooa7/porfolio-development/career-intelligence-assistant`.
2. Start a new chat for that project so the repository-local skills are discovered.
   If the picker does not show `speckit-` skills, reopen the project/application.
3. Read the existing constitution. It is already populated; there is no need to
   regenerate the whole project's specification or run initialization again.
4. Pick one open PLAN/BACKLOG item and use the skills in chat. Codex uses
   `$speckit-<command>`; these are agent instructions, not terminal commands.
5. Inspect the generated spec and plan before moving to implementation. Keep changes
   incremental, update the existing docs and commit regularly.

The [official integration reference](https://github.github.io/spec-kit/reference/integrations.html)
documents Codex's `.agents/skills` layout and `$speckit-` spelling. Official
[OpenAI documentation](https://learn.chatgpt.com/docs/build-skills) explains that
repository skill discovery scans from the working directory up to the repository
root, rather than searching child projects. Skills normally refresh automatically;
restart Codex if the newly installed skills do not appear.

## Suggested first change

Update 2026-10-02: the human requested implementation of this slice while retaining
deferred checks. Its [spec, plan and tasks](../specs/001-synthetic-analysis-benchmark/spec.md)
now exist and `make benchmark` is implemented. Use the existing artifacts rather
than creating another spec for the same change. Tests/lint subsequently resumed
and pass; offline benchmark execution is recorded in Evaluation. Commands and scope are in
[Evaluation](evaluation.md#current-analysis-benchmark-plan-194).
The prompts below document how that bounded feature was chosen.

The first feature targeted PLAN 19.4's current-analysis measurement slice, building
on the implemented 19.2–19.3 work. Its planning prompt was:

```text
$speckit-specify Add a reproducible synthetic benchmark for the existing career
analysis under PLAN 19.4. Record cold/warm elapsed time, physical completion and
embedding API attempts, cache reuse and provider/model/prompt attribution. Reuse
the current chunk/search/judge pipeline and progress accounting. Preserve existing
public APIs and privacy controls. No pipeline rewrite, real CVs or hosted calls
by default. Keep tests, lint and benchmark execution pending until I request them.
```

The corresponding planning steps use these skills:

```text
$speckit-clarify
$speckit-plan Inspect the existing implementation and reuse its architecture.
$speckit-tasks Keep verification as a final pending phase under my current instruction.
$speckit-analyze
```

Those steps create/review planning artifacts. They do not establish a measured
performance result. When you are ready for implementation, use `$speckit-implement`
and then `$speckit-converge`; restate any current limits on execution. `converge`
may inspect/run verification, so do not invoke it as evidence of passing checks
while validation is still deferred. The human has since resumed lint, hermetic
and integration checks for PR #43; its bounded record is
[specs/005-pr43-ci-repair/](../specs/005-pr43-ci-repair/spec.md). Benchmark/browser
and broader release verification remain separate work.

`$speckit-constitution` is available for future governance amendments. The optional
checklist skill reviews specification quality. Issue creation through
`$speckit-taskstoissues` is separate work and requires an explicit request.

## Keep one roadmap

Root PLAN.md owns milestones and release gates; BACKLOG.md owns priority. A feature
`specs/<change>/spec.md` elaborates only its bounded change and links to the root item.
Its `plan.md` records implementation design; `tasks.md` records execution. Do not
copy the global backlog or existing application into every generated artifact.

Plans must inspect the real `backend/src/career_assistant/`, `backend/tests/` and
`frontend/src/` layout. Template examples for a new project, new framework, generic
`src/` folders or authentication are examples, not tasks for this established app.
Prefer an existing module, dependency or fixture over introducing another approach.

Completed feature directories are historical records of a change. Later changes
use a new linked feature; current behavior and architecture stay in the existing
product/API/architecture documentation. Measured numbers stay in docs/evaluation.md.

## Optional CLI setup and future upgrades

The project files and skills are committed. A permanent CLI installation is optional
for using those skills, but useful for integration management on your machine.
The adoption used an isolated, one-time `uvx` invocation rather than changing the
application's Python environment.

On this machine `uv` exists at `/Users/mehmooa7/.local/bin/uv` but was not on this
session's PATH. You can install the pinned management CLI once with:

```bash
/Users/mehmooa7/.local/bin/uv tool install specify-cli \
  --from git+https://github.com/github/spec-kit.git@v1.0.13
```

With `~/.local/bin` on your terminal PATH, inspect the installed integration from
the repository root:

```bash
specify integration status
```

For a deliberate future upgrade, first commit local changes and install the chosen
release of the CLI, then use the manifest-aware command:

```bash
specify integration upgrade codex
```

Review the generated diff and version before committing. Existing constitution
customizations are retained by integration upgrades. Avoid `init --force` as a
routine upgrade mechanism. See the official
[upgrade guide](https://github.github.io/spec-kit/upgrade.html).

To reproduce the initial scaffold in another existing checkout that has no Spec Kit
files, the pinned bootstrap command used here was:

```bash
uvx --from git+https://github.com/github/spec-kit.git@v1.0.13 specify init \
  --here --force --non-interactive --integration codex \
  --integration-options="--skills" --script sh --ignore-agent-tools
```

Run this from the application repository root after committing/backing up work.
A clone of this branch already has these files and needs no reinitialization.

## Verification state

The CLI initialization succeeded, the installed version is recorded as 1.0.13 and
the constitution resolver successfully loaded the upstream template. The new
constitution contains the project's existing rules. Discovery by a fresh Codex chat
still needs the project reload described above.

No application tests, lint, model benchmarks or migrations were run for the original
adoption, following the human's instruction. Verification subsequently resumed:
retirement acceptance (spec 009), provider/runtime acceptance (spec 010) and full
lint/hermetic checks pass. Benchmark/browser/security/startup and current model
quality gates remain separate in PLAN 19.4. Workflow adoption alone closes no gate.
