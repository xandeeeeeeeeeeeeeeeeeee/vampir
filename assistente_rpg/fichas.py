"""Criação inicial completa e verificável para Crianças da Noite do livro básico.

Escolhas padrão são propostas editáveis, nunca fatos da campanha ou regras novas.
"""
import copy
import re
from core import ATTRS, SKILLS, Problem, consultar
from core import fresh

CLANS={
 'Brujah':('Celeridade','Potência','p0069-t007'),
 'Gangrel':('Proteanismo','Animalismo','p0075-t002'),
 'Malkavian':('Auspícios','Ofuscação','p0081-t005'),
 'Nosferatu':('Ofuscação','Animalismo','p0087-t002'),
 'Toreador':('Auspícios','Presença','p0093-t002'),
 'Tremere':('Auspícios','Dominação','p0099-t005'),
 'Ventrue':('Dominação','Presença','p0104-t004')}
POWERS={
 'Auspícios':[('Sentidos Aguçados','p0251-t004'),('Sentir o Invisível','p0251-t005')],
 'Ofuscação':[('Manto de Sombras','p0263-t003'),('Silêncio da Morte','p0263-t004')],
 'Dominação':[('Compelir','p0258-t003'),('Nublar Memória','p0258-t004')],
 'Presença':[('Fascínio','p0268-t005'),('Amedrontar','p0268-t004')],
 'Celeridade':[('Graça Felina','p0254-t005'),('Reflexos Rápidos','p0254-t006')],
 'Potência':[('Corpo Letal','p0266-t003'),('Salto Vertiginoso','p0266-t004')],
 'Proteanismo':[('Olhos da Besta','p0271-t004'),('Peso Pena','p0271-t005')],
 'Animalismo':[('Sentir a Besta','p0247-t005'),('Famulus Enlaçado','p0247-t004')]}
BASE_SOURCES=['p0218-t001','p0138-t004','p0138-t005','p0138-t006','p0139-t002','p0139-t003','p0151-t006','p0152-t001','p0187-t003','p0189-t003','p0195-t003','p0186-t003','p0187-t001']


def completa(question):
    q=consultar.normalizar(question)
    return bool(re.search(r'(?:crie|criar|monte|montar|gere|gerar|complete|completar).{0,60}\bficha\b',q)) and not any(x in q for x in ['parcial','preencha apenas','so atributos','somente atributos'])


def perfil(question,sheet=None):
    q=consultar.normalizar(question);sheet=sheet or {}
    if any(x in q for x in ['ancilla','neofito','sangue-ralo','sangue ralo','caitiff']):
        raise Problem('A criação completa automática cobre Crianças da Noite dos sete clãs básicos. Para outro perfil, peça uma ficha parcial com o perfil explícito; não será apresentada como completa.')
    clan=next((c for c in CLANS if consultar.normalizar(c) in q),sheet.get('cla') or 'Malkavian')
    if clan not in CLANS:raise Problem('Clã sem pacote inicial validado: '+str(clan))
    return clan


