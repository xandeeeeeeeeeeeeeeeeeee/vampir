"""Guias editoriais prontos, escritos e conferidos na biblioteca; sem inferência."""
import uuid
from core import fresh, consultar

GUIDES = [
('testes', 'Rolagens V5 — do pedido ao resultado', 'Parada, sucessos, dificuldade e exemplos numéricos.',
['p0120-t001','p0122-t004','p0123-t001'], '''## Teste simples
1. Diga o que pretende alcançar e como age. O narrador escolhe a parada e a dificuldade.
2. Some os valores das características indicadas, normalmente Atributo + Habilidade.
3. Substitua dados comuns por dados de Fome quando aplicável; não aumente a parada.
4. Role d10. Resultados de 6 a 10 contam sucessos. Cada par de 10 vale quatro sucessos, em vez de dois.
5. Compare o total à dificuldade: igualar ou superar vence o teste.

## Leitura rápida
- 1–5: nenhum sucesso comum. Um 1 em dado comum não cancela sucessos.
- 6–9: um sucesso por dado.
- Dois 10: quatro sucessos. Três 10: cinco. Quatro 10: oito.
- Uma vitória que contém um par de 10 é uma vitória crítica. Um par de 10 não garante vitória se a dificuldade ainda não foi alcançada.

## Exemplo
Inteligência 3 + Investigação 2 = cinco dados. Com 3, 6, 7, 10, 10, o total é seis sucessos: dois pelos 6/7 e quatro pelo par de 10. Contra dificuldade 4, é uma vitória crítica.
Disputas, dano, poderes e vitórias automáticas têm regras próprias; consulte a regra específica antes de aplicar este resumo.'''),
('fome', 'Fome, críticos e falhas bestiais', 'Quando os dados vermelhos entram e o que realmente causa um resultado bestial.',
['p0207-t003','p0208-t001','p0209-t001','p0209-t002'], '''## Quantos dados de Fome?
Dados de Fome = o menor valor entre Fome e tamanho da parada. Eles substituem dados comuns.
- Parada 6, Fome 2: quatro dados comuns + dois de Fome.
- Parada 2, Fome 4: dois dados de Fome; continuam sendo dois dados ao todo.
- Não use dados de Fome em Checagens, Força de Vontade ou Humanidade.

## Condições completas
- Crítico bestial: uma VITÓRIA CRÍTICA com pelo menos um 10 em dado de Fome.
- Falha bestial: o teste FALHOU e pelo menos um dado de Fome mostrou 1.
- Um 10 vermelho isolado, sem vitória crítica, não basta para um crítico bestial.
- Um 1 vermelho em um teste vencido não torna o resultado uma falha bestial.
- Dados de Fome nunca são rerrolados com Força de Vontade.

## Exemplo que evita confusão
Um 10 vermelho e um 10 comum formam quatro sucessos. Se bastam para vencer, a vitória crítica é bestial. Se o teste exige cinco e não há outros sucessos, esse par não produz uma vitória crítica. Só haverá falha bestial se existir também um 1 vermelho.

As consequências narrativas são decididas com o narrador segundo as regras. Este resumo não transforma toda falha em frenesi.'''),
('vontade', 'Força de Vontade — consulta rápida', 'Rerrolagens, custo e exceções.',
['p0124-t005','p0160-t003'], '''## Rerrolar
Gaste um ponto de Força de Vontade para rerrolar até três dados comuns elegíveis. Marque o gasto como um ponto de dano Superficial à Força de Vontade, sem dividi-lo pela metade.

## Não pode
- Rerrolar dados de Fome.
- Rerrolar trilhas como Força de Vontade e Humanidade.
- Ignorar exceções explícitas, como Conflitos de Rolagem Única.

## Decisão prática
Confira dificuldade, sucessos e quais dados podem mudar o resultado. Um 10 comum pode ser rerrolado para tentar desfazer um crítico bestial, mas o dado vermelho permanece. Considere o risco de perder a vitória.

## Outros usos
A regra também prevê usos específicos para controlar o personagem por um turno durante frenesi/coerção, fazer movimentos mínimos sob estaca ou ignorar penalidades de Vitalidade por um turno. Consulte as condições do efeito antes de aplicar.'''),
('atributos', 'Criação V5 — atributos e trilhas', 'Distribuição inicial dos nove atributos e valores derivados.',
['p0138-t004','p0146-t005'], '''## Distribuição inicial
- Um atributo com 4.
- Três atributos com 3.
- Quatro atributos com 2.
- Um atributo com 1.
Isso preenche os nove atributos. Não distribua pontos como se fossem um orçamento livre.

## Grupos
Físicos: Força, Destreza, Vigor.
Sociais: Carisma, Manipulação, Autocontrole.
Mentais: Inteligência, Raciocínio, Determinação.

## Trilhas
Vitalidade = Vigor + 3.
Força de Vontade = Autocontrole + Determinação.

## Exemplo original
Um investigador paciente: Força 1; Destreza 2; Vigor 2; Carisma 2; Manipulação 2; Autocontrole 3; Inteligência 3; Raciocínio 3; Determinação 4. Vitalidade 5; Força de Vontade 7.

Este é só o passo de atributos. Clã, disciplinas, predador, especializações, vantagens, defeitos, Convicções, Pilares e escolhas da crônica ainda precisam ser conferidos. O editor aceita fichas parciais.'''),
('habilidades', 'Criação V5 — distribuições de habilidades', 'Três caminhos iniciais, com as contagens prontas.',
['p0138-t005'], '''## Escolha uma distribuição
- Pau pra Toda Obra: uma habilidade com 3, oito com 2, dez com 1.
- Equilibrado: três habilidades com 3, cinco com 2, sete com 1.
- Especialista: uma habilidade com 4, três com 3, três com 2, três com 1.
As demais começam sem pontos. Estes são caminhos alternativos, não pacotes cumulativos.

## Especializações
Confira as especializações gratuitas de Erudição, Ofícios, Performance e Ciência quando essas habilidades têm pontos, além da especialização gratuita adicional. Registre as especializações em notas até haver campo específico.

## Escolher pelo conceito
Distribua primeiro as habilidades que descrevem a vida humana e o papel na coterie. A especialização deve ter escopo específico, combinado com o narrador, em vez de cobrir toda a habilidade.
Escolhas posteriores, como o tipo de predador, podem adicionar características. A distribuição inicial sozinha não certifica uma ficha completa.'''),
('dano', 'Dano e trilhas — como anotar', 'Vitalidade, Força de Vontade e marcas de dano.',
['p0128-t003','p0220-t004'], '''## Identifique a trilha
Ferimentos físicos afetam Vitalidade; pressão e desgaste mental podem afetar Força de Vontade, conforme o efeito.

## Marcas
- Dano Superficial: marque /.
- Dano Agravado: marque X.
- Na aplicação geral, divida o dano Superficial pela metade, arredondando para cima, salvo regra específica em contrário.
- Gastos voluntários, como o uso de Força de Vontade para rerrolar, não são divididos pela metade.
- Trilhas cheias e Debilitação exigem as regras próprias de conversão; não continue somando marcas indefinidamente.

## Recuperação vampírica
A recuperação de dano Superficial à Vitalidade usa Checagem de Sangue; a quantidade recuperada depende da Potência de Sangue. Não use uma quantidade fixa para todos os vampiros.
Mortais, cura de Agravado, fogo, luz solar e poderes possuem regras próprias. Confira o efeito antes de determinar o tipo de dano.'''),
('sangue', 'Checagens de Sangue e despertar', 'O dado único que pode aumentar a Fome.',
['p0213-t002','p0221-t004'], '''## Checagem de Sangue
Role um único dado: 6 ou mais mantém a Fome; falha aumenta a Fome em um.
Essa checagem não recebe dados de Fome. Ela verifica o custo do Sangue, não substitui um teste necessário para executar a ação.

## Quando consultar
Ao despertar à noite, usar Rubor de Vida, Impulso do Sangue, recuperação vampírica ou poderes que exijam a checagem. O custo específico do poder sempre prevalece; não aplique uma checagem genérica a todo efeito.

## Despertar
Ao despertar a cada noite, há uma Checagem de Sangue. Se sua falha elevaria a Fome acima de 5, o vampiro entra em Torpor em vez de testar frenesi de fome.
Despertar durante o dia usa regras de Humanidade e duração próprias; não se resolve apenas com a checagem noturna.

Registre Fome e consequências antes de prosseguir para outra ação, para evitar cobrar o mesmo custo duas vezes.'''),
('interpretacao', 'Roleplay — intenção, vínculo e escolha', 'Um guia pronto para interpretar sem decorar todas as regras.', [], '''## Na sua vez
Diga sua intenção, a ação concreta e o que seu personagem fala. Exemplo: “Quero descobrir se ela mente; pergunto quem pagou o transporte e observo sua reação.” O narrador determina se há teste.

## Três âncoras de interpretação
Desejo: o que quero nesta cena?
Limite: o que não aceito fazer para conseguir?
Vínculo: quem seria afetado pela minha escolha?

## Informação e personagem
Separe o que você leu do que seu personagem descobriu. Pergunte se uma informação é pública, rumor ou conhecimento específico antes de usá-la em cena.

## Cena com outro jogador
Ofereça escolhas e ganchos, sem decidir sentimentos ou ações do personagem alheio. Combine limites para conflito entre personagens. Se uma cena desconforta alguém, interrompa e ajuste com o grupo.

Guia editorial de interpretação, não regra mecânica do livro.'''),
('planejamento', 'Sessões — preparar escolhas e consequências', 'Estrutura prática para preparar uma noite sem impor um roteiro.', [], '''## Preparação de uma sessão
Defina um conflito imediato, dois ou três envolvidos com objetivos incompatíveis e uma consequência caso ninguém intervenha.
Para cada pista importante, prepare formas distintas de descobri-la: testemunha, evidência e documento. Um único teste fracassado não precisa encerrar toda a investigação.

## Três caminhos
Negociar: o que cada lado pode oferecer e qual preço exige?
Investigar: que prova muda a decisão e quem a esconde?
Confrontar: o que pode ser perdido, mesmo vencendo?
São possibilidades; os jogadores podem escolher um quarto caminho.

## NPC em cinco linhas
Objetivo concreto; medo; recurso; relação; atitude se pressionado. Uma dívida útil tem credor, valor/objeto, prazo e consequência, em vez de apenas “ele deve algo”.

## Após a sessão
Confirme o que ocorreu. Atualize posições, relações e pendências. Mantenha alternativas não escolhidas como alternativas, sem narrá-las como fatos.
Método editorial de preparação, não cânone publicado.'''),
('atelie', 'Ateliê — fichas, IA e materiais', 'Como usar o assistente e encontrar suas referências prontas.', [], '''## Onde encontrar
Personagens: cards e fichas. Sessões: materiais e cheat sheets prontos. Biblioteca: busca no livro, sem carregar a IA. Conversa: pedidos de criação, pesquisa e planejamento.

## Usar a IA
Selecione registros relevantes, escolha a ferramenta e envie seu pedido. Gemma 12B serve ao trabalho comum; Gemma 26B é uma escolha explícita para trabalho extenso. Há uma geração por vez entre os participantes; o modelo é liberado ao terminar.

## Propostas
A resposta não muda a campanha sozinha. Revise e aceite fichas, notas e cheat sheets pessoais. Propostas sobre o mundo compartilhado são decididas pelo mestre.
Conversas são individuais. A IA de um jogador recebe somente os registros que ele pode consultar.

## Materiais prontos
Estes guias foram escritos e disponibilizados no sistema. Não é necessário pedir à IA para criá-los. Você pode exportar Markdown/HTML ou pedir uma versão pessoal adaptada à sua ficha.
Ao editar, respeite as fontes e diferencie regra oficial de regra da casa. Segredos ficam nos campos privados.''')
]

