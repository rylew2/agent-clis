#!/usr/bin/env bash
set -u

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

export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"
export PATH="$repo_root/bin:$PATH"

bench_dir="$repo_root/cache/token-benchmarks"
mkdir -p "$bench_dir"

names=()
commands=()
exit_codes=()
outputs=()

run_benchmark_command() {
  local name="$1"
  shift

  local stdout_path="$bench_dir/$name.txt"
  local stderr_path="$bench_dir/$name.err.txt"

  "$@" >"$stdout_path" 2>"$stderr_path"
  local exit_code=$?

  if [ "$exit_code" -ne 0 ]; then
    {
      echo ""
      echo "[command failed with exit code $exit_code]"
      cat "$stderr_path"
    } >>"$stdout_path"
  fi

  names+=("$name")
  commands+=("$*")
  exit_codes+=("$exit_code")
  outputs+=("$stdout_path")
}

run_benchmark_command "ytx-transcript" ytx transcript YHk45NEpspE --no-header
run_benchmark_command "searchx-search" searchx search "Python argparse documentation" --limit 3 --max-chars 1000
run_benchmark_command "docsx-search" docsx search "Python argparse documentation" --limit 3 --max-chars 1000
run_benchmark_command "docsx-read" docsx read "https://docs.python.org/3/library/argparse.html" --max-chars 1000
run_benchmark_command "refx-search" refx search "Python argparse documentation" --max-chars 1000
run_benchmark_command "redditx-search" redditx search "Claude Code" --subreddit ClaudeAI --limit 3 --max-chars 1000
run_benchmark_command "corosx-status" corosx status
run_benchmark_command "browserx-links" browserx links "https://example.com" --limit 10
run_benchmark_command "semgrepx-scan" semgrepx scan . --config auto --limit 5

manifest_path="$bench_dir/manifest.json"
"$python_cmd" - "$manifest_path" "${#names[@]}" "${names[@]}" "${commands[@]}" "${exit_codes[@]}" "${outputs[@]}" <<'PY'
import json
import sys

manifest_path = sys.argv[1]
count = int(sys.argv[2])
offset = 3
names = sys.argv[offset:offset + count]
offset += count
commands = sys.argv[offset:offset + count]
offset += count
exit_codes = [int(value) for value in sys.argv[offset:offset + count]]
offset += count
outputs = sys.argv[offset:offset + count]

rows = [
    {"name": name, "command": command, "exit_code": exit_code, "output": output}
    for name, command, exit_code, output in zip(names, commands, exit_codes, outputs)
]

with open(manifest_path, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=2)
    fh.write("\n")
PY

echo "Benchmark output written to $bench_dir"
echo ""
"$python_cmd" -m agent_clis.tokensx "${outputs[@]}" --format table
