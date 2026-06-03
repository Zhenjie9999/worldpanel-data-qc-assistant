$ErrorActionPreference = "Stop"

if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
    cloudflared --version
    exit 0
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget is not available. Ask IT to install cloudflared from Cloudflare's official distribution."
}

winget install --id Cloudflare.cloudflared --exact --source winget
Write-Host ""
Write-Host "cloudflared installation requested. Open a new terminal before starting the public test tunnel."
