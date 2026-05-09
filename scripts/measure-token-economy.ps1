$ErrorActionPreference = "Continue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $repoRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

$benchDir = Join-Path $repoRoot "cache\token-benchmarks"
New-Item -ItemType Directory -Force -Path $benchDir | Out-Null

function Invoke-BenchmarkCommand {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string[]]$Command
  )

  $stdoutPath = Join-Path $benchDir "$Name.txt"
  $stderrPath = Join-Path $benchDir "$Name.err.txt"
  $exe = $Command[0]
  $argsForExe = @()
  if ($Command.Length -gt 1) {
    $argsForExe = $Command[1..($Command.Length - 1)]
  }

  & $exe @argsForExe > $stdoutPath 2> $stderrPath
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    Add-Content -LiteralPath $stdoutPath -Value ""
    Add-Content -LiteralPath $stdoutPath -Value "[command failed with exit code $exitCode]"
    Add-Content -LiteralPath $stdoutPath -Value (Get-Content -Raw -LiteralPath $stderrPath)
  }

  [PSCustomObject]@{
    name = $Name
    command = ($Command -join " ")
    exit_code = $exitCode
    output = $stdoutPath
  }
}

$results = @()
$results += Invoke-BenchmarkCommand "ytx-transcript" @("ytx", "transcript", "YHk45NEpspE", "--no-header")
$results += Invoke-BenchmarkCommand "searchx-search" @("searchx", "search", "Python argparse documentation", "--limit", "3", "--max-chars", "1000")
$results += Invoke-BenchmarkCommand "docsx-search" @("docsx", "search", "Python argparse documentation", "--limit", "3", "--max-chars", "1000")
$results += Invoke-BenchmarkCommand "docsx-read" @("docsx", "read", "https://docs.python.org/3/library/argparse.html", "--max-chars", "1000")
$results += Invoke-BenchmarkCommand "refx-search" @("refx", "search", "Python argparse documentation", "--max-chars", "1000")
$results += Invoke-BenchmarkCommand "redditx-search" @("redditx", "search", "Claude Code", "--subreddit", "ClaudeAI", "--limit", "3", "--max-chars", "1000")
$results += Invoke-BenchmarkCommand "corosx-status" @("corosx", "status")
$results += Invoke-BenchmarkCommand "browserx-links" @("browserx", "links", "https://example.com", "--limit", "10")
$results += Invoke-BenchmarkCommand "semgrepx-scan" @("semgrepx", "scan", ".", "--config", "auto", "--limit", "5")

$manifestPath = Join-Path $benchDir "manifest.json"
$results | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host "Benchmark output written to $benchDir"
Write-Host ""
python -m agent_clis.tokensx ($results.output) --format table
