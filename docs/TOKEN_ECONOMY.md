# Token Economy

This repo uses narrow CLIs to avoid two kinds of token cost:

1. MCP startup/schema cost: tool definitions and server instructions that are loaded before a tool is called.
2. Per-call output cost: raw payloads, page text, logs, JSON, screenshots, or thread dumps returned after a call.

The CLI output numbers below were measured locally on 2026-05-09 with `tokensx`, using a simple heuristic:

```text
estimated tokens = max(ceil(characters / 4), ceil(words * 1.3))
```

These are estimates, not billing-grade tokenizer counts. They are good enough for comparing payload size.

## Regenerate

```powershell
.\scripts\measure-token-economy.ps1
```

The script writes ignored benchmark files under `cache/token-benchmarks/` and prints a Markdown table using `tokensx`.

## Measured Output Savings

| Task | CLI output estimate | Raw / MCP-style payload estimate | Estimated output avoided | Reduction |
|---|---:|---:|---:|---:|
| `ytx transcript YHk45NEpspE --no-header` vs timestamped transcript segments | 9,705 | 12,868 | 3,163 | 25% |
| `searchx search "Python argparse documentation" --limit 3 --max-chars 1000` vs raw Exa search JSON | 1,845 | 46,430 | 44,585 | 96% |
| `docsx search "Python argparse documentation" --limit 3 --max-chars 1000` vs raw Exa search JSON | 1,845 | 46,431 | 44,586 | 96% |
| `docsx read https://docs.python.org/3/library/argparse.html --max-chars 1000` vs full extracted page | 636 | 42,137 | 41,501 | 98% |
| `refx search "Python argparse documentation" --max-chars 1000` vs raw Ref MCP tool result | 547 | 317 | None; CLI output is larger because it adds formatting and the cache path | Startup/schema savings only |
| `searchx fetch https://docs.python.org/3/library/argparse.html --max-chars 1000` vs raw Exa contents JSON | 650 | 20,729 | 20,079 | 97% |
| `redditx search "Claude Code" --subreddit ClaudeAI --limit 3 --max-chars 1000` vs raw Reddit JSON | 1,624 | 5,158 | 3,534 | 69% |
| `semgrepx scan . --config auto --limit 5` with no findings vs raw Semgrep JSON | 57 | 950 | 893 | 94% |
| `corosx status` | 170 | Not measured | Not measured | Not measured |
| `browserx links https://example.com --limit 10` | 25 | Not measured | Not measured | Not measured |

## MCP Startup Cost

The table above excludes the always-loaded MCP startup/schema cost. That cost is client-specific and should be measured with the agent client's context accounting, for example Claude Code's `/context`, with one MCP enabled and then disabled.

Practical estimate ranges:

| MCP counterpart | Startup/schema estimate | Notes |
|---|---:|---|
| `youtube-transcript` | 200-500 tokens | Small tool surface. Savings mostly come from not loading it in sessions that do not need transcripts. |
| `exa` | 500-1,200 tokens | Search/fetch definitions plus instructions. Big savings come from output caps and raw-cache behavior. |
| `ref` | 400-1,000 tokens | Similar to Exa, but docs pages can be very large unless capped. |
| `reddit` | 500-1,500 tokens | Thread payloads can be much larger than the tool schema. |
| `semgrep` | 500-1,500 tokens | Native Semgrep already emits large JSON; `semgrepx` keeps raw JSON cached locally. |
| `coros` | 2,000-5,000 tokens | Large tool surface: auth, cache, metrics, sleep, activities, workouts, planning. |
| `playwright` / browser MCP | 3,000-10,000+ tokens | Large interactive tool surface. Page snapshots and screenshots can dominate per-call cost. Keep MCP for exploratory browser work. |

## Interpretation

For a one-off call, use:

```text
MCP estimated cost = MCP startup/schema cost + MCP output cost
CLI estimated cost = CLI output cost
```

For repeated sessions where an MCP is loaded but rarely used, the startup/schema cost matters more than any single call. That is the main reason these CLIs exist: keep routine read-heavy integrations available from the terminal without carrying their tool definitions in every agent session.

The strongest output-reduction wins so far are `searchx`, `docsx`, `redditx`, and `semgrepx`, because they cap output and cache raw data. `refx` is different: Ref's search result is already compact, so the main win is avoiding Ref MCP startup/schema cost in agent sessions. `ytx` still returns a large transcript, so its main win is avoiding MCP startup cost and making transcript capture scriptable. `browserx` is intentionally partial: use CLI commands for deterministic links/screenshots, but keep browser MCPs for live inspection and clicking.
