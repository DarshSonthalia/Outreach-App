param([string]$token)
if (-not $token) { Write-Error 'Token argument required'; exit 1 }
$ErrorActionPreference = 'Stop'
$repoName = 'Outreach-App-Github'
$repoDesc = 'Repository created by assistant'
$private = $true
Set-Location -LiteralPath "$PSScriptRoot"
$user = (Invoke-RestMethod -Headers @{Authorization = "token $token"} -Uri 'https://api.github.com/user').login
if (-not $user) { Write-Error 'Failed to get GitHub user'; exit 1 }
$body = @{ name = $repoName; description = $repoDesc; private = $private } | ConvertTo-Json
try {
    Invoke-RestMethod -Headers @{Authorization = "token $token"} -Uri 'https://api.github.com/user/repos' -Method Post -Body $body -ContentType 'application/json'
} catch {
    try { $status = $_.Exception.Response.StatusCode.Value__ } catch { $status = $null }
    if ($status -eq 422) { Write-Output 'Repository may already exist; continuing.' } else { throw $_ }
}
if (-not (Test-Path '.git')) { git init }
# Stage everything
git add -A
# Commit if no HEAD exists
$hasHead = $false
try { git rev-parse --verify HEAD > $null; $hasHead = $true } catch { $hasHead = $false }
if (-not $hasHead) {
    git commit -m 'Initial commit (assistant)'
} else {
    try {
        git commit -m 'Update commit (assistant)'
    } catch {
        Write-Output 'No new changes to commit'
    }
}
$remoteUrlWithToken = "https://${user}:${token}@github.com/${user}/${repoName}.git"
try { git remote remove origin } catch { }
git remote add origin $remoteUrlWithToken
git push -u origin --all
git push origin --tags
# replace remote with tokenless url
git remote set-url origin "https://github.com/${user}/${repoName}.git"
Write-Output "REPO_URL=https://github.com/${user}/${repoName}"