LEGACY_GUIDE=next(body.strip() for slug,_,_,_,body in GUIDES if slug=='atelie')
GUIDE_REPLACEMENTS=[
('Conversa: pedidos de criação, pesquisa e planejamento.',
 'Conversa: o mestre cria e planeja; jogadores consultam regras, preparam sua ficha e exploram a interpretação.'),
('Gemma 12B serve ao trabalho comum; Gemma 26B é uma escolha explícita para trabalho extenso.',
 'Jogadores usam apenas Gemma 12B, com até quatro fichas/materiais pessoais ou referências de regras. O mestre também pode escolher Gemma 26B, planejar sessões e analisar continuidade.'),
('Propostas sobre o mundo compartilhado são decididas pelo mestre.',
 'Somente o mestre gera propostas sobre o mundo compartilhado. Na IA dos jogadores, apenas o modo de ficha pode propor materiais pessoais; consulta e interpretação não alteram documentos.'),
('A IA de um jogador recebe somente os registros que ele pode consultar.',
 'A IA de um jogador recebe apenas suas fichas/notas, guias e regras liberadas. Não recebe NPCs, sessões ou tramas da campanha e não decide cenas, rolagens ou reações do mundo.')]
updated_guide=LEGACY_GUIDE
for old,new in GUIDE_REPLACEMENTS:updated_guide=updated_guide.replace(old,new)
GUIDES=[(slug,title,summary,sources,updated_guide if slug=='atelie' else body)
        for slug,title,summary,sources,body in GUIDES]


