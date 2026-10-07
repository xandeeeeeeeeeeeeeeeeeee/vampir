# Acesso privado

O servidor escuta somente 127.0.0.1. Use Tailscale Serve privado com HTTPS após autenticar sua conta. Crie config.json a partir de config.example.json, inicie a aplicação e execute CONFIGURAR_ACESSO_PRIVADO.ps1 nesta pasta. O script exige Tailscale conectado, recusa conflito com outro serviço na porta 443 e grava seu domínio privado na configuração local ignorada pelo Git. Reinicie a aplicação após configurar.

Restrinja os membros convidados ao serviço HTTPS na política da sua rede. Não exponha a porta do Ollama nem o banco. Cada jogador precisa também de sua conta própria na aplicação, criada pelo mestre. A máquina precisa estar ligada. Acesso remoto não foi validado nesta entrega porque a VPN de origem estava desconectada; teste com uma conta de jogador antes de usar fora da máquina.