def modelo(question,clan):
    tech=any(w in consultar.normalizar(question) for w in ['software','tecnologia','programador','desenvolvedor'])
    ranked=(['Tecnologia','Investigação','Percepção','Ciência','Erudição','Ofícios','Furtividade','Empatia','Manha','Subterfúgio','Persuasão','Etiqueta','Atletismo','Condução','Ocultismo'] if tech else
            ['Percepção','Empatia','Persuasão','Investigação','Manha','Furtividade','Subterfúgio','Etiqueta','Tecnologia','Erudição','Atletismo','Briga','Condução','Ocultismo','Performance'])
    skills={k:0 for k in SKILLS}
    for i,k in enumerate(ranked):skills[k]=3 if i<3 else 2 if i<8 else 1
    attrs=dict(zip(ATTRS,[1,2,2,2,2,3,4,3,3]))
    primary,secondary,bane=CLANS[clan]
    powers=[{'disciplina':d,'nome':n,'nivel':1,'fonte':ref} for d,num in [(primary,2),(secondary,1)] for n,ref in POWERS[d][:num]]
    specialties={k:['Pesquisa' if k=='Erudição' else 'Matemática' if k=='Ciência' else 'Reparos' if k=='Ofícios' else 'Teatro'] for k in ['Erudição','Ciência','Ofícios','Performance'] if skills[k]>0}
    specialties.setdefault('Tecnologia' if tech else 'Percepção',[]).append('Programação' if tech else 'Vigilância')
    creation={'perfil':'crianca','geracao':13,'experiencia':0,'distribuicao':'equilibrado',
              'predador':'Não se aplica: recém-abraçado, ainda sem método habitual de caça.',
              'especializacoes':specialties,'poderes':powers,
              'vantagens':[{'nome':'Contatos','pontos':3,'descricao':'Um especialista humano em segurança de sistemas; vínculo proposto, não NPC confirmado.','fonte':'p0187-t003'},
                            {'nome':'Recursos','pontos':2,'descricao':'Poupança e apartamento da vida humana; classe média.','fonte':'p0195-t003'},
                            {'nome':'Refúgio','pontos':2,'descricao':'Apartamento privado com cômodo interno protegido da luz solar.','fonte':'p0189-t003'}],
              'defeitos':[{'nome':'Inimigos','pontos':2,'descricao':'Um mortal Mortífero (Efetividade 4), antigo rival profissional, quer arruinar sua vida. É uma proposta pessoal para aprovação do mestre.','fonte':'p0186-t003'}],
              'conviccoes':[{'texto':'Não sacrificar inocentes para proteger meus interesses.','pilar':'Lia, amiga humana que ajudou alguém mesmo sob risco pessoal; vínculo proposto.'}],
              'ambicao':'Preservar a própria autonomia enquanto entende a sociedade vampírica.',
              'desejo':'Encontrar uma pessoa confiável nesta noite.',
              'senhor':'Identidade desconhecida pelo personagem; mistério intencional proposto para o prelúdio.',
              'aparencia':'Aparência de adulto de 30 anos; roupas comuns da vida humana.',
              'perdicao':consultar.obter(bane)[0]['texto'],
              'detalhe_perdicao':('Sob o efeito da Perdição, padrões e coincidências dominam sua interpretação das coisas; as penalidades seguem a fonte do clã.' if clan=='Malkavian' else
                                 'Preferência alimentar por mortais que trabalham em tecnologia.' if clan=='Ventrue' else
                                 'Deformidades visíveis; Repulsivo da Perdição é adicional e não conta nos dois pontos de Defeitos escolhidos.' if clan=='Nosferatu' else
                                 'Aplicar a Perdição do clã descrita acima; manifestações narrativas seguem essa regra.'),
              'escolhas_assumidas':'Proposta inicial: Criança da Noite, 13ª geração, sem XP extra, distribuição equilibrada; Fome 1 é condição inicial proposta, não regra fixa. Poderes de nível 1 são escolhas permitidas, inclusive os dois de uma Disciplina com 2 pontos. Todos os vínculos, recursos, ambições e descrições podem ser alterados antes de aceitar. Princípios da crônica e coterie são escolhas coletivas do mestre.'}
    return {'cla':clan,'conceito':'Investigar o mundo noturno preservando os laços humanos.',
            'atributos':attrs,'habilidades':skills,'disciplinas':{primary:2,secondary:1},
            'recursos':{'humanidade':7,'potencia_sangue':1,'gravidade_perdicao':2,'fome':1,'vitalidade':5,'forca_vontade':6,'dano_superficial':0,'dano_agravado':0},
            'historico':'Vida humana interrompida pelo Abraço recente. Busca entender o que mudou e proteger seus vínculos.','criacao':creation}


def finalizar(answer,question):
    answer=copy.deepcopy(answer)
    for p in answer.get('propostas',[]):
        r=p.get('registro',{})
        if r.get('kind')!='personagem':continue
        if p.get('alvo'):
            p['registro']=completar_existente(r)
            continue
        s=r.setdefault('sheet',{});base=modelo(question,perfil(question,s));assumed=[]
        for k,v in base.items():
            if k in ['atributos','habilidades','disciplinas','recursos','criacao'] or not s.get(k):
                s[k]=copy.deepcopy(v);assumed.append(k)
        if assumed:s['criacao']['escolhas_assumidas']+=' Campos completados pelo pacote local: '+', '.join(assumed)+'.'
        validar(s)
        ids=fontes(s)
        r['sources']=list(dict.fromkeys(r.get('sources',[])+ids))
        r['content']='Criação inicial completa para o perfil Criança da Noite. As estatísticas são calculadas pelo pacote local documentado, não pela prosa do modelo. Escolhas pessoais são propostas; aprovação não confirma NPCs ou fatos do mundo. Veja o histórico e todas as etapas nos campos da ficha.'
    if not any(p.get('registro',{}).get('kind')=='personagem' for p in answer.get('propostas',[])):
        raise Problem('O pedido exige uma ficha completa em uma proposta personagem, não apenas uma descrição.')
    return answer


