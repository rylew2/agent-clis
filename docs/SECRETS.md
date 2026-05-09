# Secrets

No API keys or tokens should be committed to this repo.

## Current State

`ytx` does not require an API key.

Future tools may need credentials:

| Tool | Secret source |
|---|---|
| `searchx` | `EXA_API_KEY` |
| `docsx` | `REF_API_KEY` if using Ref directly |
| `redditx` | Reddit OAuth client ID/secret or read-only public endpoints |
| `googlex` | Google OAuth/application credentials |
| `slackx` | Slack bot token |
| `atlassianx` | Atlassian API token |

## Setup Pattern

Use environment variables for global CLI use:

```powershell
[Environment]::SetEnvironmentVariable("EXA_API_KEY", "your-key", "User")
```

Open a new terminal after setting a user environment variable.

For local development, copy `.env.example` to `.env` and fill values. `.env` is ignored by Git.

## Before Committing

Run:

```powershell
rg -n "api[_-]?key|token|secret|password|sk-|ghp_|xox|AIza" .
git status --short
```

Only placeholder names like `EXA_API_KEY` should appear.
