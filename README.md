# zero-harness

A minimal terminal agent harness designed for efficiency and reliability. Under 3,000 lines of Python, 8 tools, and a ~700-word system prompt. Unnecessary features? **ZERO**. **It can also fix itself.**

![zero fixing a failing test](assets/demo.gif)

## Setup

Needs macOS, [uv](https://docs.astral.sh/uv/getting-started/installation/), and an [OpenAI](https://platform.openai.com/api-keys) or [Anthropic](https://platform.claude.com/settings/keys) API key.

```bash
uv tool install https://github.com/devinjones812/zero-harness/archive/main.zip
```

Run `zero`, pick a provider and model, and paste your key. It's stored locally in `~/.zero/.env`.

---

*No uv? Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`, then open a new terminal.

---

## Features

- **Self-repair.** `/self-improve` opens a new zero in its own source with your transcript. It finds the cause, fixes it, and reloads your session.
- **Any model.** `/model` lists each provider's newest models. Switch mid-session without losing context. Ask zero to add any OpenAI- or Anthropic-compatible provider, such as [Venice](https://venice.ai).
- **Light approvals.** `auto-review` lets a cheap reviewer approve routine commands (needs an OpenAI or `TYPESAFE_API_KEY` key). To deny, type a reason and the agent changes course.
- **Live steering.** Type while it works. It reads your message before its next step.
- **Long sessions.** Context is summarized before the window fills. Every session is saved and resumable.
- **Web search.** Uses OpenAI or Anthropic search, or [Parallel](https://parallel.ai) for other providers.
- **Your rules.** Reads `~/.zero/AGENTS.md`, which starts as zero's default rules: concise, direct, no flattery. Edit or replace it, or symlink your own to share with other agents. Also reads the project's `AGENTS.md` or `CLAUDE.md`.
- **Skills.** Put a skill in `~/.zero/skills/<name>/SKILL.md` (or symlink one). For browser use, install [browser-harness](https://github.com/browser-use/browser-harness) and link its skill; zero then drives your real Chrome, so `auto-review` asks first.
- **Live prices.** Models, prices, and context sizes come from [models.dev](https://models.dev), refreshed daily.

**Tools:** `bash` | `job` | `read_file` | `edit_file` | `grep` | `web_search` | `web_fetch` | `todo` | `agent`

## Subagents

zero can hand a task to a subagent: a separate model run that gets only a brief and returns only its answer. This keeps zero's own context small and lets work run in parallel. Ask for subagents, or zero uses them when a task fits.

- **Read-only by default.** Subagents search, read files, and use the web. They never need approval or conflict.
- **Editing subagents.** For changes, zero can give a subagent its own copy of the project (a git worktree, with your uncommitted changes and your `.venv` or `node_modules` linked in). It edits and runs tests there. When it finishes, zero merges its changes into your files with one approval, under your approval mode. `/undo` reverts them. If a file changed in your copy too, overlapping edits go back to zero to resolve. Needs a git repo.
- **Parallel.** Up to 4 at once, each with its own one-line status.
- **Any model.** Each subagent runs on one of:
  - your current model (the default)
  - `smart`: for hard, narrow problems, such as one failing test
  - `fast`: for simple searches
  - any model you name, such as "use openai/gpt-6.2-astra", even from another provider

  zero asks you to pick the `smart` and `fast` models the first time it needs one, and saves your choice. Ask zero to change them.
- **Costs** count toward the session total in the status line.

## Commands

| Command | What it does |
| --- | --- |
| `/model [provider] [model]` | Pick a provider, model, and reasoning level. Tab completes; arrow keys pick. |
| `/reasoning [level]` | Set reasoning. Levels depend on the model. |
| `/summarize` | Replace the conversation with a summary to free up context. |
| `/mode [mode]` | Set approvals: `ask`, `auto-review`, `auto-max`. |
| `/resume` | Continue a saved session. |
| `/self-improve <note>` | Have a new zero find and fix what went wrong here. |
| `/reload` | Restart zero to apply code changes, keeping the conversation. |
| `/new` | Start a new session. |
| `/undo` | Undo the last turn's file edits. Repeat to go further back. |
| `/title <title>` | Rename the session. |
| `/history` | Show everything printed this session in a pager. `q` returns. |

Ctrl+E opens the input in `$EDITOR`. End a line with `\` for a newline.

## Hacking on zero

Clone the repo and run `uv tool install --editable .`. Code edits apply after `/reload`. Run tests with `uv run pytest`. `/self-improve` needs this install.

- Add a tool: create `src/zero_harness/tools/<name>.py` with a `SCHEMA` and a `run()`, then add it to `TOOLS` in `tools/registry.py`.
- Add a provider: see the format at the top of `src/zero_harness/models/registry.py`.
- Add an API format (beyond OpenAI Responses and Anthropic Messages): add a module to `src/zero_harness/models/`.

## License

MIT
