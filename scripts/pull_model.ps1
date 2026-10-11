# usage: powershell -ExecutionPolicy Bypass -File scripts\pull_model.ps1 [-Repo ...] [-Quant ...] [-Name ...]
param(
  [string]$Repo = "mradermacher/Qwen3.5-2B-uncensored-ara-GGUF",
  [string]$Quant = "Q4_K_M",
  [string]$Name = "qwen-2b-uncensored"
)
$ErrorActionPreference = "Stop"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { Write-Host "Ollama is not installed: https://ollama.com/download"; exit 1 }
Set-Location (Join-Path $PSScriptRoot "..")
ollama pull "hf.co/${Repo}:${Quant}"
$tmp = New-TemporaryFile
(Get-Content models\Modelfile.template -Raw).Replace("__REPO__", $Repo).Replace("__QUANT__", $Quant) | Set-Content -Encoding ascii $tmp
ollama create $Name -f $tmp
Remove-Item $tmp
Write-Host "Done. Test: ollama run $Name"
Write-Host "Then set writer.model to `"$Name`" in config.json."
