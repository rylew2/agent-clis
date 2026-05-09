# Secrets

No API keys or tokens should be committed to this repo.

## Current State

`ytx`, `semgrepx`, `redditx`, `corosx`, and `browserx links` do not require API keys. `redditx` currently uses public Reddit JSON endpoints and does not use OAuth credentials. `browserx screenshot` requires local Playwright tooling, not an API key.

Future tools may need credentials:

| Tool | Secret source |
|---|---|
| `searchx` | `EXA_API_KEY` |
| `docsx search` | `EXA_API_KEY` |
| `refx` | `REF_API_KEY` and available Ref credits |
| future `redditx` OAuth mode | Reddit OAuth client ID/secret |
| `googlex` | Google OAuth/application credentials |
| `slackx` | Slack bot token |
| `atlassianx` | Atlassian API token |

## Setup Pattern

Use environment variables for global CLI use.

Windows PowerShell:

```powershell
[Environment]::SetEnvironmentVariable("EXA_API_KEY", "your-key", "User")
[Environment]::SetEnvironmentVariable("REF_API_KEY", "your-key", "User")
```

macOS/Linux:

```sh
export EXA_API_KEY="your-key"
export REF_API_KEY="your-key"
```

Add those `export` lines to `~/.zshrc`, `~/.bashrc`, or another private shell startup file if you want them available in every terminal. Open a new terminal after setting persistent environment variables.

For file-based local setup, copy `.env.example` to `.env` and fill values. `.env` is ignored by Git. The CLIs load `.env` from this repo, from the current directory tree, or from `%USERPROFILE%\.config\agent-clis\.env` on Windows or `~/.config/agent-clis/.env` on macOS/Linux; real environment variables win over `.env` values.

## Before Committing

Run:

Windows:

```powershell
rg -n "api[_-]?key|token|secret|password|sk-|ghp_|xox|AIza" .
git status --short
```

macOS/Linux:

```sh
rg -n "api[_-]?key|token|secret|password|sk-|ghp_|xox|AIza" .
git status --short
```

Only placeholder names like `EXA_API_KEY` should appear.
