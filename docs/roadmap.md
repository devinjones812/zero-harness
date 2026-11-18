# Roadmap

zero stays small: a feature goes in when real use needs it.

## Later: non-interactive mode

`zero -p "prompt"` would run one prompt, print the result, and exit. Claude Code (`-p`), Codex (`exec`), and Hermes have it.

Why we'd use it:

- Scripts and CI: for example, "fix the lint errors" as a pipeline step.
- Git hooks: review or summarize a diff before a commit.
- Pipes: `git diff | zero -p "write a commit message"`.

What it needs: plain output without the prompt UI, a rule for approvals when no one can answer (deny risky commands), and an exit code for success or failure.

## Not built: memory

Hermes and Claude Code can save facts across sessions on their own. zero does not, on purpose:

- `AGENTS.md` already does this job, and you edit it on purpose. To make zero remember something, tell it "add this to AGENTS.md".
- Automatic memory saves trivial or wrong facts, the facts go stale, and you rarely check what it saved.
- Every saved fact goes into every model call, so cost and noise grow over time.

## Not built until we need it

Each of these adds code to maintain. We'll add one when a real task needs it:

- MCP servers: when we need an external tool such as GitHub, Linear, or a database.
- Subagents: when tasks need parallel work or a separate context for large searches.
- `@file` references: when the extra `read_file` round becomes a real cost.
- Search across sessions: when `/resume` by title is not enough.
- Hooks: when we need custom code before or after tool calls.
- Sandboxed execution (Docker, SSH): when we run untrusted code or work on remote machines.
- Other model providers: when we want a model that isn't on OpenAI.
- `AGENTS.md` in subfolders: when we work in a large repo with rules for each folder.
