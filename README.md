# zero-harness

A minimal terminal agent harness I built around OpenAI models. 
Designed for efficiency and reliability. <2,000 lines of Python, 8 tools, and a ~700-word system prompt. Unnecessary features? **ZERO**. **It can also fix itself.**

![zero fixing a failing test](assets/demo.gif)

## Setup

Needs macOS, [uv](https://docs.astral.sh/uv/getting-started/installation/), and an [OpenAI API key](https://platform.openai.com/api-keys).

```bash
uv tool install https://github.com/devinjones812/zero-harness/archive/main.zip
```

Run `zero` and paste your API key. It's stored locally in `~/.zero/.env`.

---

*No uv? Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`, then open a new terminal.

---

## Features

- **Fixes itself.** When it falls short, with one command you can open a new zero in its own source code with a transcript of your session. That agent finds the cause, proposes fixes, and your conversation reloads with them in place.
- **Approvals that stay out of your way.** In `auto` mode, OpenAI or Jev reviews routine commands. If the review fails, zero asks you. At a prompt, type a reason instead of "no" and the agent changes course.
- **Steer it live.** Type while it works and it reads your message before its next step. Its thinking streams as it goes, so you can stop it early.
- **Long sessions.** It trims and summarizes context before the window fills. Every session is saved and resumable.
- **Optional providers.** Add them anytime. For Parallel web search, set `"search_provider": "parallel"` in `~/.zero/config.json` and add `PARALLEL_API_KEY` to `~/.zero/.env`.

Tools: `bash`, `job`, `read_file`, `edit_file`, `grep`, `todo`, and one search/fetch pair from the configured provider.

## Commands

| Command | What it does |
| --- | --- |
| `/model` | Pick a model, then its reasoning effort. |
| `/effort <level>` | Set reasoning effort: `low`, `medium`, `high`, `xhigh`, `max`. |
| `/mode <mode>` | Set approvals: `ask`, `auto`, `auto-max`. |
| `/new` | Start a new session. |
| `/resume` | Continue a saved session. |
| `/undo` | Undo the last turn's file edits. Repeat to go further back. |
| `/summarize` | Replace the conversation with a summary to free up context. |
| `/title <title>` | Rename the session. |
| `/self-improve <note>` | Have a new zero find and fix what went wrong here. |
| `/reload` | Restart zero to apply code changes, keeping the conversation. |

Ctrl+E opens the input in `$EDITOR`. End a line with `\` for a newline.

## Hacking on zero

Clone the repo and run `uv tool install --editable .`. Code edits apply after `/reload`. `/self-improve` needs this install. To add a tool, create `src/zero_harness/tools/<name>.py` with a `SCHEMA` and a `run()`, then add it to `TOOLS` in `tools/registry.py`.

## License

MIT
