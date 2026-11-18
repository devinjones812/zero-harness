# zero-harness

A minimal terminal coding agent on the OpenAI Responses API.

![zero at startup](docs/screenshot.png)

## Setup

Needs macOS, [uv](https://docs.astral.sh/uv/), and [ripgrep](https://github.com/BurntSushi/ripgrep).

```bash
uv tool install git+https://github.com/devinjones812/zero-harness
```

Put your keys in `~/.zero/.env` (see [`.env.example`](.env.example)). Only `OPENAI_API_KEY` is required.

## Use

Run `zero`, or `zero "message"`. `zero -r` resumes a session. Type `/` for commands. Ctrl+E opens the input in `$EDITOR`.

`/mode` sets approvals: `ask` asks every time, `auto` (default) lets a classifier approve routine commands, `auto-max` asks only for known destructive commands.

## Self-improvement

When zero falls short, type `/self-improve`. It commits a checkpoint, then opens a new zero in its own source code with a transcript of your session. That agent proposes fixes, and makes them after you approve. Type `/reload` in the first window to continue with the fixes. Needs an editable install: clone the repo and run `uv tool install --editable .`.

## License

MIT
