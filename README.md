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

### Fixes itself
Run `/self-improve` when it falls short. A new zero opens in its own source with your session transcript, finds the cause, and proposes fixes. Your conversation reloads with them in place.

### Any model, switch anytime
- `/model` shows each provider's newest model per family. The full list is one step away.
- Switch mid-session. The conversation carries over.
- Add another provider by asking zero. Any API compatible with OpenAI Responses or Anthropic Messages works, such as [Venice](https://venice.ai).

### Approvals that stay out of your way
- `auto-review`: a cheap reviewer approves routine commands. Needs an OpenAI key (Decisions API) or a `TYPESAFE_API_KEY` (Jev).
- `ask` and `auto-max` work with any provider.
- At a prompt, type a reason instead of "no" and the agent changes course.

### Steer it live
Type while it works; it reads your message before its next step. Thinking streams as it goes, so you can stop it early.

### Long sessions
Context is trimmed and summarized before the window fills. Every session is saved and resumable.

### Web search
Uses your provider's search (OpenAI or Anthropic) on its cheapest current model. For other providers, add a [Parallel](https://parallel.ai) key and ask zero to use it.

### Your rules
zero reads `~/.zero/AGENTS.md` every session, plus the project's `AGENTS.md` or `CLAUDE.md`. Share one file across agents with a symlink:

```bash
ln -s ~/path/to/AGENTS.md ~/.zero/AGENTS.md
```

### Live prices
Models, prices, context sizes, and reasoning levels come from [models.dev](https://models.dev). Cached in `~/.zero/catalog.json`, refreshed at startup once a day.

**Tools:** `bash` · `job` · `read_file` · `edit_file` · `grep` · `web_search` · `web_fetch` · `todo`

## Commands

| Command | What it does |
| --- | --- |
| `/model [provider] [model]` | Pick a provider, model, and reasoning level. Tab completes; arrow keys pick. |
| `/reasoning [level]` | Set reasoning. Levels depend on the model. |
| `/mode [mode]` | Set approvals: `ask`, `auto-review`, `auto-max`. |
| `/new` | Start a new session. |
| `/resume` | Continue a saved session. |
| `/undo` | Undo the last turn's file edits. Repeat to go further back. |
| `/summarize` | Replace the conversation with a summary to free up context. |
| `/title <title>` | Rename the session. |
| `/self-improve <note>` | Have a new zero find and fix what went wrong here. |
| `/reload` | Restart zero to apply code changes, keeping the conversation. |

Ctrl+E opens the input in `$EDITOR`. End a line with `\` for a newline.

## Hacking on zero

Clone the repo and run `uv tool install --editable .`. Code edits apply after `/reload`. Run tests with `uv run pytest`. `/self-improve` needs this install.

- Add a tool: create `src/zero_harness/tools/<name>.py` with a `SCHEMA` and a `run()`, then add it to `TOOLS` in `tools/registry.py`.
- Add a provider: see the format at the top of `src/zero_harness/models/registry.py`.
- Add an API format (beyond OpenAI Responses and Anthropic Messages): add a module to `src/zero_harness/models/`.

## License

MIT
