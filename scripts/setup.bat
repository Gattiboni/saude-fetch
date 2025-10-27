@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0\..

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

cd frontend
yarn install
cd ..

if not exist backend\.env (
  copy backend\.env.example backend\.env
)

REM Create Desktop shortcut to open http://localhost:3000 (requires PowerShell)
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\Fetch Saude.lnk');$s.TargetPath='C:\\Windows\\System32\\cmd.exe';$s.Arguments='/c start http://localhost:3000';$s.Save()"

echo Setup complete.
echo 1) Backend: call .venv\Scripts\activate ^&^& uvicorn backend.server:app --host 0.0.0.0 --port 8001
echo 2) Frontend: cd frontend ^&^& yarn dev --host
