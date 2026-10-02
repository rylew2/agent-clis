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

Create a Slack app at <https://api.slack.com/apps?new_app=1> and add **User Token Scopes** (search requires a user `xoxp-` token). Pick the scopes that match what you need to read:

| Command | Scopes |
| --- | --- |
| `message`, `thread`, `history` | `channels:history`, `groups:history`, `im:history`, and/or `mpim:history` |
| `channels`, `history #name` | `channels:read`, `groups:read`, `im:read`, and/or `mpim:read` |
| `search` | `search:read` |
| `--resolve-users` | `users:read` |

Add `files:read` if file metadata matters. Do not add write scopes such as `chat:write`; `slackx` is read-only.

Add those `export` lines to `~/.zshrc`, `~/.bashrc`, or another private shell startup file if you want them available in every terminal. Open a new terminal after setting persistent environment variables.

On macOS, prefer the login Keychain so secrets never land in files or shell history. `require_env` falls back to Keychain items with service `agent-clis` and the variable name as the account. The trailing `-w` prompts for the value with hidden input:

```sh
security add-generic-password -U -s agent-clis -a EXA_API_KEY -w
```

Lookup order: real environment variables, then `.env`, then Keychain.

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
