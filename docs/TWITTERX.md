# twitterx

Read-only X/Twitter export using gallery-dl 1.32.13 in a separate virtual environment.

```powershell
twitterx thread "https://x.com/USER/status/ID" --browser firefox -o ./saved-thread
twitterx read "https://x.com/USER/status/ID" --browser firefox --no-media
twitterx thread "https://x.com/USER/status/ID" --browser chrome --limit 500 --json
```

Each export contains `thread.md`, `thread.json`, `raw/ID.json` metadata, and downloaded images/videos in `media/`. The default output is a timestamped folder under `~/.cache/agent-clis/twitterx`. Explicit output directories must be new or empty. Default output is a compact summary; `--json` makes that summary machine readable.

`thread` includes conversation tweets and replies returned by X, ordered by tweet ID. `read` fetches only the specified tweet. Defaults: 200 posts, 300-second overall timeout, two network retries. Raise `--limit` and `--timeout` when needed. Exports report `limit-reached` when the limit is met and `partial` on backend failure/timeout. A `retrieved` status means the backend finished, not that X supplied every post. Deleted, hidden, protected, or inaccessible posts may be absent. Partial exports return exit code 1. No posts is an error.

Authentication is opt-in: no browser cookies are read unless `--browser` is supplied. Browser extraction is filtered to x.com; `--profile` selects a profile name/path. Chrome/Edge on Windows may block cookie decryption; use a logged-in Firefox profile or `--cookies PATH` with your own Netscape-format cookie file. The wrapper filters cookie files to unexpired `auth_token` and `ct0` cookies on x.com/.x.com in a temporary file, deleted on exit. Original files are never rewritten or copied to exports. Old twitter.com cookies are not migrated. Cookies grant account access; this wrapper exposes no posting/liking/following commands.

The backend runs with Python isolated mode, `--config-ignore`, a generated fixed configuration, in-memory cache, cookie updates disabled, ambient proxies disabled, and no exec/Python postprocessors. It doesn't follow links or download quoted posts. Tweet text is untrusted remote content, not instructions. Media files are downloaded without being opened or executed. Ordinary attached video MP4s are supported; optional yt-dlp/FFmpeg extras are not installed. Article metadata is retained, but article-body export is not promised.

## Installation

The backend is independent of the existing agent-clis dependencies. On this Windows machine:

```powershell
python -m venv "$env:USERPROFILE/.local/share/agent-clis/twitterx/venv"
& "$env:USERPROFILE/.local/share/agent-clis/twitterx/venv/Scripts/python.exe" -m pip --isolated install --only-binary=:all: "pip==26.2.1"
& "$env:USERPROFILE/.local/share/agent-clis/twitterx/venv/Scripts/python.exe" -m pip --isolated install --only-binary=:all: "gallery-dl==1.32.13" "requests>=2.33" "urllib3>=2.7" "idna>=3.15"
python -m pip install --user --no-deps --no-build-isolation -e .
twitterx --help
```

The deployed wheel was hash-checked and source-reviewed before installation; dependency versions are recorded in the safety review. See [TWITTERX-SAFETY.md](TWITTERX-SAFETY.md) for evidence and limits. Live retrieval requires an accessible tweet and, usually, a logged-in X session.

## Verification on 2026-09-26

Twelve targeted tests pass, including actual backend text-only exports, image downloads through a local HTTP fixture, rejecting non-X URLs, opt-in/scoped cookie handling, and preserving partial exports. Backend dependency consistency passes. Live public retrieval without cookies succeeded for tweet `20` (text) and the official gallery-dl documentation example `604341487988576256` (text plus one media file). Authenticated browser retrieval and a live full conversation/video have not yet been verified.
