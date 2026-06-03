$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as Administrator."
}

$displayName = "Worldpanel Data QC Assistant - Domain TCP 8765"
$existing = Get-NetFirewallRule -DisplayName $displayName -ErrorAction SilentlyContinue
if ($existing) {
    Set-NetFirewallRule -DisplayName $displayName -Enabled True -Direction Inbound -Action Allow -Profile Domain
} else {
    New-NetFirewallRule -DisplayName $displayName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -Profile Domain
}

Write-Host "Firewall rule enabled for Domain networks only: TCP 8765."
