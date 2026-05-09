# Install

These tools are packaged as a Python project. After cloning the repo on another computer, install once and the commands will be available from new terminals.

## Windows

From the repo root:

```powershell
.\scripts\install.ps1
```

The installer prefers `pipx` when available because it keeps CLI tools isolated from the system Python. If `pipx` is not installed, it falls back to:

```powershell
python -m pip install --user -e .
```

If the Python user scripts directory is not on your user `PATH`, the script adds it. Open a new terminal after install.

## Manual Install

```powershell
python -m pip install -e .
```

Then test:

```powershell
ytx --help
searchx --help
docsx --help
semgrepx --help
redditx --help
corosx --help
browserx --help
ytx transcript YHk45NEpspE --no-header
```

Optional external tools:

- `semgrepx` needs Semgrep on PATH: `python -m pip install semgrep`. Registry configs such as `auto` may report pseudonymous rule metrics to Semgrep.
- `browserx screenshot` needs Playwright's Node CLI: `npm install -g playwright` and `playwright install chromium`

## Update After Pull

For editable installs, pulling the repo is usually enough:

```powershell
git pull
```

If dependencies changed:

```powershell
.\scripts\install.ps1
```

## Uninstall

If installed with `pipx`:

```powershell
pipx uninstall agent-clis
```

If installed with `pip`:

```powershell
python -m pip uninstall agent-clis
```
