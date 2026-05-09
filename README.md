# Agent CLIs

Personal command-line tools for agent workflows. The goal is to replace narrow, read-heavy MCP usage with small CLIs that keep raw output out of the model context.

## Tools

| Command | Status | Purpose |
|---|---|---|
| `ytx` | working | Fetch YouTube transcripts and save wiki source notes. |
| `searchx` | working, requires `EXA_API_KEY` | Compact Exa web search/fetch wrapper. |
| `docsx` | working, search requires `EXA_API_KEY` | Documentation search/read wrapper. |
| `semgrepx` | working, requires Semgrep CLI | Semgrep wrapper that returns concise findings. |
| `redditx` | working, public Reddit JSON | Reddit search/thread reader with cached raw data. |
| `corosx` | working, requires local COROS cache | COROS cache/reporting CLI. |
| `browserx` | partial | Link extraction and Playwright screenshots. |

See [ROADMAP.md](ROADMAP.md) for the build order.

More detail:

- [Install guide](docs/INSTALL.md)
- [Secrets guide](docs/SECRETS.md)
- [Tool ideas](docs/TOOLS.md)

## Run Without Installing

From this repo:

```powershell
$env:PYTHONPATH = ".\src"
python -m agent_clis.ytx transcript YHk45NEpspE --no-header
python -m agent_clis.searchx search "agent cli tools" --limit 3
```

Or use the PowerShell launcher:

```powershell
.\bin\ytx.ps1 transcript YHk45NEpspE --no-header
```

## Install For Local Use

From this repo:

```powershell
.\scripts\install.ps1
```

Then run from any directory:

```powershell
ytx transcript YHk45NEpspE
searchx search "agent cli tools" --limit 3
```

The installer uses `pipx` if available, otherwise `pip --user -e .`. Open a new terminal after install if the command is not immediately found.

## Secrets

No secrets are required for `ytx`, `semgrepx`, `redditx`, or most `browserx` commands. `searchx` and `docsx search` read `EXA_API_KEY`; see [docs/SECRETS.md](docs/SECRETS.md). `.env` is ignored, and `.env.example` contains only placeholders.

## Design Rules

- Keep default output short and readable.
- Add `--json` or `--format json` for machine-readable output.
- Add `--limit`, `--since`, `--fields`, or equivalent controls before commands can produce large output.
- Cache raw responses locally when they are expensive, large, or rate-limited.
- Store secrets in environment variables or ignored local config, never in committed files.
- Build read-only commands first. Add write commands only with dry-run and explicit confirmation.
