$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = Join-Path $repoRoot "src"
python -m agent_clis.secretsx @args
exit $LASTEXITCODE
