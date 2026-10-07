# Validação da entrega

No projeto de origem, 78 testes automatizados passaram, incluindo edição concorrente, autorização direta na API, revisão, exportação, cancelamento, biblioteca, fichas, mapa e calendário. O ensaio prático real foi preservado fora desta distribuição, com quatro tentativas de ficha (duas recusadas, uma com histórico truncado e reteste final completo). Dados do mestre e credenciais de demonstração não foram incluídos aqui.

Chrome: navegação, fichas completas, mapa público/privado, biblioteca com referências e calendário em computador e celular passaram, sem erros JavaScript. Nenhuma inferência ocorreu nos testes do calendário. A auditoria confirmou o livro e a campanha original de Jorge preservados, dez guias disponíveis e nenhum modelo residente ao concluir.

A cópia distribuída foi verificada separadamente. Resultados estão em VERIFICACAO_PACOTE.json na raiz. Os testes usam biblioteca privada somente em uma pasta de verificação separada; o índice nunca entra no ZIP. MANIFESTO_SHA256.json lista os arquivos entregues, excluindo o próprio manifesto. Mudanças posteriores invalidam os hashes.

Tailscale estava desconectado na origem. Não foi possível validar acesso remoto com jogador; apenas HTTP local e permissões da aplicação. A validação não certifica toda a lore nem cobre perfis de ficha fora do perfil inicial documentado.
