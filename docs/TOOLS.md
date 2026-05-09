# Tool Ideas

## Good CLI Candidates

These are good fits because they are read-heavy, can cache raw output, and can return concise summaries to the agent.

| Tool | Why it fits |
|---|---|
| `ytx` | No auth, narrow transcript fetch, immediate replacement for YouTube transcript MCP. |
| `searchx` | Built. Search/fetch output can be capped and cached before the model sees it. |
| `docsx` | Built. Exa-backed documentation search/read utility for exact URLs and concise excerpts. |
| `refx` | Built. Ref-backed documentation lookup through Ref's MCP HTTP endpoint without loading Ref MCP into the agent session. |
| `semgrepx` | Built. Semgrep is already CLI-native; wrapper summarizes findings. |
| `redditx` | Built. Threads can be huge; CLI caches raw JSON and prints top comments only. |
| `corosx` | Built. Existing local cache can support reports without live API calls. |
| `browserx` | Partial. Deterministic links/screenshots are scripted; exploratory console work stays MCP for now. |
| `tokensx` | Built. Estimates token counts for saved outputs and supports token-economy benchmarks. |

## Keep MCP For Now

- Exploratory browser control.
- Live UI state inspection.
- Write-heavy workflows until CLI dry-run, confirmation, and audit logging exist.
- Multi-tool platforms where discovery is the core value.
