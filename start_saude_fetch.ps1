<#
start_saude_fetch.ps1 — versão corrigida
Ajuste: cada serviço é iniciado no diretório correto (app/backend e app/frontend)
#>

param(
  [string]$Action = "start"
)

$MongoBin = "C:\\Program Files\\MongoDB\\Server\\8.2\\bin\\mongod.exe"
$MetaFile = Join-Path -Path $PSScriptRoot -ChildPath "saude_fetch.pids.json"
$ShortcutFolder = "D:\\Backup C 256\\Desktop\\Gattiboni Enterprises\\Lucas Farinazzo"
$ShortcutName = "Start - saude-fetch.lnk"
$ShortcutPath = Join-Path -Path $ShortcutFolder -ChildPath $ShortcutName

function Save-Pids($obj) {
    $json = $obj | ConvertTo-Json -Depth 4
    Set-Content -Path $MetaFile -Value $json -Encoding UTF8
}

function Get-Pids() {
    if (Test-Path $MetaFile) {
        try { return Get-Content $MetaFile -Raw | ConvertFrom-Json } catch { return $null }
    }
    return $null
}

function Start-Mongo {
    Write-Host ">> Verificando mongod..."
    if (-not (Test-Path $MongoBin)) {
        Write-Error "mongod.exe não encontrado em $MongoBin. Ajuste $MongoBin no topo do script."
        return $null
    }

    if (-not (Test-Path "C:\\data\\db")) {
        try { New-Item -ItemType Directory -Path "C:\\data\\db" -Force | Out-Null } catch {}
    }

    $mongodRunning = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
    if ($mongodRunning) {
        Write-Host "mongod já está rodando (PID(s): $($mongodRunning.Id -join ','))."
        return @{ name="mongod"; pids=($mongodRunning.Id) }
    }

    $arg = "--dbpath `"C:\\data\\db`" --bind_ip 127.0.0.1"
    $proc = Start-Process -FilePath $MongoBin -ArgumentList $arg -WindowStyle Minimized -PassThru
    Start-Sleep -Seconds 2
    Write-Host "mongod iniciado (PID: $($proc.Id))."
    return @{ name="mongod"; pids=(@($proc.Id)) }
}

function Start-Backend {
    Write-Host ">> Preparando backend..."
    $backendDir = Join-Path $PSScriptRoot "backend"
    if (-not (Test-Path $backendDir)) { Write-Error "Backend não encontrado."; return $null }

    Push-Location $backendDir
    if (-not (Test-Path ".venv")) {
        Write-Host "Criando virtualenv (.venv)..."
        python -m venv .venv
    }

    $activate = Join-Path $backendDir ".venv\\Scripts\\Activate.ps1"
    if (Test-Path $activate) {
        & $activate
        pip install -r requirements.txt
    }

    $uvicornCmd = ".\\.venv\\Scripts\\Activate.ps1; uvicorn server:app --host 0.0.0.0 --port 8001"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $uvicornCmd -WorkingDirectory $backendDir -PassThru
    Write-Host "Backend iniciado (PID: $($proc.Id)) na porta 8001."
    Pop-Location
    return @{ name="backend"; pids=(@($proc.Id)) }
}

function Start-Frontend {
    Write-Host ">> Preparando frontend..."
    $frontendDir = Join-Path $PSScriptRoot "frontend"
    if (-not (Test-Path $frontendDir)) { Write-Warning "Frontend não encontrado."; return $null }

    Push-Location $frontendDir
    if (-not (Test-Path "node_modules")) {
        Write-Host "Instalando dependências do frontend (yarn install)..."
        yarn install
    }

    $frontCmd = "cd `"$frontendDir`"; yarn dev --host"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $frontCmd -WorkingDirectory $frontendDir -PassThru
    Write-Host "Frontend iniciado (PID: $($proc.Id)) na porta 3000."
    Pop-Location
    return @{ name="frontend"; pids=(@($proc.Id)) }
}

function New-Shortcut {
    if (-not (Test-Path $ShortcutFolder)) { New-Item -ItemType Directory -Path $ShortcutFolder -Force | Out-Null }
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $ps = Join-Path $PSScriptRoot "start_saude_fetch.ps1"
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$ps`""
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.IconLocation = "$MongoBin,0"
    $shortcut.Save()
    Write-Host "Atalho criado em: $ShortcutPath"
}

function Stop-All {
    $p = Get-Pids
    if (-not $p) { Write-Warning "Nenhum PID salvo."; return }
    foreach ($entry in $p) {
        foreach ($procId in $entry.pids) {
            try {
                if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    Write-Host "Parado PID $procId ($($entry.name))"
                }
            } catch {}
        }
    }
    Remove-Item $MetaFile -ErrorAction SilentlyContinue
    Write-Host "Parada completa."
}

if ($Action -eq "stop") {
    Write-Host "Parando saude-fetch..."
    Stop-All
    return
}

$all = @()
$mong = Start-Mongo; if ($mong) { $all += $mong }
$back = Start-Backend; if ($back) { $all += $back }
$front = Start-Frontend; if ($front) { $all += $front }
Save-Pids $all
try { New-Shortcut } catch {}
Write-Host "`nTudo iniciado. Para parar: .\\start_saude_fetch.ps1 stop"
