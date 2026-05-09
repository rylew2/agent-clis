# Agent CLIs

Personal command-line tools for agent workflows. The goal is to replace narrow, read-heavy MCP usage with small CLIs that keep raw output out of the model context.

## Tools

| Command | Status | Purpose |
|---|---|---|
| `ytx` | working | Fetch YouTube transcripts and save wiki source notes. |
| `searchx` | planned | Compact web search/fetch wrapper. |
| `docsx` | planned | Documentation search/read wrapper. |
| `semgrepx` | planned | Semgrep wrapper that returns concise findings. |
| `redditx` | planned | Reddit search/thread reader with cached raw data. |
| `corosx` | planned | COROS cache/reporting CLI. |
| `browserx` | planned | Repeatable Playwright screenshot/smoke-test commands. |

See [ROADMAP.md](ROADMAP.md) for the build order.

## Run Without Installing

From this repo:

```powershell
$env:PYTHONPATH = ".\src"
python -m agent_clis.ytx transcript YHk45NEpspE --no-header
```

Or use the PowerShell launcher:

```powershell
.\bin\ytx.ps1 transcript YHk45NEpspE --no-header
```

## Install For Local Use

From this repo:

```powershell
python -m pip install -e .
```

Then run from any directory:

```powershell
ytx transcript YHk45NEpspE
```

## Design Rules

- Keep default output short and readable.
- Add `--json` or `--format json` for machine-readable output.
- Add `--limit`, `--since`, `--fields`, or equivalent controls before commands can produce large output.
- Cache raw responses locally when they are expensive, large, or rate-limited.
- Store secrets in environment variables or ignored local config, never in committed files.
- Build read-only commands first. Add write commands only with dry-run and explicit confirmation.
