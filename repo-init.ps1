# Run in PowerShell INSIDE your personal repo folder (where .git exists)

$ErrorActionPreference = "Stop"

# 1) Verify we're in a git repo
git rev-parse --is-inside-work-tree | Out-Null

# 2) Get current origin URL (must exist)
$remoteUrl = (git remote get-url origin 2>$null)
if (-not $remoteUrl) {
  throw "No 'origin' remote found. If you haven't cloned yet, clone first, then run this script inside the cloned folder."
}

# 3) Ensure origin is HTTPS (PAT approach)
if ($remoteUrl -match '^git@') {
  Write-Host "Origin is SSH ($remoteUrl). Switching to HTTPS for PAT-based auth..." -ForegroundColor Yellow

  # Convert: git@github.com:OWNER/REPO.git -> https://github.com/OWNER/REPO.git
  $httpsUrl = $remoteUrl -replace '^git@github\.com:', 'https://github.com/'
  git remote set-url origin $httpsUrl
  $remoteUrl = $httpsUrl
}

if ($remoteUrl -notmatch '^https://github\.com/') {
  throw "This script supports GitHub HTTPS remotes. Current origin: $remoteUrl"
}

# 4) Make credential storage path-specific so company + personal can coexist
git config --local credential.useHttpPath true | Out-Null

# 5) Use Git Credential Manager (Windows)
git config --local credential.helper manager-core | Out-Null

# 6) Ask for personal GitHub username + PAT
$ghUser = Read-Host "Enter your PERSONAL GitHub username"
$securePat = Read-Host "Paste your PERSONAL GitHub PAT (it will not echo)" -AsSecureString
$pat = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePat))

if ([string]::IsNullOrWhiteSpace($ghUser) -or [string]::IsNullOrWhiteSpace($pat)) {
  throw "Username / PAT can't be empty."
}

# 7) Remove any cached credential for THIS exact URL (so the new one wins)
$uri = [Uri]$remoteUrl
$ghHost = $uri.Host
$ghPath = $uri.AbsolutePath

$reject = @"
protocol=https
host=$ghHost
path=$ghPath

"@
$reject | git credential reject | Out-Null

# 8) Store the personal credential for THIS repo URL
$approve = @"
protocol=https
host=$ghHost
path=$ghPath
username=$ghUser
password=$pat

"@
$approve | git credential approve | Out-Null

# 9) Test authentication
Write-Host "Testing access to origin..." -ForegroundColor Cyan
git ls-remote $remoteUrl | Out-Null

Write-Host "✅ Done. This repo will use your PERSONAL GitHub credentials for $remoteUrl" -ForegroundColor Green