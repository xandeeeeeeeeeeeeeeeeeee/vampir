"""Calendário de datas fictícias; nenhuma inferência ou agendamento automático."""
import calendar
import datetime
import html
import re
from core import Problem, require_master


def obter(store,user,mes,visao='atual'):
    if not isinstance(mes,str) or not re.fullmatch(r'\d{4}-\d{2}',mes):raise Problem('Escolha um mês no formato AAAA-MM.')
    year,month=map(int,mes.split('-'))
    if not 1<=year<=9999 or not 1<=month<=12:raise Problem('Mês inválido.')
    if visao not in ['atual','jogadores']:raise Problem('Visão inválida.')
    viewer=user
    if visao=='jogadores':require_master(user);viewer={'id':'','role':'jogador'}
    records=store.records(viewer);visible={r['id']:r for r in records};entries=[];undated=[]
    for r in records:
        if r['kind'] not in ['sessao','acontecimento','trama','nota']:continue
        match=re.match(r'^(\d{4}-\d{2}-\d{2})(?:$|\s|T)',r['date'])
        day=None
        if match:
            try:day=datetime.date.fromisoformat(match[1])
            except ValueError:pass
        if not day:undated.append(r);continue
        if day.strftime('%Y-%m')!=mes:continue
        references=[{'id':id,'nome':visible[id]['name'],'registro':visible[id]} for id in r['links'] if id in visible]
        entries.append({'dia':day.day,'data':day.isoformat(),'registro':r,'referencias':references})
    first,days=calendar.monthrange(year,month)
    return {'mes':mes,'primeiro_dia':first,'dias':days,'titulo':store.campaign(viewer)['titulo'],
            'visao':'mestre' if viewer['role']=='mestre' else 'jogadores',
            'eventos':sorted(entries,key=lambda e:(e['data'],e['registro']['date'],e['registro']['name'])),'sem_data':undated}


def exportar(data):
    esc=lambda t:html.escape(str(t),quote=True)
    parts=['<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Calendário da crônica</title><h1>'+esc(data['titulo'])+'</h1>',
           '<p>'+esc(data['mes'])+' · visão '+esc(data['visao'])+' · datas do mundo da campanha</p>']
    for entry in data['eventos']:
        r=entry['registro'];parts.extend(['<section id="registro-'+esc(r['id'])+'"><h2>'+esc(r['date']+' — '+r['name'])+'</h2>',
            '<p>'+esc(r['kind']+' · '+r['state'])+'</p><p>'+esc(r['summary'])+'</p><pre>'+esc(r['content'])+'</pre>',
            '<p>Referências: '+', '.join(esc(ref['nome']) for ref in entry['referencias'])+'</p>'])
        if data['visao']=='mestre' and r.get('master_notes'):parts.append('<h3>Notas do mestre</h3><pre>'+esc(r['master_notes'])+'</pre>')
        parts.append('</section>')
    return ''.join(parts)+'</html>'
