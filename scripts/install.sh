#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if command -v python3 >/dev/null 2>&1; then
  python_cmd="python3"
elif command -v python >/dev/null 2>&1; then
  python_cmd="python"
else
  echo "Python 3.11+ is required but was not found on PATH." >&2
  exit 1
fi

"$python_cmd" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required.")
PY

if command -v pipx >/dev/null 2>&1; then
  echo "Installing agent-clis with pipx..."
  pipx install --force --editable "$repo_root"
  pipx ensurepath
else
  echo "pipx not found; installing agent-clis with pip --user..."
  "$python_cmd" -m pip install --user -e "$repo_root"
  user_base="$("$python_cmd" -m site --user-base)"
  scripts_path="$user_base/bin"

  case ":$PATH:" in
    *":$scripts_path:"*) ;;
    *)
      echo ""
      echo "Add this directory to PATH if the commands are not found:"
      echo "  $scripts_path"
      echo ""
      echo "For zsh, add this to ~/.zshrc:"
      echo "  export PATH=\"$scripts_path:\$PATH\""
      echo "For bash, add this to ~/.bashrc or ~/.bash_profile:"
      echo "  export PATH=\"$scripts_path:\$PATH\""
      ;;
  esac
fi

echo ""
echo "Install complete. Test in a new terminal with:"
echo "  ytx --help"
echo "  searchx --help"
echo "  docsx --help"
echo "  refx --help"
echo "  semgrepx --help"
echo "  redditx --help"
echo "  corosx --help"
echo "  browserx --help"
echo "  tokensx --help"
