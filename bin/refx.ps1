$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = Join-Path $repoRoot "src"
python -m agent_clis.refx @args
exit $LASTEXITCODE
