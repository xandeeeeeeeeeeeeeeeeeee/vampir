param([switch]$SemAbrir)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskApp = Join-Path $taskRoot 'assistente_rpg'
if (-not (Test-Path -LiteralPath (Join-Path $taskApp 'config.json'))) { Copy-Item -LiteralPath (Join-Path $taskApp 'config.example.json') -Destination (Join-Path $taskApp 'config.json') }
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'base_mestre_rpg\busca\livro.sqlite3'))) { throw 'Importe sua biblioteca local primeiro: python IMPORTAR_BIBLIOTECA.py CAMINHO_BASE_MESTRE_RPG' }
$taskConfig = Get-Content -LiteralPath (Join-Path $taskApp 'config.json') -Raw | ConvertFrom-Json
$taskPython = (Get-Command python -ErrorAction Stop).Source
$taskAddress = 'http://127.0.0.1:' + $taskConfig.porta
try { $taskHealth = Invoke-RestMethod ($taskAddress + '/api/status') -TimeoutSec 2 }
catch {
    $env:PYTHONIOENCODING = 'utf-8'
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-u', ('"' + (Join-Path $taskApp 'servidor.py') + '"')) -WorkingDirectory $taskApp -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskApp 'servidor.stdout.log') -RedirectStandardError (Join-Path $taskApp 'servidor.stderr.log') -PassThru
    $taskProcess.Id | Set-Content -LiteralPath (Join-Path $taskApp 'servidor.pid')
    Start-Sleep -Seconds 2
    $taskHealth = Invoke-RestMethod ($taskAddress + '/api/status') -TimeoutSec 5
}
Write-Host "Assistente disponível em $taskAddress. IA sob demanda; nenhum modelo iniciado."
if (-not $SemAbrir) { Start-Process $taskAddress }
