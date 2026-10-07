$ErrorActionPreference = 'Stop'
$taskPidPath = Join-Path $PSScriptRoot 'assistente_rpg\servidor.pid'
if (Test-Path -LiteralPath $taskPidPath) {
    $taskPid = [int](Get-Content -LiteralPath $taskPidPath)
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $taskPid"
    $taskServer = Join-Path $PSScriptRoot 'assistente_rpg\servidor.py'
    if ($taskProcess -and $taskProcess.Name -eq 'python.exe' -and $taskProcess.CommandLine.Contains($taskServer)) {
        Stop-Process -Id $taskPid
    } elseif ($taskProcess) { throw 'O PID não corresponde ao assistente; nenhum processo encerrado.' }
}
Write-Host 'Servidor do assistente encerrado. Documentos confirmados permanecem salvos.'
