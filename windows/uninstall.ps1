# Remove localredact. Keeps your always-redact list unless -All is given.
param([switch]$All)
$home_ = if ($env:LOCALREDACT_HOME) { $env:LOCALREDACT_HOME } else { Join-Path $env:LOCALAPPDATA "localredact" }
Remove-Item -Recurse -Force (Join-Path $home_ "venv"), (Join-Path $home_ "app") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path ([Environment]::GetFolderPath("Programs")) "localredact") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path ([Environment]::GetFolderPath("Desktop")) "localredact.lnk") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--openai--privacy-filter") -ErrorAction SilentlyContinue
if ($All) { Remove-Item -Recurse -Force $home_ -ErrorAction SilentlyContinue }
Write-Host "localredact removed."
