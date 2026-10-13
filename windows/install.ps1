# Install localredact on Windows: Python environment, model (~2.8 GB), Start menu + desktop shortcuts.
# Run from the repo folder:  powershell -ExecutionPolicy Bypass -File windows\install.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here
$home_ = if ($env:LOCALREDACT_HOME) { $env:LOCALREDACT_HOME } else { Join-Path $env:LOCALAPPDATA "localredact" }
$venv = Join-Path $home_ "venv"
$app = Join-Path $home_ "app"
$list = Join-Path $home_ "Always redact.txt"
$py = Join-Path $venv "Scripts\python.exe"
$pyw = Join-Path $venv "Scripts\pythonw.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Install uv first:  winget install --id=astral-sh.uv -e   (then open a new PowerShell window)"
    exit 1
}

Write-Host "1/4 Python environment -> $venv"
uv venv -q --allow-existing --python 3.12 $venv
if ($LASTEXITCODE) { throw "uv venv failed" }
uv pip install -q --python $py --torch-backend=auto -r (Join-Path $here "requirements.txt")
if ($LASTEXITCODE) { throw "package install failed" }

Write-Host "2/4 Model (first time ~2.8 GB) -> Hugging Face cache"
& $py -I (Join-Path $here "engine_torch.py") --download-only
if ($LASTEXITCODE) { throw "model download failed" }

Write-Host "3/4 App -> $app"
New-Item -ItemType Directory -Force -Path $app | Out-Null
Copy-Item (Join-Path $repo "core\redact_core.py"), (Join-Path $here "engine_torch.py"), (Join-Path $here "localredact_app.pyw") $app -Force
if (-not (Test-Path $list)) { Copy-Item (Join-Path $repo "always-redact.example.txt") $list }

Write-Host "4/4 Shortcuts"
$shell = New-Object -ComObject WScript.Shell
$startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "localredact"
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
foreach ($dir in @($startMenu, [Environment]::GetFolderPath("Desktop"))) {
    $lnk = $shell.CreateShortcut((Join-Path $dir "localredact.lnk"))
    $lnk.TargetPath = $pyw
    $lnk.Arguments = "`"$(Join-Path $app 'localredact_app.pyw')`""
    $lnk.WorkingDirectory = $app
    $lnk.Description = "Redact personal information from documents, locally"
    $lnk.Save()
}
$lnk = $shell.CreateShortcut((Join-Path $startMenu "Edit always-redact list.lnk"))
$lnk.TargetPath = "notepad.exe"
$lnk.Arguments = "`"$list`""
$lnk.Save()

$gpu = & $py -I -c "import torch; print('NVIDIA GPU (fast)' if torch.cuda.is_available() else 'CPU only (works, but long files take minutes)')"
Write-Host ""
Write-Host "Done. Open 'localredact' from the Start menu or desktop and choose files to redact."
Write-Host "Running on: $gpu"
Write-Host "Words that must always be removed (your name, street...): Start menu > localredact > Edit always-redact list"