def da_persona(persona,question,records,selection):
    if not isinstance(persona,dict) or any(not isinstance(persona.get(k),str) or not persona[k].strip() for k in ['nome','conceito','historico']):
        raise Problem('A IA precisa fornecer nome, conceito e histórico pessoal; nenhum rascunho vazio será salvo.')
    if len(persona['historico'].split())<40 or not re.search(r'[.!?][\"”\']?\s*$',persona['historico']):
        raise Problem('Histórico incompleto: escreva ao menos 40 palavras, com frases completas, sem terminar no meio de uma frase.')
    selected=[r for r in records if r['id'] in selection and r['kind']=='personagem']
    edit=bool(re.search(r'\bcomplet(?:e|ar)\b',consultar.normalizar(question)))
    current=selected[0] if edit and len(selected)==1 else None
    r=copy.deepcopy(current) if current else fresh('personagem')
    r.update(name=persona['nome'],summary=persona['conceito'])
    r['sheet'].update(cla=perfil(question,(current or {}).get('sheet')),conceito=persona['conceito'],historico=persona['historico'])
    return {'resposta':'Ficha completa proposta com histórico criado pela IA e mecânica montada pelo pacote local verificado. Confira as escolhas assumidas.',
            'fontes':[],'propostas':[{'alvo':current['id'] if current else '', 'versao':current['version'] if current else 0,
                                     'motivo':'Criação inicial completa para revisão; as escolhas mecânicas vêm do pacote local.', 'registro':r}]}


def completar_existente(record):
    """Completa campos ausentes preservando escolhas iniciais compatíveis."""
    r=copy.deepcopy(record);old=r['sheet'];base=modelo(r['summary']+' '+old.get('conceito',''),perfil('',old))
    attrs=old.get('atributos',{})
    remaining=[1,2,2,2,2,3,3,3,4]
    for value in attrs.values():
        if type(value) is not int or value not in remaining:raise Problem('Atributos existentes não cabem no orçamento inicial. Revise antes de completar.')
        remaining.remove(value)
    a=dict(attrs)
    for key,wanted in base['atributos'].items():
        if key not in a:
            value=wanted if wanted in remaining else remaining[0];a[key]=value;remaining.remove(value)
    budget={1:7,2:5,3:3};skills={key:0 for key in SKILLS}
    for key,value in old.get('habilidades',{}).items():
        if value:
            if key not in skills or type(value) is not int or value not in budget or budget[value]==0:raise Problem('Habilidades existentes não cabem no perfil equilibrado; precisam de revisão explícita.')
            skills[key]=value;budget[value]-=1
    ordered=sorted(SKILLS,key=lambda key:base['habilidades'][key],reverse=True)
    for value in [3,2,1]:
        for key in ordered:
            if budget[value] and not skills[key]:skills[key]=value;budget[value]-=1
    base.update(atributos=a,habilidades=skills)
    for key in ['conceito','historico','notas','notas_mestre','papel','condicoes']:
        if old.get(key):base[key]=old[key]
    base['recursos']['vitalidade']=a['Vigor']+3;base['recursos']['forca_vontade']=a['Autocontrole']+a['Determinação']
    for key in ['fome','dano_superficial','dano_agravado']:
        if key in old.get('recursos',{}):base['recursos'][key]=old['recursos'][key]
    c=base['criacao'];c['especializacoes']={k:['Pesquisa' if k=='Erudição' else 'Matemática' if k=='Ciência' else 'Reparos' if k=='Ofícios' else 'Teatro'] for k in ['Erudição','Ciência','Ofícios','Performance'] if skills[k]}
    extra=next(k for k in ordered if skills[k]);c['especializacoes'].setdefault(extra,[]).append('Aplicação profissional')
    c['escolhas_assumidas']+=' Complemento da ficha existente: atributos já informados e habilidades com pontos foram preservados; novas escolhas exigem revisão. Históricos e notas anteriores permanecem no registro.'
    r['sheet']=base;r['sources']=list(dict.fromkeys(r.get('sources',[])+fontes(base)));validar(base)
    return r


def fontes(s):
    c=s['criacao'];ids=BASE_SOURCES+[CLANS[s['cla']][2]]+[p['fonte'] for p in c['poderes']]+[v['fonte'] for v in c['vantagens']+c['defeitos']]
    for id in ids:consultar.obter(id)
    return list(dict.fromkeys(ids))


