# Git pre-commit 훅 설치 (pack_data 자동 실행)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $root ".githooks\pre-commit"
$dst = Join-Path $root ".git\hooks\pre-commit"
if (-not (Test-Path $src)) { Write-Error "missing $src"; exit 1 }
Copy-Item -Force $src $dst
Write-Host "installed: $dst"
