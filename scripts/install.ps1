$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $repoRoot

function Test-Command($Name) {
  $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Add-UserPath($PathToAdd) {
  $current = [Environment]::GetEnvironmentVariable("Path", "User")
  $parts = @()
  if ($current) {
    $parts = $current -split ";"
  }

  $alreadyPresent = $parts | Where-Object {
    $_.TrimEnd("\") -ieq $PathToAdd.TrimEnd("\")
  }

  if (-not $alreadyPresent) {
    $newPath = if ($current) { "$current;$PathToAdd" } else { $PathToAdd }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added to user PATH: $PathToAdd"
    Write-Host "Open a new terminal for PATH changes to take effect."
  }
}

if (-not (Test-Command python)) {
  throw "Python is required but was not found on PATH."
}

if (Test-Command pipx) {
  Write-Host "Installing agent-clis with pipx..."
  pipx install --force --editable "$repoRoot"
  pipx ensurepath
} else {
  Write-Host "pipx not found; installing agent-clis with pip --user..."
  python -m pip install --user -e "$repoRoot"
  $userBase = python -m site --user-base
  $scriptsPath = Join-Path $userBase "Scripts"
  Add-UserPath $scriptsPath
}

Write-Host ""
Write-Host "Install complete. Test in a new terminal with:"
Write-Host "  ytx --help"
Write-Host "  searchx --help"
Write-Host "  docsx --help"
Write-Host "  refx --help"
Write-Host "  semgrepx --help"
Write-Host "  redditx --help"
Write-Host "  corosx --help"
Write-Host "  browserx --help"
Write-Host "  tokensx --help"
