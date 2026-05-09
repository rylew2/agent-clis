$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$srcPath = Join-Path $repoRoot "src"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath;$env:PYTHONPATH" } else { $srcPath }
python -m agent_clis.corosx @args
exit $LASTEXITCODE