def atualizar_guia_uso(store):
    """Explicit editorial update; leave customizations and archives untouched."""
    actor={'id':'catalogo-editorial','role':'mestre'}
    identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,'atelie-rpg/guias/v1/atelie'))
    record=next((r for r in store.records(actor,True) if r['id']==identifier),None)
    if not record or record['archived'] or record['content']!=LEGACY_GUIDE:return False
    record['content']=updated_guide
    store.put(actor,record,record['version'])
    return True


def ids_catalogo():
    return {str(uuid.uuid5(uuid.NAMESPACE_URL,'atelie-rpg/guias/v1/'+slug)) for slug,*_ in GUIDES}


def instalar(store):
    actor={'id':'catalogo-editorial','role':'mestre'}
    existing={r['id'] for r in store.records(actor, True)}
    created=[]
    for slug, title, summary, sources, body in GUIDES:
        record=fresh('cheat_sheet')
        record['id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'atelie-rpg/guias/v1/'+slug))
        if record['id'] in existing:
            continue  # Nunca sobrescreve personalizações ou material arquivado.
        references=[]
        for source_id in sources:
            source=consultar.obter(source_id)[0]
            references.append(f"- {source['titulo']} — página PDF {source['pagina_pdf']}, ID {source_id}")
        record.update(name=title,summary=summary,origin='adaptacao' if sources else 'criacao',
                      state='confirmado',all_players=True,sources=sources,
                      content=body.strip()+('\n\n## Referências do livro\n'+'\n'.join(references) if references else ''),
                      sheet={'papel':'Guia editorial pronto'})
        store.put(actor,record,0)
        created.append(record['id'])
    return created


if __name__=='__main__':
    from core import Store,ROOT
    print('Materiais adicionados:',len(instalar(Store(ROOT/'dados'))))
