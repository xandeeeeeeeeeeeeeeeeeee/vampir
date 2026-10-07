"""Atlas esquemático: autorização aplicada antes de renderizar ou exportar."""
import html
import uuid
from core import Problem, require_master


def validar(value):
    if not isinstance(value,dict) or not {'tipo','x','y'}<=set(value) or set(value)-{'tipo','x','y','largura','altura','territorio'}:
        raise Problem('Cartografia inválida.')
    if value.get('tipo') not in ['distrito','local']:raise Problem('Escolha distrito ou local no mapa.')
    for key in ['x','y','largura','altura']:
        v=value.get(key,20 if key in ['largura','altura'] else 50)
        if type(v) not in [int,float] or not 0<=v<=100:raise Problem('Coordenada do mapa deve estar entre 0 e 100.')
    if value['tipo']=='distrito' and (value.get('largura',20)<=0 or value.get('altura',20)<=0 or value.get('x',50)+value.get('largura',20)>100 or value.get('y',50)+value.get('altura',20)>100):
        raise Problem('O distrito deve caber dentro do mapa.')
    if not isinstance(value.get('territorio',''),str) or len(value.get('territorio',''))>200:raise Problem('Território inválido.')


def obter(store,user,visao='atual'):
    if visao not in ['atual','jogadores']:raise Problem('Visão do mapa inválida.')
    viewer=user
    if visao=='jogadores':
        require_master(user)
        viewer={'id':'','role':'jogador'}
    items=[r for r in store.records(viewer) if r['kind']=='local' and r['sheet'].get('cartografia')]
    return {'titulo':store.campaign(viewer)['titulo'],'visao':'mestre' if viewer['role']=='mestre' else 'jogadores','esquematico':True,'registros':items}


def svg(data):
    esc=lambda s:html.escape(str(s),quote=True)
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 1000 750" role="img">','<title>'+esc(data['titulo'])+' — '+esc(data['visao'])+'</title>',
           '<rect width="1000" height="750" fill="#111b20"/>','<text x="24" y="32" fill="#e9e4da" font-size="22">'+esc(data['titulo'])+'</text>',
           '<text x="24" y="58" fill="#a6b0b6" font-size="14">Atlas esquemático · '+esc(data['visao'])+'</text>']
    for r in sorted(data['registros'],key=lambda r:r['sheet']['cartografia']['tipo']!='distrito'):
        c=r['sheet']['cartografia'];x=c.get('x',50)*9+40;y=c.get('y',50)*6+90
        parts.append('<g><title>'+esc(r['name']+' — '+r['summary'])+'</title>')
        if c['tipo']=='distrito':
            parts.append(f'<rect x="{x}" y="{y}" width="{c.get("largura",20)*9}" height="{c.get("altura",20)*6}" rx="9" fill="#263630" stroke="#6f916b"/>');x+=10;y+=22
        else:parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#e5b676"/>');x+=12
        parts.append(f'<text x="{x}" y="{y}" fill="#e9e4da" font-size="14">'+esc(r['name'])+'</text></g>')
    return ''.join(parts)+'</svg>'


def exportar(data):
    esc=lambda s:html.escape(str(s),quote=True)
    parts=['<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>'+esc(data['titulo'])+'</title><h1>Atlas da crônica</h1>',
           '<p>Visão: '+esc(data['visao'])+' · Esquemático; posições são editáveis, sem escala geográfica.</p>',svg(data)]
    for r in data['registros']:
        parts.extend(['<section><h2>'+esc(r['name'])+'</h2><p>'+esc(r['summary'])+'</p><pre>'+esc(r['content'])+'</pre>',
                      '<p>Território: '+esc(r['sheet']['cartografia'].get('territorio',''))+'</p>'])
        if data['visao']=='mestre' and r.get('master_notes'):parts.append('<h3>Notas do mestre</h3><pre>'+esc(r['master_notes'])+'</pre>')
        parts.append('</section>')
    return ''.join(parts)+'</html>'


def iniciar(store,user):
    """Cidade fictícia criada explicitamente; IDs estáveis preservam personalizações."""
    require_master(user)
    from core import fresh
    districts=[('Centro Histórico',5,5,28,27,'Praças, prefeitura, museus e arquivos; movimento até tarde.'),
               ('Porto Velho',5,38,28,25,'Docas, armazéns e rotas de carga. Ruas vazias depois da meia-noite.'),
               ('Distrito Financeiro',38,5,26,27,'Torres empresariais, hotéis e vigilância privada.'),
               ('Jardins da Serra',69,5,26,27,'Residências muradas, parques e ruas tranquilas.'),
               ('Vila Operária',38,38,26,25,'Oficinas, prédios populares e terminais noturnos.'),
               ('Cinturão Industrial',69,38,26,25,'Fábricas, terrenos abandonados e vias expressas.')]
    known={r['id'] for r in store.records(user,True)};added=[]
    entries=[(name,'distrito',x,y,w,h,summary,True,'') for name,x,y,w,h,summary in districts]
    entries.extend([
        ('Arquivo Municipal', 'local',15,18,20,20,'Documentos antigos, plantas urbanas e jornais.',True,'Há um acervo fechado e uma rota subterrânea; ideias do mestre, ainda não fatos confirmados.'),
        ('Clube Eclipse','local',48,20,20,20,'Vida noturna e encontros privados.',True,'Possível Elísio. A filiação e o controle ainda são propostas do mestre.'),
        ('Terminal das Docas','local',18,50,20,20,'Cargas, trabalhadores noturnos e acesso ao rio.',True,'Uma futura disputa de domínio pode surgir aqui; planejamento não confirmado.'),
        ('Estação Central','local',48,50,20,20,'Conexões entre bairros e transporte noturno.',True,''),
        ('Hospital Santa Aurora','local',78,20,20,20,'Emergências e plantões durante toda a noite.',True,'Acesso ao banco de sangue não é garantido; avaliar riscos e Máscara.'),
        ('Refúgio Oculto','local',82,53,20,20,'Imóvel fora dos registros públicos da coterie.',False,'Local secreto de preparação do mestre. Revelar por compartilhamento explícito quando descoberto.')])
    for name,kind,x,y,w,h,summary,public,secret in entries:
        id=str(uuid.uuid5(uuid.NAMESPACE_URL,'atelie:santa-aurora:'+name))
        if id in known:continue
        r=fresh('local');r.update(id=id,name=name,summary=summary,state='rascunho',all_players=public,
            content='Santa Aurora — cidade fictícia editável. Este registro é uma proposta de cenário. Anote aqui acessos, horários, contatos conhecidos, rumores e mudanças observadas.',master_notes=secret,
            sheet={'cartografia':{'tipo':kind,'x':x,'y':y,'largura':w,'altura':h,'territorio':'Controle ainda não estabelecido'}})
        store.put(user,r,0);added.append(id)
    return {'criados':added,'cidade':'Santa Aurora','observacao':'Proposta editável; não altera o livro nem confirma acontecimentos.'}
