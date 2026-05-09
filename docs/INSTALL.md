# Install

These tools are packaged as a Python project. After cloning the repo on another computer, install once and the commands will be available from new terminals on Windows, macOS, or Linux.

The shared install target is the package entry points in `pyproject.toml`. The PowerShell and Bash scripts are convenience wrappers around the same Python package.

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

## macOS / Linux

From the repo root:

```sh
./scripts/install.sh
```

The installer prefers `pipx` when available because it keeps CLI tools isolated from the system Python. If `pipx` is not installed, it falls back to:

```sh
python3 -m pip install --user -e .
```

If the Python user scripts directory is not on your `PATH`, the script prints the directory and shell snippet to add to `~/.zshrc`, `~/.bashrc`, or `~/.bash_profile`. Open a new terminal after install.

## Manual Install

Windows:

```powershell
python -m pip install --user -e .
```

macOS/Linux:

```sh
python3 -m pip install --user -e .
```

Then test:

```sh
ytx --help
searchx --help
docsx --help
refx --help
semgrepx --help
redditx --help
corosx --help
browserx --help
tokensx --help
ytx transcript YHk45NEpspE --no-header
```

Optional external tools:

- `semgrepx` needs Semgrep on PATH: `python -m pip install semgrep` or `python3 -m pip install semgrep`. Registry configs such as `auto` may report pseudonymous rule metrics to Semgrep.
- `browserx screenshot` needs Playwright's Node CLI: `npm install -g playwright` and `playwright install chromium`

## Run Without Installing

Windows PowerShell:

```powershell
$env:PYTHONPATH = ".\src"
python -m agent_clis.ytx --help
.\bin\ytx.ps1 transcript YHk45NEpspE --no-header
```

macOS/Linux:

```sh
export PYTHONPATH="$PWD/src"
python3 -m agent_clis.ytx --help
./bin/ytx transcript YHk45NEpspE --no-header
```

## Update After Pull

For editable installs, pulling the repo is usually enough:

```sh
git pull
```

If dependencies changed:

Windows:

```powershell
.\scripts\install.ps1
```

macOS/Linux:

```sh
./scripts/install.sh
```

## Uninstall

If installed with `pipx`:

```sh
pipx uninstall agent-clis
```

If installed with `pip`:

Windows:

```powershell
python -m pip uninstall agent-clis
```

macOS/Linux:

```sh
python3 -m pip uninstall agent-clis
```
