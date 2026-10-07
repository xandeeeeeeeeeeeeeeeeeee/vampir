$ErrorActionPreference = 'Stop'
$taskTailscale = (Get-Command tailscale -ErrorAction Stop).Source
$taskStatusText = & $taskTailscale status --json
if ($LASTEXITCODE -ne 0) { throw 'Execute este script com acesso ao serviço Tailscale (Administrador, se necessário).' }
$taskStatus = $taskStatusText | ConvertFrom-Json
if ($taskStatus.BackendState -ne 'Running' -or -not $taskStatus.Self.DNSName) {
    throw 'Entre na sua conta pelo aplicativo Tailscale (ou tailscale login) e execute novamente. Nenhuma publicação feita.'
}
$taskDns = $taskStatus.Self.DNSName.TrimEnd('.')
$taskExisting = (& $taskTailscale serve status --json) | ConvertFrom-Json
$taskExisting443 = $taskExisting.TCP.'443'
if ($taskExisting443) {
    $taskExistingProxy = $taskExisting.Web."${taskDns}:443".Handlers.'/'.Proxy
    if ($taskExistingProxy -ne 'http://127.0.0.1:8766') { throw 'Já existe outro Serve na porta 443. Não foi alterado; use uma porta privada separada.' }
}
$taskConfigPath = Join-Path $PSScriptRoot 'config.json'
$taskConfig = Get-Content -LiteralPath $taskConfigPath -Raw | ConvertFrom-Json
$taskConfig.host_remoto = $taskDns
[IO.File]::WriteAllText($taskConfigPath, ($taskConfig | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
# Somente Serve privado. Não utilizar Funnel, nem abrir portas do roteador.
& $taskTailscale serve --bg --yes --https=443 ("http://127.0.0.1:" + $taskConfig.porta)
if ($LASTEXITCODE -ne 0) { throw 'Tailscale Serve não foi configurado. Consulte a mensagem acima; pode ser necessário habilitar HTTPS no painel.' }
Write-Host "Endereço privado: https://$taskDns"
Write-Host 'Reinicie o assistente para carregar o host remoto. Configure os grants conforme ACESSO_PRIVADO.md antes de convidar jogadores.'
