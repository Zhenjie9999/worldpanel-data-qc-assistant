$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared is not installed. Run install_cloudflared.ps1 first."
}

$securePassword = Read-Host "Shared access password" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $env:WORLDPANEL_QC_ACCESS_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}

if (-not $env:WORLDPANEL_QC_ACCESS_PASSWORD) {
    throw "A shared access password is required."
}

$env:WORLDPANEL_QC_ALLOW_LLM_SETTINGS = "0"
$env:WORLDPANEL_QC_COOKIE_SECURE = "1"
$env:WORLDPANEL_QC_MAX_REQUEST_BYTES = "157286400"

$port = 8877
if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
    throw "Port $port is already in use. Close the existing public-test QC window first."
}

$stdout = Join-Path $root "local_data\public-test-app.out.log"
$stderr = Join-Path $root "local_data\public-test-app.err.log"
$tunnelStdout = Join-Path $root "local_data\cloudflared.out.log"
$tunnelStderr = Join-Path $root "local_data\cloudflared.err.log"
$runtimePath = Join-Path $root "local_data\public-test-runtime.json"
Remove-Item -LiteralPath $stdout, $stderr, $tunnelStdout, $tunnelStderr -Force -ErrorAction SilentlyContinue
$server = Start-Process -FilePath "python" -ArgumentList "app.py", "--host", "127.0.0.1", "--port", "$port", "--no-browser" -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

try {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/health" -TimeoutSec 1 | Out-Null
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if ($attempt -eq 20) {
        throw "The local QC service did not start. Review local_data\public-test-app.err.log."
    }
    $tunnel = Start-Process -FilePath "cloudflared" -ArgumentList "tunnel", "--url", "http://127.0.0.1:$port" -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $tunnelStdout -RedirectStandardError $tunnelStderr -PassThru
    $url = ""
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        $logs = (Get-Content -LiteralPath $tunnelStdout -Raw -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath $tunnelStderr -Raw -ErrorAction SilentlyContinue)
        $match = [regex]::Match($logs, "https://[a-z0-9-]+\.trycloudflare\.com")
        if ($match.Success) {
            $url = $match.Value
            break
        }
    }
    if (-not $url) {
        throw "The temporary HTTPS URL could not be detected. Review local_data\cloudflared.err.log."
    }
    @{
        app_pid = $server.Id
        tunnel_pid = $tunnel.Id
        url = $url
        started_at = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding UTF8
    Write-Host ""
    Write-Host "Temporary HTTPS public tunnel is ready."
    Write-Host "Share only this URL:"
    Write-Host $url
    Write-Host ""
    Read-Host "Press Enter to stop the public test service"
} finally {
    if ($tunnel -and -not $tunnel.HasExited) {
        Stop-Process -Id $tunnel.Id -Force
    }
    if (-not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
    Remove-Item -LiteralPath $runtimePath -Force -ErrorAction SilentlyContinue
}
