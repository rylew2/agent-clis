# Roadmap

Build order is based on context savings, implementation risk, and how often the workflow appears in the research wiki.

## 1. `ytx` - YouTube Transcripts

Status: working.

Replaces routine use of the `youtube-transcript` MCP for read-only transcript capture.

Commands:

```powershell
ytx transcript <url-or-video-id>
ytx transcript <url-or-video-id> --format json
ytx save-source <url-or-video-id> --title "..." -o path/to/source.md
```

Next improvements:

- Add `--summary` only after choosing a non-Anthropic summarizer or local summarization path.
- Add optional source filename helper for the research wiki.

## 2. `searchx` - Web Search / Fetch

Status: working v1. Requires `EXA_API_KEY`.

Goal: reduce routine Exa MCP usage.

Initial commands:

```powershell
searchx search "query" --limit 5
searchx fetch "https://example.com" --max-chars 4000
```

Requirements:

- Read API key from `EXA_API_KEY`.
- Return compact Markdown by default.
- Store raw responses under ignored `cache/searchx/`.
- Never print full page text unless `--full` is passed.

## 3. `docsx` - Documentation Lookup

Status: working v1. `read` needs no key; `search` uses Exa and requires `EXA_API_KEY`.

Goal: reduce routine Ref MCP usage while preserving precise source attribution. Ref's public docs currently emphasize MCP setup rather than a documented REST search endpoint, so v1 avoids guessing an undocumented API.

Initial commands:

```powershell
docsx search "python fastapi dependency overrides" --limit 5
docsx read "<exact-doc-url>" --max-chars 4000
```

Requirements:

- Prefer official docs when query includes a library/framework.
- Output URL, title, and concise excerpts.
- Keep exact fetched content in cache for repeat reads.

## 4. `semgrepx` - Semgrep Wrapper

Status: working v1. Requires `semgrep` on PATH. Semgrep registry configs may report pseudonymous rule metrics to Semgrep, per Semgrep's own CLI behavior.

Goal: replace Semgrep MCP with native CLI use.

Initial commands:

```powershell
semgrepx scan --config auto
semgrepx scan --severity ERROR
```

Requirements:

- Call Semgrep CLI.
- Return only file, line, severity, rule, and message by default.
- Save full JSON to cache for later inspection.

## 5. `redditx` - Reddit Research

Status: working v1 using public Reddit JSON endpoints.

Goal: reduce Reddit MCP use for read-only research.

Initial commands:

```powershell
redditx search "query" --subreddit ClaudeAI --limit 10
redditx thread "<url>" --top 20
```

Requirements:

- Cache thread JSON.
- Print top comments and score metadata.
- Add hard output caps.

## 6. `corosx` - COROS Reports

Status: working v1 against the local SQLite cache at `~/.config/coros-mcp/cache.db`.

Goal: use the existing COROS local cache for routine reports without loading COROS MCP tools.

Initial commands:

```powershell
corosx daily --weeks 4
corosx sleep --weeks 4
corosx activities --from 20260501 --to 20260509
```

Requirements:

- Read from the existing SQLite cache where possible.
- Avoid live API calls unless `--sync` is passed.
- Keep workout creation/scheduling in MCP until write safety is designed.

## 7. `browserx` - Repeatable Browser Checks

Status: partial v1. `links` is built. `screenshot` shells to Playwright via `npx`. `console` remains MCP/manual for now.

Goal: reduce Playwright MCP usage for deterministic checks.

Initial commands:

```powershell
browserx screenshot http://localhost:3000 --out screenshot.png
browserx console http://localhost:3000
browserx links http://localhost:3000
```

Requirements:

- Keep MCP for exploratory UI control.
- Use CLI only for fixed smoke checks, screenshots, console errors, and link crawling.

## Later

- `googlex`: read-only Gmail/calendar summaries, with careful OAuth and PII handling.
- `slackx`: read-only channel/search summaries; writes require dry-run and confirmation.
- `atlassianx`: Jira/Confluence reads; writes require explicit audit logging.

## Packaging

The repo should stay clone-and-install simple:

```powershell
git clone <repo-url>
cd agent-clis
.\scripts\install.ps1
ytx --help
```

No API keys belong in Git. Add required future credentials as environment variables documented in `docs/SECRETS.md`.
