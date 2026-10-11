# Checks this Windows machine and proves the studio works. Installs nothing; it tells you what is missing.
# Run from PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$fail = $false

$py = $null
foreach ($c in @("python", "py")) {
  if (Get-Command $c -ErrorAction SilentlyContinue) {
    & $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $py = $c; break }
  }
}
if (-not $py) { Write-Host "MISSING: Python 3.9 or newer.  winget install Python.Python.3.12"; $fail = $true }
else { Write-Host ("python: " + (& $py --version)) }

foreach ($t in @("ffmpeg", "ffprobe")) {
  if (Get-Command $t -ErrorAction SilentlyContinue) { Write-Host "${t}: found" }
  else { Write-Host "MISSING: $t   (winget install Gyan.FFmpeg, then open a NEW terminal)"; $fail = $true }
}
if ($fail) { Write-Host "`nInstall the missing pieces above, then run this script again."; exit 1 }

Write-Host "`nRunning the self-test (renders a tiny mock movie, checks it has video AND audio)..."
& $py -m movie_studio selftest
if ($LASTEXITCODE -ne 0) { Write-Host "Self-test failed. See docs\INSTALL.md, Troubleshooting."; exit 1 }

Write-Host "`nDone. The studio works on this machine."
Write-Host "  Try it:     $py -m movie_studio make `"A short test. Another short test.`" --writer template --scenes 3"
Write-Host "  Text model: scripts\pull_model.ps1   (needs Ollama: https://ollama.com/download)"
Write-Host "  Real video: docs\INSTALL.md, section 'Real video'"
