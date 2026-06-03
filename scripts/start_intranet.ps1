$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

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
$env:WORLDPANEL_QC_COOKIE_SECURE = "0"
$env:WORLDPANEL_QC_MAX_REQUEST_BYTES = "157286400"

if (Get-NetTCPConnection -State Listen -LocalPort 8765 -ErrorAction SilentlyContinue) {
    throw "Port 8765 is already in use. Close the existing QC window before starting intranet mode."
}

Write-Host ""
Write-Host "Starting Worldpanel Data QC Assistant for the company intranet."
Write-Host "Keep this window open while colleagues use the service."
Write-Host ""
python app.py --intranet --no-browser
