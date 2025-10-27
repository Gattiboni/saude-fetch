<#
start_saude_fetch.ps1
Uso:
  - Iniciar tudo: .\start_saude_fetch.ps1
  - Parar tudo:   .\start_saude_fetch.ps1 stop
#>

param(
  [string]$Action = "start"
)

$MongoBin = "C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe"
$MetaFile = Join-Path -Path $PSScriptRoot -ChildPath "saude_fetch.pids.json"
$ShortcutFolder = "D:\Backup C 256\Desktop\Gattiboni Enterprises\Lucas Farinazzo"
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
        Write-Error "mongod.exe não encontrado em $MongoBin."
        return $null
    }

    if (-not (Test-Path "C:\data\db")) {
        try { New-Item -ItemType Directory -Path "C:\data\db" -Force | Out-Null } catch {}
    }

    $mongodRunning = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
    if ($mongodRunning) {
        Write-Host "mongod já está rodando (PID: $($mongodRunning.Id -join ','))."
        return @{ name="mongod"; pids=($mongodRunning.Id) }
    }

    $arg = "--dbpath `"C:\data\db`" --bind_ip 127.0.0.1"
    $proc = Start-Process -FilePath $MongoBin -ArgumentList $arg -WindowStyle Minimized -PassThru
    Start-Sleep -Seconds 2
    Write-Host "mongod iniciado (PID: $($proc.Id))."
    return @{ name="mongod"; pids=(@($proc.Id)) }
}

function Start-Backend {
    Write-Host ">> Iniciando backend..."
    $backendDir = Join-Path $PSScriptRoot "backend"
    if (-not (Test-Path $backendDir)) { Write-Error "Backend não encontrado."; return $null }

    Push-Location $backendDir
    if (-not (Test-Path ".venv")) {
        Write-Host "Criando virtualenv..."
        python -m venv .venv
    }

    $activate = Join-Path $backendDir ".venv\Scripts\Activate.ps1"
    if (Test-Path "requirements.txt") {
        & $activate
        pip install -r requirements.txt
        deactivate 2>$null
    }

    $uvicornCmd = ".`\.venv\Scripts\Activate.ps1; uvicorn server:app --host 0.0.0.0 --port 8001"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$uvicornCmd -WorkingDirectory $backendDir -PassThru
    Pop-Location
    Write-Host "Backend iniciado (PID: $($proc.Id))."
    return @{ name="backend"; pids=(@($proc.Id)) }
}

function Start-Frontend {
    Write-Host ">> Iniciando frontend..."
    $frontendDir = Join-Path $PSScriptRoot "frontend"
    if (-not (Test-Path $frontendDir)) { Write-Error "Frontend não encontrado."; return $null }

    Push-Location $frontendDir
    if (-not (Test-Path "node_modules")) {
        Write-Host "Instalando dependências (yarn install)..."
        yarn install
    }

    # Carrega variáveis do .env do frontend
    $envFile = Join-Path $frontendDir ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+)\s*$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($name, $value)
            }
        }
        Write-Host "Variáveis do frontend carregadas a partir de .env"
    }

    $frontCmd = "cd `"$frontendDir`"; yarn dev --host"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$frontCmd -WorkingDirectory $frontendDir -PassThru
    Pop-Location
    Write-Host "Frontend iniciado (PID: $($proc.Id))."
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
    Write-Host ">> Encerrando todos os processos..."
    $p = Get-Pids
    if (-not $p) {
        Write-Warning "Nenhum PID salvo. Tentando encerrar processos conhecidos."
        Get-Process -Name "mongod","node","python","powershell" -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.MainWindowTitle -like "*saude-fetch*" -or $_.Path -like "*saude-fetch*") {
                try { Stop-Process -Id $_.Id -Force } catch {}
            }
        }
        return
    }

    foreach ($entry in $p) {
        foreach ($procId in $entry.pids) {
            try {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "Matando $($entry.name) (PID: $procId)..."
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
    }

    # Fecha todas as janelas PowerShell relacionadas ao saude-fetch
    Get-Process -Name "powershell" -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Path -like "*saude-fetch*") {
            try { Stop-Process -Id $_.Id -Force } catch {}
        }
    }

    Remove-Item $MetaFile -ErrorAction SilentlyContinue
    Write-Host "Parada completa. Todas as janelas de execução foram encerradas."
}

# === fluxo principal ===
if ($Action -eq "stop") {
    Stop-All
    exit
}

$all = @()
$all += Start-Mongo
$all += Start-Backend
$all += Start-Frontend
Save-Pids $all

try { New-Shortcut } catch { Write-Warning "Falha ao criar atalho: $_" }

Write-Host "`nTudo iniciado. Para encerrar: .\start_saude_fetch.ps1 stop"
