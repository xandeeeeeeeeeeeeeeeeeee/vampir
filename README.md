# Ateliê da Crônica

Assistente local para planejar campanhas de Vampiro: A Máscara V5 em conjunto. Python, SQLite e interface web responsiva, sem dependências Python externas. O modelo só trabalha quando alguém envia um pedido.

## Conteúdo

- Registros vinculados de personagens, NPCs, lugares, facções, sessões, acontecimentos, segredos e regras da casa.
- Fontes publicadas separadas de adaptações, rumores, propostas, planejamento e fatos confirmados.
- Propostas de IA com revisão e aceitação, histórico, arquivamento, restauração e detecção de conflitos.
- Fichas, cards e exportações Markdown/HTML; dez cheat sheets editoriais instalados pelo sistema.
- Cidade fictícia editável com distritos e notas públicas/privadas; calendário interativo com referências.
- Biblioteca com seções completas, páginas clicáveis e navegação entre referências.
- Contas individuais e filtros no servidor. Jogadores usam IA para regras, ficha própria e interpretação pessoal; planejamento integral e segredos são do mestre.

## Instalação local

Use Python 3.11 ou superior com SQLite/FTS5. A distribuição contém somente código: campanhas, contas, livro e modelos precisam ficar na máquina do proprietário.

1. Copie este projeto para sua máquina.
2. Importe explicitamente sua biblioteca V5 já indexada e compatível: `python IMPORTAR_BIBLIOTECA.py "CAMINHO/base_mestre_rpg"`. O arquivo original do livro permanece separado. Um PDF bruto não é aceito por este importador; ele utiliza o índice revisado com os IDs verificados pela aplicação.
3. No Windows, execute `INICIAR_ASSISTENTE.cmd`. O script cria a configuração local a partir do exemplo. Em outros sistemas, copie `assistente_rpg/config.example.json` para `assistente_rpg/config.json` e execute `python assistente_rpg/servidor.py`.
4. Abra http://127.0.0.1:8766 e crie a conta do mestre. Crie contas de jogadores pela administração. Nenhuma conta ou senha vem instalada.
5. Para usar IA, inicie seu Ollama local com os modelos configurados. A edição de registros e consulta do livro funcionam com Ollama desligado.

Configuração testada: `gemma4:12b-it-qat` para conversa e tarefas pequenas; `gemma4:26b-a4b-it-qat` como opção explícita do mestre para trabalho extenso. Não há download automático. Apenas um pedido por vez; o modelo é descarregado ao concluir. Ajuste as opções na configuração local, que não deve ser versionada.

`PARAR_ASSISTENTE.ps1` encerra apenas o servidor identificado pelo seu PID. Não apaga documentos. Backup e importação de campanhas estão em `assistente_rpg/administrar.py`; a importação é explícita e exige campanha vazia e snapshot da origem.

## Fichas e qualidade

Criação completa suportada: Crianças da Noite de 12ª/13ª geração, sem XP adicional, sete clãs básicos e distribuição equilibrada de habilidades. A IA escreve o histórico; a mecânica vem do pacote local validado e tem referências verificáveis. Vínculos, antecedentes, Fome inicial e escolhas pessoais são propostas editáveis. Outros perfis exigem edição manual ou solicitação parcial. Não há garantia de ausência de toda contradição narrativa: revise propostas antes de confirmar.

Na máquina de origem (Ryzen 5 5500, RX 6600 8 GB, aproximadamente 16 GB de RAM), os retestes finais de ficha levaram cerca de 51 e 57 segundos. Tentativas anteriores falharam e motivaram a separação entre narrativa e mecânica. O 26B teve medições históricas muito mais lentas; esta versão não afirma que seja superior por ser maior. Veja VALIDACAO.md.

## Testes

Sem biblioteca, entre na pasta assistente_rpg e execute `python -m unittest test_assistente.DataTests -v` para os testes de dados independentes do livro. Após importar o índice compatível, execute `python -m unittest discover -s assistente_rpg -p "test*.py" -v`. Os testes de IA usam servidor simulado; não carregam modelos reais.

As datas do calendário são fictícias e não executam automações. Mestre tem prévia do conteúdo liberado a todos; cada jogador também vê seus materiais e notas autorizados. O mapa inicial só é instalado ao escolher a ação correspondente na interface.

## Acesso remoto e publicação

Consulte assistente_rpg/ACESSO_PRIVADO.md para HTTPS privado por Tailscale. Ollama e SQLite permanecem locais. Acesso remoto ainda precisa de validação com uma conta de jogador na rede configurada.

Antes de enviar ao GitHub, mantenha o .gitignore e confira `git status`. Não adicione configuração local, índices do livro, bancos, backups, credenciais ou logs com `git add -f`. Esta entrega prepara os arquivos; não cria nem publica um repositório remoto. Nenhuma licença de redistribuição foi escolhida nesta entrega.
