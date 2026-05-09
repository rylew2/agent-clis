# Tool Ideas

## Good CLI Candidates

These are good fits because they are read-heavy, can cache raw output, and can return concise summaries to the agent.

| Tool | Why it fits |
|---|---|
| `ytx` | No auth, narrow transcript fetch, immediate replacement for YouTube transcript MCP. |
| `searchx` | Search/fetch output can be capped and cached before the model sees it. |
| `docsx` | Documentation search needs exact URLs and concise excerpts, not a full MCP server in every session. |
| `semgrepx` | Semgrep is already CLI-native; wrapper can summarize findings. |
| `redditx` | Threads can be huge; CLI can cache raw JSON and print top comments only. |
| `corosx` | Existing local cache can support reports without live API calls. |
| `browserx` | Deterministic screenshots/smoke checks can be scripted. |

## Keep MCP For Now

- Exploratory browser control.
- Live UI state inspection.
- Write-heavy workflows until CLI dry-run, confirmation, and audit logging exist.
- Multi-tool platforms where discovery is the core value.
