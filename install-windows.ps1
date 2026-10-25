# Copies the spac-525-writing skill into C:\Users\<you>\.claude\skills (outside the synced plugin folder).
# Run from the root of this repository:  powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
$dest = Join-Path $env:USERPROFILE ".claude\skills\spac-525-writing"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force ".claude\skills\spac-525-writing\*" $dest
Write-Host "Installed spac-525-writing to $dest"
python (Join-Path $dest "scripts\check_draft.py") --help | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Host "Checker runs." } else { Write-Host "Python not found or checker failed; install Python 3 and retry." }
