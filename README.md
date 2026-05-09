# Agent CLIs

Personal command-line tools for agent workflows. The goal is to replace narrow, read-heavy MCP usage with small CLIs that keep raw output out of the model context.

## Tools

| Command | Status | Replaces / reduces | Purpose |
|---|---|---|---|
| `ytx` | working | `youtube-transcript` MCP | Fetch YouTube transcripts and save wiki source notes. |
| `searchx` | working, requires `EXA_API_KEY` | `exa` MCP | Compact Exa web search/fetch wrapper. |
| `docsx` | working, search requires `EXA_API_KEY` | `ref` MCP for docs lookup; Exa-backed in this repo | Documentation search/read wrapper. |
| `semgrepx` | working, requires Semgrep CLI | `semgrep` MCP | Semgrep wrapper that returns concise findings. |
| `redditx` | working, public Reddit JSON | `reddit` MCP | Reddit search/thread reader with cached raw data. |
| `corosx` | working, requires local COROS cache | `coros` MCP for read-only reports | COROS cache/reporting CLI. |
| `browserx` | partial | `playwright` / browser MCP for deterministic checks only | Link extraction and Playwright screenshots. |
| `tokensx` | working | No MCP replacement; measurement helper | Approximate token counts for saved outputs. |

See [ROADMAP.md](ROADMAP.md) for the build order.

More detail:

- [Install guide](docs/INSTALL.md)
- [Secrets guide](docs/SECRETS.md)
- [Tool ideas](docs/TOOLS.md)
- [Token economy estimates](docs/TOKEN_ECONOMY.md)

## Token Savings Snapshot

Measured on 2026-05-09 with `tokensx`. These are approximate output-token counts, not billing-grade tokenizer numbers, and they exclude MCP startup/schema overhead.

| CLI task | Compared against | CLI output | Counterpart payload | Output reduction |
|---|---|---:|---:|---:|
| `searchx search` for Python argparse docs | Raw Exa search JSON, similar to what an Exa MCP call may expose if not compacted | 1,845 | 46,430 | 96% |
| `docsx read` Python argparse page | Full extracted documentation page text | 636 | 42,137 | 98% |
| `searchx fetch` Python argparse page | Raw Exa contents JSON, similar to an Exa fetch MCP payload if not compacted | 650 | 20,729 | 97% |
| `redditx search` Claude Code posts | Raw Reddit public JSON search response | 1,624 | 5,158 | 69% |
| `semgrepx scan` with no findings | Raw Semgrep JSON output | 57 | 950 | 94% |
| `ytx transcript` | Timestamped YouTube transcript segments | 9,705 | 12,868 | 25% |

See [docs/TOKEN_ECONOMY.md](docs/TOKEN_ECONOMY.md) for the full methodology and MCP startup-cost estimates.

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

No secrets are required for `ytx`, `semgrepx`, `redditx`, or most `browserx` commands. `redditx` currently uses public Reddit JSON endpoints, not OAuth. `searchx` and `docsx search` read `EXA_API_KEY`; see [docs/SECRETS.md](docs/SECRETS.md). `.env` is ignored, and `.env.example` contains only placeholders.

## Design Rules

- Keep default output short and readable.
- Add `--json` or `--format json` for machine-readable output.
- Add `--limit`, `--since`, `--fields`, or equivalent controls before commands can produce large output.
- Cache raw responses locally when they are expensive, large, or rate-limited.
- Store secrets in environment variables or ignored local config, never in committed files.
- Build read-only commands first. Add write commands only with dry-run and explicit confirmation.
