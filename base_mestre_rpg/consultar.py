"""Ferramentas locais para o mestre; a saída JSON é interna, não a narrativa."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
import sys
import unicodedata

B = Path(__file__).resolve().parent


def normalizar(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if not unicodedata.combining(c))


def conexao():
    return sqlite3.connect((B / 'busca/livro.sqlite3').as_uri() + '?mode=ro', uri=True)


def buscar(consulta, categoria=None, limite=6):
    aliases = json.loads((B / 'busca/aliases.json').read_text(encoding='utf-8'))
    extra = [v for k, v in aliases.items() if normalizar(k) in normalizar(consulta)]
    termos = list(dict.fromkeys(re.findall(r'[^\W_]+', consulta + ' ' + ' '.join(extra), re.UNICODE)))
    vazios = {'o', 'a', 'de', 'da', 'do', 'as', 'os', 'em', 'como', 'qual', 'que', 'para', 'e', 'um', 'uma', 'dos', 'das'}
    termos = [t for t in termos if normalizar(t) not in vazios][:40]
    if not termos:
        return []
    # Nunca passa sintaxe FTS, SQL ou operadores digitados pelo usuário ao banco.
    expr = ' OR '.join('"' + t.replace('"', '""') + '"' for t in termos)
    sql = '''SELECT t.dados, bm25(pesquisa,0,7,3,1) AS score
             FROM pesquisa JOIN trechos t ON t.id=pesquisa.id
             WHERE pesquisa MATCH ?'''
    params = [expr]
    if categoria:
        sql += ' AND t.categoria=?'
        params.append(categoria)
    sql += ' ORDER BY score, t.pagina, t.id LIMIT ?'
    params.append(max(1, min(limite, 30)))
    db = conexao()
    try:
        encontrados = []
        for raw, score in db.execute(sql, params):
            d = json.loads(raw)
            corpo = d.pop('texto')
            norm = normalizar(corpo)
            ocorrencias = [norm.find(normalizar(t)) for t in termos if normalizar(t) in norm]
            pos = max(0, min(ocorrencias, default=0) - 160)
            d['previa'] = corpo[pos:pos + 950]
            d['trecho_completo'] = f'consultar.py trecho {d["id"]} --vizinhos 1'
            d['score'] = score
            encontrados.append(d)
        return encontrados
    finally:
        db.close()


def obter(identificador, vizinhos=0):
    db = conexao()
    try:
        row = db.execute('SELECT rowid,categoria FROM trechos WHERE id=?', (identificador,)).fetchone()
        if row is None:
            raise ValueError('Trecho não encontrado.')
        raio = max(0, min(vizinhos, 3))
        return [json.loads(d[0]) for d in db.execute(
            'SELECT dados FROM trechos WHERE rowid BETWEEN ? AND ? AND categoria=? ORDER BY rowid',
            (row[0] - raio, row[0] + raio, row[1]))]
    finally:
        db.close()


def avaliar_dados(comuns, fome, dificuldade):
    if isinstance(dificuldade, bool) or not isinstance(dificuldade, int) or dificuldade < 0:
        raise ValueError('Dificuldade precisa ser inteiro não negativo.')
    if not comuns and not fome:
        raise ValueError('Parada vazia: defina vitória automática ou aplique o mínimo previsto na regra.')
    if any(isinstance(d, bool) or not isinstance(d, int) or not 1 <= d <= 10 for d in comuns + fome):
        raise ValueError('Dados precisam ter faces inteiras de 1 a 10.')
    dez = sum(d == 10 for d in comuns + fome)
    sucessos = sum(d >= 6 for d in comuns + fome) + 2 * (dez // 2)
    vitoria = sucessos >= dificuldade
    critico = vitoria and dez >= 2
    return {'dados_comuns': comuns, 'dados_fome': fome, 'dificuldade': dificuldade,
            'sucessos': sucessos, 'margem': sucessos - dificuldade, 'vitoria': vitoria,
            'critico': critico, 'critico_bestial': critico and 10 in fome,
            'falha_bestial': not vitoria and 1 in fome,
            'fontes_paginas_pdf': [120, 122, 123, 207, 208, 209],
            'escopo': 'Contagem de teste simples. Empates de disputas, dano, poderes e exceções exigem a regra específica.'}


def rolar(parada, fome, dificuldade, tipo='normal'):
    if not 1 <= parada <= 100 or not 0 <= fome <= 5:
        raise ValueError('Parada deve ser 1–100; Fome deve ser 0–5.')
    numero_fome = 0 if tipo in ('checagem', 'forca_vontade', 'humanidade') else min(fome, parada)
    rng = random.SystemRandom()
    return avaliar_dados([rng.randint(1, 10) for _ in range(parada - numero_fome)],
                         [rng.randint(1, 10) for _ in range(numero_fome)], dificuldade)


def rerrolar(comuns, fome, indices, dificuldade, rng=None):
    avaliar_dados(comuns, fome, dificuldade)
    if not 1 <= len(indices) <= 3 or len(set(indices)) != len(indices):
        raise ValueError('Rerrole de um a três dados comuns distintos.')
    if any(i < 0 or i >= len(comuns) for i in indices):
        raise ValueError('Índice inválido: índices começam em zero e referem-se apenas aos dados comuns.')
    rng = rng or random.SystemRandom()
    novos = list(comuns)
    for i in indices:
        novos[i] = rng.randint(1, 10)
    resultado = avaliar_dados(novos, list(fome), dificuldade)
    resultado['dados_comuns_anteriores'] = comuns
    resultado['indices_rerrolados'] = indices
    resultado['custo_a_aplicar'] = '1 dano Superficial à Força de Vontade; verificar disponibilidade e permissão na regra específica.'
    resultado['fonte_rerrolagem_pagina_pdf'] = 124
    return resultado


def validar_campanha(estado):
    erros = []
    if not isinstance(estado, dict):
        return ['Estado precisa ser um objeto JSON.']
    if estado.get('sistema') != 'Vampiro: A Máscara' or estado.get('edicao') != 'Quinta Edição':
        erros.append('Sistema/edição divergente da fonte desta base.')
    rev = estado.get('revisao')
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
        erros.append('Revisão inválida.')
    colecoes = ['personagens', 'npcs', 'locais', 'faccoes', 'relacoes', 'fatos', 'segredos', 'tramas', 'regras_da_casa', 'eventos', 'pendencias']
    ids = set()
    itens = []
    entidades = set()
    for chave in colecoes:
        lista = estado.get(chave)
        if not isinstance(lista, list):
            erros.append(f'{chave}: esperado uma lista.')
            continue
        for item in lista:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
                erros.append(f'{chave}: registro sem ID textual.')
                continue
            if item['id'] in ids:
                erros.append(f'ID duplicado: {item["id"]}')
            ids.add(item['id'])
            itens.append((chave, item))
            if chave in ('personagens', 'npcs', 'locais', 'faccoes'):
                entidades.add(item['id'])
    for chave, item in itens:
        for referencia in item.get('referencias', []):
            if referencia not in ids:
                erros.append(f'{item["id"]}: referência inexistente {referencia}')
        for pessoa in item.get('conhecido_por', []):
            if pessoa != 'mestre' and pessoa not in entidades:
                erros.append(f'{item["id"]}: observador inexistente {pessoa}')
        if chave == 'relacoes':
            for campo in ('origem', 'destino'):
                if item.get(campo) not in entidades:
                    erros.append(f'{item["id"]}: relação sem entidade válida em {campo}')
        if chave in ('personagens', 'npcs'):
            mecanica = item.get('mecanica', {})
            if not isinstance(mecanica, dict):
                erros.append(f'{item["id"]}: mecanica precisa ser um objeto.')
                continue
            for campo, maximo in [('fome', 5), ('humanidade', 10), ('potencia_sangue', 10)]:
                v = mecanica.get(campo)
                if v is not None and (isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= maximo):
                    erros.append(f'{item["id"]}: {campo} fora de 0–{maximo}')
            for campo in ('vitalidade', 'forca_vontade'):
                trilha = mecanica.get(campo)
                if trilha is not None:
                    valores = [trilha.get(k) for k in ('maxima', 'superficial', 'agravado')] if isinstance(trilha, dict) else []
                    if len(valores) != 3 or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in valores):
                        erros.append(f'{item["id"]}: trilha {campo} inválida')
                    elif valores[1] + valores[2] > valores[0]:
                        erros.append(f'{item["id"]}: trilha {campo} excedida; aplicar conversão/estado antes de salvar')
    return erros


def validar_base():
    m = json.loads((B / 'MANIFESTO.json').read_text(encoding='utf-8'))
    erros = []
    dados = (B / m['copia_literal']).read_bytes()
    if hashlib.sha256(dados).hexdigest() != m['fonte_sha256']:
        erros.append('Cópia literal alterada após a indexação.')
    fonte = dados.decode('utf-8-sig')
    tematico = (B / 'LIVRO_PARA_AGENTES.md').read_text(encoding='utf-8')

    def partes(t):
        marcas = list(re.finditer(r'<!--\s*Página\s+(\d+)\s*-->', t))
        saida = {}
        for i, marca in enumerate(marcas):
            fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(t)
            s = t[marca.end():fim].strip()
            # Cabeçalho do assunto seguinte fica entre o último bloco e o próximo marcador.
            s = re.split(r'\n\n<a id="assunto-', s)[0].strip()
            n = int(marca[1])
            if n in saida:
                erros.append(f'Página temática duplicada: {n}')
            saida[n] = s
        return saida

    original, organizado = partes(fonte), partes(tematico)
    if set(original) != set(organizado) or len(organizado) != 434:
        erros.append('Cobertura temática incompleta.')
    for n, t in original.items():
        convertido = organizado.get(n, '').replace('](fontes/', '](')
        if t != convertido:
            erros.append(f'Conteúdo alterado/ausente na página {n}')
    db = conexao()
    try:
        if db.execute('SELECT count(*) FROM trechos').fetchone()[0] != m['trechos']:
            erros.append('Contagem de trechos divergente.')
        for raw, in db.execute('SELECT dados FROM trechos'):
            d = json.loads(raw)
            if hashlib.sha256(d['texto'].encode('utf-8')).hexdigest() != d['sha256_texto']:
                erros.append(f'Trecho alterado: {d["id"]}')
    finally:
        db.close()
    for arquivo in [B / 'LIVRO_PARA_AGENTES.md', B / m['copia_literal']]:
        for imagem in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', arquivo.read_text(encoding='utf-8')):
            if not (arquivo.parent / imagem).exists():
                erros.append(f'Imagem ausente: {imagem}')
    return {'paginas': len(organizado), 'trechos': m['trechos'], 'falhas': erros}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='acao', required=True)
    p = sub.add_parser('buscar'); p.add_argument('consulta'); p.add_argument('--categoria'); p.add_argument('--limite', type=int, default=6)
    p = sub.add_parser('trecho'); p.add_argument('id'); p.add_argument('--vizinhos', type=int, default=0)
    p = sub.add_parser('rolar'); p.add_argument('--parada', type=int, required=True); p.add_argument('--fome', type=int, default=0); p.add_argument('--dificuldade', type=int, required=True); p.add_argument('--tipo', choices=['normal', 'checagem', 'forca_vontade', 'humanidade'], default='normal')
    p = sub.add_parser('rerrolar'); p.add_argument('--comuns', type=int, nargs='+', required=True); p.add_argument('--fome', type=int, nargs='*', default=[]); p.add_argument('--indices', type=int, nargs='+', required=True); p.add_argument('--dificuldade', type=int, required=True)
    sub.add_parser('validar-base')
    p = sub.add_parser('validar-campanha'); p.add_argument('--arquivo', type=Path, default=B / 'campanha/estado.json')
    args = parser.parse_args()
    if args.acao == 'buscar': resultado = buscar(args.consulta, args.categoria, args.limite)
    elif args.acao == 'trecho': resultado = obter(args.id, args.vizinhos)
    elif args.acao == 'rolar': resultado = rolar(args.parada, args.fome, args.dificuldade, args.tipo)
    elif args.acao == 'rerrolar': resultado = rerrolar(args.comuns, args.fome, args.indices, args.dificuldade)
    elif args.acao == 'validar-base': resultado = validar_base()
    else: resultado = {'falhas': validar_campanha(json.loads(args.arquivo.read_text(encoding='utf-8')))}
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 1 if isinstance(resultado, dict) and resultado.get('falhas') else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, sqlite3.Error) as erro:
        print(json.dumps({'erro_interno': str(erro)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