def validar(s):
    c=s.get('criacao')
    if not isinstance(c,dict):raise Problem('Faltam etapas estruturadas da criação completa.')
    if {'perfil','geracao','experiencia','distribuicao','predador','especializacoes','poderes','vantagens','defeitos','conviccoes','ambicao','desejo','senhor','aparencia','perdicao','detalhe_perdicao','escolhas_assumidas'}!=set(c):
        raise Problem('Faltam campos da criação completa.')
    if c['perfil']!='crianca' or c['geracao'] not in [12,13] or type(c['geracao']) is not int or c['experiencia']!=0 or type(c['experiencia']) is not int:raise Problem('Perfil inicial sem XP precisa de Criança da Noite de 12ª ou 13ª geração.')
    if s.get('cla') not in CLANS:raise Problem('Clã sem pacote validado.')
    if set(s.get('atributos',{}))!=set(ATTRS) or sorted(s['atributos'].values())!=[1,2,2,2,2,3,3,3,4]:raise Problem('Distribuição dos nove atributos iniciais incompleta ou inválida.')
    if set(s.get('habilidades',{}))!=set(SKILLS):raise Problem('Registre as 27 habilidades, inclusive as que têm zero.')
    values=sorted(v for v in s['habilidades'].values() if v)
    if values!=[1]*7+[2]*5+[3]*3 or c['distribuicao']!='equilibrado':raise Problem('Pacote completo exige distribuição equilibrada: 3×3, 5×2 e 7×1.')
    ds=s.get('disciplinas',{});allowed=set(CLANS[s['cla']][:2])
    # Este pacote usa as duas disciplinas publicadas selecionadas; outras escolhas exigem revisão explícita.
    if set(ds)!=allowed or sorted(ds.values())!=[1,2]:raise Problem('Disciplinas iniciais: duas do pacote de clã, com 2 e 1 pontos.')
    r=s.get('recursos',{})
    if r.get('vitalidade')!=s['atributos']['Vigor']+3 or r.get('forca_vontade')!=s['atributos']['Autocontrole']+s['atributos']['Determinação']:raise Problem('Trilhas derivadas não conferem.')
    if r.get('humanidade')!=7 or r.get('potencia_sangue')!=1 or r.get('gravidade_perdicao')!=2 or not {'fome','dano_superficial','dano_agravado'}<=set(r):raise Problem('Recursos iniciais incompletos.')
    specs=c['especializacoes']
    if not isinstance(specs,dict) or any(k not in SKILLS or not s['habilidades'][k] or not isinstance(v,list) or not v or any(not isinstance(t,str) or not t.strip() for t in v) for k,v in specs.items()):raise Problem('Especializações inválidas.')
    mandatory=[k for k in ['Erudição','Ofícios','Performance','Ciência'] if s['habilidades'][k]>0]
    if any(k not in specs for k in mandatory) or sum(len(v) for v in specs.values())!=len(mandatory)+1:raise Problem('Faltam especializações gratuitas, inclusive a adicional.')
    powers=c['poderes']
    if not isinstance(powers,list) or len(powers)!=3:raise Problem('Escolha um poder por ponto de Disciplina.')
    for d,count in ds.items():
        ps=[p for p in powers if p.get('disciplina')==d]
        if len(ps)!=count or len({p.get('nome') for p in ps})!=count or any((p.get('nome'),p.get('fonte')) not in POWERS[d] or p.get('nivel')!=1 for p in ps):raise Problem('Poderes devem corresponder ao catálogo inicial documentado.')
    for field,total in [('vantagens',7),('defeitos',2)]:
        entries=c[field]
        if not isinstance(entries,list) or any(not isinstance(v,dict) or type(v.get('pontos')) is not int or v['pontos']<=0 or not v.get('nome') or not v.get('descricao') or not v.get('fonte') for v in entries) or sum(v['pontos'] for v in entries)!=total:raise Problem('Distribuição incompleta de '+field)
        approved={'Contatos':'p0187-t003','Recursos':'p0195-t003','Refúgio':'p0189-t003'} if field=='vantagens' else {'Inimigos':'p0186-t003'}
        if len({v['nome'] for v in entries})!=len(entries) or any(approved.get(v['nome'])!=v['fonte'] or v['pontos']>({'Contatos':3,'Recursos':5,'Refúgio':5,'Inimigos':2}[v['nome']]) for v in entries):raise Problem('Use as vantagens/defeitos documentados do pacote inicial.')
    convictions=c['conviccoes']
    if not isinstance(convictions,list) or not 1<=len(convictions)<=3 or any(not isinstance(v,dict) or not isinstance(v.get('texto'),str) or not v['texto'].strip() or not isinstance(v.get('pilar'),str) or not v['pilar'].strip() for v in convictions):raise Problem('Cada Convicção exige um Pilar humano descrito.')
    for k in ['predador','ambicao','desejo','senhor','aparencia','perdicao','detalhe_perdicao','escolhas_assumidas']:
        if not isinstance(c[k],str) or not c[k].strip():raise Problem('Campo obrigatório: '+k)
    if not s.get('historico') or not s.get('conceito'):raise Problem('Histórico e conceito são obrigatórios.')
    fontes(s)
