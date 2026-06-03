$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $root "local_data\intranet-runtime.json"
if (-not (Test-Path $runtimePath)) {
    Write-Host "No intranet runtime record was found."
    exit 0
}

$runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
if ($runtime.app_pid -and (Get-Process -Id $runtime.app_pid -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $runtime.app_pid -Force
}
Remove-Item -LiteralPath $runtimePath -Force
Write-Host "Worldpanel Data QC Assistant intranet service stopped."
