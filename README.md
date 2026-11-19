# zero-harness

A minimal terminal agent harness for OpenAI, Anthropic, and any other model provider.
Designed for efficiency and reliability. Under 3,000 lines of Python, 8 tools, and a ~700-word system prompt. Unnecessary features? **ZERO**. **It can also fix itself.**

![zero fixing a failing test](assets/demo.gif)

## Setup

Needs macOS, [uv](https://docs.astral.sh/uv/getting-started/installation/), and an [OpenAI](https://platform.openai.com/api-keys) or [Anthropic](https://platform.claude.com/settings/keys) API key.\*

```bash
uv tool install https://github.com/devinjones812/zero-harness/archive/main.zip
```

Run `zero`, pick a provider and model, and paste your key. It's stored locally in `~/.zero/.env`.

\*Other providers work too: ask zero to add one (any API compatible with OpenAI's Responses API, such as [Venice](https://venice.ai)), then pick it with `/model`.

---

*No uv? Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`, then open a new terminal.

---

## Features

- **Fixes itself.** When it falls short, with one command you can open a new zero in its own source code with a transcript of your session. That agent finds the cause, proposes fixes, and your conversation reloads with them in place.
- **Any model, switch anytime.** `/model` shows each provider's newest model of each family, with the full list one step away. Switch mid-session; the conversation carries over.
- **Approvals that stay out of your way.** In `auto-review` mode, a cheap reviewer approves routine commands: OpenAI Decisions with an OpenAI key, or Jev with a `TYPESAFE_API_KEY`. Without either, use `ask` or `auto-max`. At a prompt, type a reason instead of "no" and the agent changes course.
- **Steer it live.** Type while it works and it reads your message before its next step. Its thinking streams as it goes, so you can stop it early.
- **Long sessions.** It trims and summarizes context before the window fills. Every session is saved and resumable.
- **Web search** with your model's provider: OpenAI or Anthropic search, run on their cheapest current model. For other providers, or if you prefer it, add a [Parallel](https://parallel.ai) key and ask zero to use it.
- **Your rules.** zero reads `~/.zero/AGENTS.md` in every session, plus the project's `AGENTS.md` or `CLAUDE.md`. To share one file with other agents, symlink it: `ln -s ~/path/to/AGENTS.md ~/.zero/AGENTS.md`.
- **Live prices.** Model lists, prices, context sizes, and reasoning levels come from [models.dev](https://models.dev), cached in `~/.zero/catalog.json` and refreshed at startup once a day.

Tools: `bash`, `job`, `read_file`, `edit_file`, `grep`, `web_search`, `web_fetch`, `todo`.

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
