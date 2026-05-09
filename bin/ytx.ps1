$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$srcPath = Join-Path $repoRoot "src"

if ($env:PYTHONPATH) {
  $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
} else {
  $env:PYTHONPATH = $srcPath
}

python -m agent_clis.ytx @args
exit $LASTEXITCODE
