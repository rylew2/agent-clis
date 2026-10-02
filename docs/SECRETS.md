# Secrets

No API keys or tokens should be committed to this repo.

## Current State

`ytx`, `semgrepx`, `redditx`, `corosx`, and `browserx links` do not require API keys. `redditx` reads public old.reddit.com pages (set `REDDIT_USER_AGENT` to override the request User-Agent); no OAuth credentials are used. `browserx screenshot` requires local Playwright tooling, not an API key.

Future tools may need credentials:

| Tool | Secret source |
|---|---|
| `searchx` | `EXA_API_KEY` |
| `docsx search` | `EXA_API_KEY` |
| `refx` | `REF_API_KEY` and available Ref credits |
| `figmax` | `FIGMA_TOKEN` (Figma personal access token) |
| `slackx` | `SLACK_TOKEN`, `SLACK_USER_TOKEN`, or `SLACK_BOT_TOKEN` |
| future `redditx` OAuth mode | Reddit OAuth client ID/secret |
| `googlex` | Google OAuth/application credentials |
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
export SLACK_USER_TOKEN="xoxp-your-token"
```

Create a Slack app at <https://api.slack.com/apps?new_app=1>. For read-only message/thread lookup, install it with whichever history scopes match what you need to read: `channels:history`, `groups:history`, `im:history`, and/or `mpim:history`. Add `users:read` for `slackx --resolve-users`; add `files:read` if file metadata matters.

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
