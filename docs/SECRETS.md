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
| future `redditx` OAuth mode | Reddit OAuth client ID/secret |
| `googlex` | Google OAuth/application credentials |
| `slackx` | Slack bot token |
| `atlassianx` | Atlassian API token |

## Setup Pattern

Secrets live in the OS credential store, not in plaintext. On Windows that is
**Windows Credential Manager** (the equivalent of the macOS Keychain), reached through
the `keyring` library; on macOS `keyring` uses the Keychain, and on Linux it uses the
Secret Service / kwallet. Manage entries with the `secretsx` CLI:

```sh
secretsx set EXA_API_KEY        # hidden prompt, stored in the credential store
secretsx set REF_API_KEY
secretsx list                   # names + whether each is set (never prints values)
secretsx doctor                 # shows the backend and where each secret resolves from
secretsx delete EXA_API_KEY
```

To migrate an existing `.env` in one step:

```sh
secretsx import            # copy every recognized secret from .env into the store
secretsx import --purge    # ...and then strip the secret values out of .env
```

### Resolution order

`require_env()` resolves a secret as: (1) an explicit environment variable, then
(2) the credential store. Secrets no longer fall back to `.env`. So a one-off override
still works — e.g. `EXA_API_KEY=... searchx search "…"` — without changing the store.

### Non-secret config

Copy `.env.example` to `.env` for **non-secret** config only (`REDDIT_USER_AGENT`,
`ATLASSIAN_BASE_URL`, `ATLASSIAN_EMAIL`, and `GOOGLE_APPLICATION_CREDENTIALS`, which is a
file path). `.env` is ignored by Git. The CLIs load `.env` from this repo, from the
current directory tree, or from `%USERPROFILE%\.config\agent-clis\.env` on Windows or
`~/.config/agent-clis/.env` on macOS/Linux. Do not put API keys or tokens in `.env`.

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
