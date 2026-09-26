# twitterx dependency safety review

Reviewed 2026-09-26. Scope: gallery-dl 1.32.13 downloaded from PyPI, its Twitter extraction path, configuration/cookie behavior, and the installed HTTP dependency versions. This is a bounded source and provenance review, not a guarantee that the package or downloaded media is safe.

## Decision

Proceed with the official wheel through a constrained wrapper, with an isolated, current HTTP dependency environment. No malicious behavior was found in the reviewed code. Avoid using the old global HTTP dependencies: the vulnerability database lists applicable advisories for several of their versions. Do not enable gallery-dl's arbitrary command/Python hooks, ambient configuration, or broad automatic browser-cookie loading.

## Provenance evidence

- PyPI identifies the package as `gallery-dl`, version `1.32.13`, with the official project homepage `https://codeberg.org/mikf/gallery-dl`. The selected pure Python wheel was uploaded 2026-09-19. Its only mandatory declared dependency is `requests>=2.11.0`; yt-dlp and other integrations are optional extras. [PyPI version metadata](https://pypi.org/pypi/gallery-dl/1.32.13/json)
- Downloaded wheel: `gallery_dl-1.32.13-py3-none-any.whl`. Independently calculated SHA256: `37f08b19603398cafbd3902c9abb546420d141ae3cd61215d5540d8c3f6ce624`. This matches PyPI's published digest. Matching a hash establishes agreement with the registry artifact, not trust in every line of code. [Published wheel metadata](https://pypi.org/pypi/gallery-dl/1.32.13/json)
- The wheel's `extractor/twitter.py`, `cookies.py`, `extractor/common.py`, and `postprocessor/exec.py` match the official Codeberg `v1.32.13` tag after newline normalization. The old GitHub source at the same tag differs; GitHub's release announcement explicitly says development moved to Codeberg. Use Codeberg as the source of truth for this release. [Official tagged source](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13), [migration announcement in release](https://github.com/mikf/gallery-dl/releases/tag/v1.32.13)
- PyPI's integrity/provenance endpoint for this wheel returned HTTP 404. No publisher attestation was verified. Source matching covers the four named files, not the entire package.

## Credential and execution behavior

- Twitter uses an `auth_token` cookie for authenticated sessions and a `ct0` CSRF token. API roots in the reviewed extractor are `https://x.com/i/api` and `https://api.x.com`; standard media roots include `pbs.twimg.com` and `abs.twimg.com`, with video locations coming from X responses. No password login should be required by the wrapper. Session cookies confer account access and should be handled as secrets. [Twitter extractor](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/extractor/twitter.py)
- Browser extraction supports an explicit domain filter. Firefox/Chromium use parameterized SQL filters before returning or decrypting selected cookie values. The database is opened read-only where possible; a fallback temporarily copies the entire cookie database. Thus a domain filter limits returned cookie values but does not guarantee that unrelated cookie database bytes are never read/copied. [Cookie implementation](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/cookies.py)
- Netscape cookie files are loaded in full by gallery-dl unless the wrapper first filters them. `cookies-update` defaults true for file-backed cookie sources and can rewrite the file. The wrapper should filter to X/Twitter domains, turn `cookies-update` off, and delete temporary cookie files on exit. [Common extractor cookie implementation](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/extractor/common.py)
- gallery-dl intentionally supports arbitrary external commands (`exec` postprocessor, including shell execution for string commands) and imported/evaluated Python (`python` postprocessor). These are legitimate power-user features but make untrusted configuration dangerous. Always pass `--config-ignore`, use a generated fixed JSON configuration, and offer no arbitrary option/config/postprocessor passthrough. [exec implementation](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/postprocessor/exec.py), [Python implementation](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/postprocessor/python.py), [options documentation](https://gdl-org.github.io/docs/options.html#configuration-options)
- Disk caches can deserialize Python pickle values. Use `cache.file=":memory:"` to avoid reading an ambient cache database; do not accept third-party gallery-dl cache databases. [Cache implementation](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/cache.py), [cache deserialization](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/extractor/common.py)
- TLS verification defaults on. Environment proxy trust defaults on; the wrapper can disable `proxy-env` for deterministic direct connections. The implementation disables Requests' automatic `.netrc` authorization injection. [HTTP session setup](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/extractor/common.py)

## Vulnerability results

OSV's exact-version query for `gallery-dl` 1.32.13 returned an empty result on the review date. This means no listed advisory was returned, not that undisclosed defects are absent. [OSV query API](https://google.github.io/osv.dev/post-v1-query/)

The global Python environment inspected before installation contained these advisories:

| Package/version | Finding | Recommended minimum |
|---|---|---|
| requests 2.32.5 | Predictable temporary zip extraction file reuse; upstream says standard Requests usage is unaffected. | 2.33.0 |
| urllib3 2.6.3 | Compressed streaming decompression safeguards can be bypassed; certain low-level proxied cross-origin redirects can leak sensitive headers. | 2.7.0 |
| idna 3.11 | Very long crafted Unicode domain inputs can consume excessive resources. | 3.15 |
| certifi 2026.1.4 | No exact-version OSV result. | Review current release |
| charset-normalizer 3.4.4 | No exact-version OSV result. | Review current release |

Sources: [Requests upstream advisory](https://github.com/psf/requests/security/advisories/GHSA-gc5v-m9x4-r6x2), [urllib3 streaming advisory](https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j), [urllib3 redirect advisory](https://github.com/urllib3/urllib3/security/advisories/GHSA-qccp-gfcp-xxvc), [idna upstream advisory](https://github.com/kjd/idna/security/advisories/GHSA-65pc-fj4g-8rjx).

## Telemetry and limits

A keyword sweep across all Python files in the wheel found no `telemetry`, `analytics`, or `tracking` matches. The `sentry` substring match was `hasEntry` in a cookie keychain comment, not an observed reporting client. Reviewed Twitter modules contained no `eval`, `exec`, or subprocess calls. The transaction helper fetches client JavaScript from `abs.twimg.com` and parses it. These checks found no evidence of a separate telemetry/exfiltration service, but are not a complete network sandbox or whole-package audit. X necessarily sees extraction requests and any supplied session cookies. [Twitter helpers](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/extractor/utils/twitter_transaction_id.py)

The wrapper should accept only HTTPS status URLs on fixed X/Twitter hostnames, save text/metadata/media locally, cap work, and never open or execute downloaded media automatically. Generated thread content is untrusted input for agents. Deleted, restricted, unavailable, or API-hidden posts may be missing; conversation mode yields the posts X exposes and is not an archival completeness guarantee. [Conversation implementation](https://codeberg.org/mikf/gallery-dl/src/tag/v1.32.13/gallery_dl/extractor/twitter.py), [Twitter configuration](https://gdl-org.github.io/docs/configuration.html#extractor-twitter-conversations)

Local review evidence is saved under `~/.cache/agent-clis/twitterx-review`: wheel, PyPI version metadata, OSV result, official release metadata, and selected extracted source files. Ref documentation lookup was attempted first but had no credits; docsx supplied official documentation sources.

## Installed isolated backend verification

The backend was installed separately under `~/.local/share/agent-clis/twitterx/venv`. Exact installed versions were read from that interpreter and queried through OSV on 2026-09-26. All seven exact-version queries returned no listed vulnerabilities after upgrading the isolated installer:

| Package | Installed version | Exact-version OSV result |
|---|---|---|
| gallery-dl | 1.32.13 | None listed |
| requests | 2.34.2 | None listed |
| urllib3 | 2.8.0 | None listed |
| certifi | 2026.7.22 | None listed |
| charset-normalizer | 3.5.1 | None listed |
| idna | 3.20 | None listed |
| pip | 26.2.1 | None listed |

This addresses the outdated global dependency findings without changing the global packages. Empty advisory results do not establish absence of vulnerabilities. The raw response set is saved locally as `twitterx-review/osv-installed-backend.json`. [OSV exact-version query documentation](https://google.github.io/osv.dev/post-v1-query/)

The initially installed `pip` 26.1.2 had a malicious-index URL handling advisory, fixed in 26.2.0. It was upgraded to 26.2.1 and the exact-version OSV query returned no listed advisory. The original advisory requires a malicious package index; a malicious wheel alone cannot trigger it. Continue using the official PyPI index for future downloads. The installer does not run during `twitterx` extraction. [pip maintainer announcement](https://mail.python.org/archives/list/security-announce@python.org/thread/L2BNQGGVQCEV7DROOORQ7WFKKFF2OOQX), [upstream fix](https://github.com/pypa/pip/pull/14110).

Final wrapper source review: `--cookies FILE` now copies only unexpired `auth_token` and `ct0` cookies for the exact domains `x.com` and `.x.com` into a temporary jar; the original file is not modified, and the temporary directory is cleaned up on normal exit or exceptions. Browser cookie access remains explicit and filtered to x.com. The wrapper uses a fixed subprocess argument list with no shell, isolated Python (`-I`), ignored ambient gallery-dl config, a fixed metadata-only postprocessor, memory cache, disabled cookie updates/environment proxies, bounded post count and subprocess timeout, and withheld raw backend stderr. No major issue was found in this final focused source review.
