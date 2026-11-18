# zero-harness

A minimal terminal coding agent on the OpenAI Responses API.

![zero at startup](docs/screenshot.png)

## Setup

Needs macOS, [uv](https://docs.astral.sh/uv/), and [ripgrep](https://github.com/BurntSushi/ripgrep) (`brew install ripgrep`).

Install. This adds `zero` to your PATH:

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

To hack on it, clone the repo and run `uv tool install --editable .` instead. Code edits then apply after `/reload`.

## Use

Run `zero` in any directory, or `zero "message"` to send a first message. `zero -r` resumes a session. Type while the agent works; it reads your message before its next step. Drag in an image to attach it. Ctrl+C clears the input, stops a turn, or quits. Ctrl+E opens the input in `$EDITOR` for long prompts; save and quit to bring the text back.

Auto mode (on by default) lets Jev approve routine shell commands. Risky ones still ask. At `allow? [y/N]`, type anything other than y or n to deny and tell the agent why. Temporary files go in a scratch folder that zero deletes on exit.

Commands: `/new`, `/resume`, `/model`, `/effort`, `/auto`, `/undo`, `/summarize`, `/title`, `/self-improve`, `/reload`.

What's planned, and what we left out on purpose: [docs/roadmap.md](docs/roadmap.md).

## Self-improvement

When zero falls short mid-conversation, type `/self-improve`, with an optional note such as `/self-improve the approval prompt lost my reply`.

1. zero commits its own repo as a checkpoint.
2. It saves what you saw on screen and the full session to `~/.zero/self-improve/<time>/`.
3. It opens a new Terminal window with a zero agent in its own source code. That agent reads the transcript, finds the causes in the code, and proposes fixes.
4. You approve or comment. The agent makes the fixes.
5. Type `/reload` in your first window. zero restarts with the fixes, and the conversation continues where it was.

To undo the fixes, run `git reset --hard <checkpoint>`; the agent gives you the hash. This needs a git clone of zero installed with `uv tool install --editable .`. The new-window step needs macOS Terminal; elsewhere, zero prints the command to run.

## Context

- Your global rules (`~/.cursor/rules/agents.mdc`) and the project's `AGENTS.md` (or `CLAUDE.md`) go into the system prompt, with the git branch, status, and recent commits at startup.
- Skills: add `~/.zero/skills/<name>/SKILL.md` with `name` and `description` frontmatter. The prompt lists each skill; the agent reads the full file only when a task needs it.

## Add a tool

1. Create `src/zero_harness/tools/<name>.py` with a `SCHEMA` dict and a `run(...)` function.
2. Add it to `TOOLS` in `src/zero_harness/tools/registry.py`.

## License

MIT
