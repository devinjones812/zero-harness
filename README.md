# zero-harness

A minimal terminal coding agent on the OpenAI Responses API.

![zero at startup](docs/screenshot.png)

## Setup

Needs macOS, [uv](https://docs.astral.sh/uv/), and [ripgrep](https://github.com/BurntSushi/ripgrep) (`brew install ripgrep`).

Install. This adds `zero` (and `zero-harness`) to your PATH:

```bash
uv tool install git+https://github.com/devinjones812/zero-harness
```

Put your keys in `~/.zero/.env` (see [`.env.example`](.env.example)):

```
OPENAI_API_KEY=...     # required
PARALLEL_API_KEY=...   # web_search and web_fetch
TYPESAFE_API_KEY=...   # auto mode
```

Update with `uv tool upgrade zero-harness`. Config, sessions, and skills live in `~/.zero/`, so updates keep them.

To hack on it, clone the repo and run `uv tool install --editable .` instead. Code edits then apply at once.

## Use

Run `zero` in any directory. Type while the agent works; it reads your message before its next step. Drag in an image to attach it. Ctrl+C clears the input, stops a turn, or quits.

Auto mode (on by default) lets Jev approve routine shell commands. Risky ones still ask.

Commands: `/new`, `/resume`, `/model`, `/effort`, `/auto`, `/undo`, `/summarize`, `/title`.

What's planned, and what we left out on purpose: [docs/roadmap.md](docs/roadmap.md).

## Context

- Your global rules (`~/.cursor/rules/agents.mdc`) and the project's `AGENTS.md` (or `CLAUDE.md`) go into the system prompt, with the git branch, status, and recent commits at startup.
- Skills: add `~/.zero/skills/<name>/SKILL.md` with `name` and `description` frontmatter. The prompt lists each skill; the agent reads the full file only when a task needs it.

## Add a tool

1. Create `src/zero_harness/tools/<name>.py` with a `SCHEMA` dict and a `run(...)` function.
2. Add it to `TOOLS` in `src/zero_harness/tools/registry.py`.

## License

MIT
