param([string]$token, [string]$repoUrl)
if (-not $token) { Write-Error 'Token argument required'; exit 1 }
if (-not $repoUrl) { Write-Error 'Repository URL required'; exit 1 }
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath "$PSScriptRoot"
if (-not (Test-Path '.git')) { git init }
# Stage everything
git add -A
# Commit if no HEAD exists
$hasHead = $false
try { git rev-parse --verify HEAD | Out-Null; $hasHead = $true } catch { $hasHead = $false }
if (-not $hasHead) {
    git commit -m 'Initial commit (assistant)'
} else {
    try {
        git commit -m 'Update commit (assistant)'
    } catch {
        Write-Output 'No new changes to commit'
    }
}
# parse owner and repo
$match = [regex]::Match($repoUrl, 'github.com/([^/]+)/([^/]+)(?:\.git)?$')
if (-not $match.Success) { Write-Error 'Could not parse owner/repo from URL'; exit 1 }
$owner = $match.Groups[1].Value
$repoName = $match.Groups[2].Value
$remoteWithToken = "https://${owner}:${token}@github.com/${owner}/${repoName}.git"
try { git remote remove origin } catch { }
git remote add origin $remoteWithToken
# attempt push
$pushSucceeded = $false
try {
    git push -u origin --all
    git push origin --tags
    $pushSucceeded = $true
} catch {
    Write-Output 'Initial push failed; attempting fetch+merge then push'
    try { git fetch origin } catch { Write-Output 'Fetch failed'; throw $_ }
    try {
        git merge --allow-unrelated-histories origin/main -m 'Merge remote main' | Out-Null
        git push -u origin --all
        git push origin --tags
        $pushSucceeded = $true
    } catch {
        Write-Output 'Merge failed or branch main missing; attempting force push'
        git push -u origin --all --force
        git push origin --tags --force
        $pushSucceeded = $true
    }
}
# restore tokenless remote
try { git remote set-url origin "https://github.com/${owner}/${repoName}.git" } catch { }
if ($pushSucceeded) { Write-Output "REPO_URL=${repoUrl}"; exit 0 } else { Write-Error 'Push did not succeed'; exit 1 }
