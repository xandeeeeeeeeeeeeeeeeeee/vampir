"""Leitura contextual do índice existente. Fonte e índice permanecem somente leitura."""
import copy
from functools import lru_cache
import json
import re
from core import consultar


@lru_cache(maxsize=1)
def catalogo():
    db=consultar.conexao()
    try:
        return [json.loads(row[0]) for row in db.execute('SELECT dados FROM trechos ORDER BY rowid')]
    finally:
        db.close()


def caminho(record):
    return tuple(record.get('contexto') or [record['categoria'],record['titulo']])


def intervalo(index, prefix):
    rows=catalogo()
    def belongs(record):
        path=caminho(record)
        if path[:len(prefix)]==prefix:
            return True
        # Some continuation paragraphs lost a heading at a page break in the
        # existing index. Include them until the next explicit peer section.
        return (prefix[:len(path)]==path and not re.match(r'^\s*#{1,6}\s',record['texto']))
    left=right=index
    while left>0 and belongs(rows[left-1]):left-=1
    while right+1<len(rows) and belongs(rows[right+1]):right+=1
    return rows[left:right+1]


def contexto(identifier, escopo='secao'):
    if escopo not in ['secao','capitulo','topico']:
        raise ValueError('Escopo inválido.')
    rows=catalogo()
    index=next((i for i,r in enumerate(rows) if r['id']==identifier),None)
    if index is None:raise ValueError('Trecho não encontrado.')
    hit=rows[index];path=caminho(hit)
    prefix=path[:1] if escopo=='capitulo' else path[:2]
    if escopo=='topico' and len(path)>=4:
        prefix=path if hit['categoria']=='disciplinas' else path[:-1]
    elif escopo=='topico' and len(path)>=3 and path[1] in ['Clãs','Personagens']:
        prefix=path
    entries=list(intervalo(index,prefix))
    if escopo=='topico' and hit['categoria']=='disciplinas' and len(prefix)>2:
        # Discipline description and general Characteristics apply to its powers.
        intro=[r for r in rows if caminho(r) in [path[:2],path[:2]+('Características',)]]
        entries=list({r['id']:r for r in intro+entries}.values())
    if escopo!='capitulo' and len(prefix)==2:
        # Fome also needs Dados de Fome; mere introductory prose is insufficient.
        title=consultar.normalizar(prefix[-1])
        if len(title)>=4:
            for i,r in enumerate(rows):
                rp=caminho(r)
                other=consultar.normalizar(rp[-1])
                related=re.search(r'\b'+re.escape(title)+r'\b',other) or (len(other)>=4 and re.search(r'\b'+re.escape(other)+r'\b',title))
                if len(rp)==2 and rp[:1]==prefix[:1] and rp!=prefix and related:
                    entries.extend(intervalo(i,rp))
    included={r['id'] for r in entries}
    entries=[r for r in rows if r['id'] in included]
    pages=sorted({p for r in entries for p in r.get('paginas_pdf_de_origem',[r['pagina_pdf']])})
    printed={int(p) for r in entries for p in re.findall(r'p[áa]g(?:ina)?s?\.? *(\d+)',r['texto'],re.I)}
    related=[];seen=set()
    for r in rows:
        rp=caminho(r)[:2]
        if r['id'] not in included and r.get('pagina_impressa') in printed and rp not in seen:
            related.append({'id':r['id'],'titulo':' › '.join(rp),'pagina_pdf':r['pagina_pdf']})
            seen.add(rp)
    return {'principal':identifier,'titulo':prefix[-1],'caminho':list(prefix),'escopo':escopo,
            'paginas_pdf':pages,'trechos':copy.deepcopy(entries),'relacionados':related}


def buscar(query, limite=6):
    output=[];seen=set()
    for hit in consultar.buscar(query,limite=30):
        context=contexto(hit['id'])
        key=tuple(t['id'] for t in context['trechos'])
        if key in seen:continue
        seen.add(key)
        output.append({**hit,'contexto_completo':context})
        if len(output)>=limite:break
    return output


def pagina(numero,tipo='impressa'):
    """A referência impressa abre a página inteira, com seções navegáveis."""
    from core import Problem
    if tipo not in ['impressa','pdf'] or type(numero) is not int or not 1<=numero<=1000:
        raise Problem('Página inválida.')
    key='pagina_impressa' if tipo=='impressa' else 'pagina_pdf'
    entries=[r for r in catalogo() if r.get(key)==numero or (tipo=='pdf' and numero in r.get('paginas_pdf_de_origem',[])) or
             (tipo=='impressa' and isinstance(r.get('pagina_impressa'),int) and
              numero+r['pagina_pdf']-r['pagina_impressa'] in r.get('paginas_pdf_de_origem',[]))]
    if not entries:raise Problem('Página não encontrada no livro indexado.',404)
    return {'principal':entries[0]['id'],'titulo':f'Página {tipo} {numero}','caminho':[f'Página {tipo} {numero}'],
            'escopo':'pagina','paginas_pdf':sorted({r['pagina_pdf'] for r in entries}),'trechos':copy.deepcopy(entries),'relacionados':[]}


def recuperar(identifiers, limite=14000):
    """Never truncate a section. Mandatory first context may exceed the budget."""
    output=[];seen=set();total=0
    for identifier in dict.fromkeys(identifiers):
        context=contexto(identifier,'topico')
        entries=[r for r in context['trechos'] if r['id'] not in seen]
        size=sum(len(r['texto']) for r in entries)
        if output and total+size>limite:continue
        group='|'.join(context['caminho'])
        for entry in entries:
            entry['grupo_contexto']=group
            output.append(entry);seen.add(entry['id'])
        total+=size
    return output
