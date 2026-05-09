# Secrets

No API keys or tokens should be committed to this repo.

## Current State

`ytx`, `semgrepx`, `redditx`, `corosx`, and `browserx links` do not require API keys. `redditx` currently uses public Reddit JSON endpoints and does not use OAuth credentials. `browserx screenshot` requires local Playwright tooling, not an API key.

Future tools may need credentials:

| Tool | Secret source |
|---|---|
| `searchx` | `EXA_API_KEY` |
| `docsx search` | `EXA_API_KEY` |
| future `redditx` OAuth mode | Reddit OAuth client ID/secret |
| `googlex` | Google OAuth/application credentials |
| `slackx` | Slack bot token |
| `atlassianx` | Atlassian API token |

## Setup Pattern

Use environment variables for global CLI use:

```powershell
[Environment]::SetEnvironmentVariable("EXA_API_KEY", "your-key", "User")
```

Open a new terminal after setting a user environment variable.

For file-based local setup, copy `.env.example` to `.env` and fill values. `.env` is ignored by Git. The CLIs load `.env` from this repo, from the current directory tree, or from `%USERPROFILE%\.config\agent-clis\.env`; real environment variables win over `.env` values.

## Before Committing

Run:

```powershell
rg -n "api[_-]?key|token|secret|password|sk-|ghp_|xox|AIza" .
git status --short
```

Only placeholder names like `EXA_API_KEY` should appear.
