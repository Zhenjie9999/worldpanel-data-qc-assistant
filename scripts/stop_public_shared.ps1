$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $root "local_data\public-shared-runtime.json"
if (-not (Test-Path $runtimePath)) {
    Write-Host "No public shared runtime record was found."
    exit 0
}

$runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
foreach ($processId in @($runtime.tunnel_pid, $runtime.app_pid)) {
    if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $processId -Force
    }
}
Remove-Item -LiteralPath $runtimePath -Force
Write-Host "Public shared service stopped."
