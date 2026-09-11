# Lumen - one-command start for Windows PowerShell.
# Installs dependencies on first run, then opens the API (8002) and UI (5174) in two windows.

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  Write-Host "Creating Python virtual environment..."
  python -m venv (Join-Path $backend ".venv")
  & $python -m pip install --quiet -r (Join-Path $backend "requirements.txt")
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "Installing frontend packages..."
  Push-Location $frontend
  npm install
  Pop-Location
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; & '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; npm run dev"

Start-Sleep -Seconds 4
Start-Process "http://localhost:5174"
Write-Host "Lumen: API http://127.0.0.1:8002  UI http://localhost:5174"
