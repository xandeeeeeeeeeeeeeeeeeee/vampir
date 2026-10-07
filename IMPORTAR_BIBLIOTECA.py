"""Importação explícita de biblioteca privada. Não modifica a fonte e não inicia IA."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import shutil
import sqlite3

ROOT=Path(__file__).resolve().parent

def importar(origem):
    source=Path(origem).resolve(strict=True)/'busca'
    dbpath=source/'livro.sqlite3';aliases=source/'aliases.json'
    with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Biblioteca corrompida.')
        ids={r[0] for r in db.execute('SELECT id FROM trechos')}
        # Os guias e o perfil de ficha dependem desta edição já indexada.
        required=set()
        for filename in ['fichas.py','materiais.py']:
            required.update(re.findall(r'p[0-9]{4}-t[0-9]{3}',(ROOT/'assistente_rpg'/filename).read_text(encoding='utf-8')))
        if not required<=ids:raise ValueError('Índice incompatível com as referências do perfil V5: '+', '.join(sorted(required-ids)))
        db.execute('SELECT id FROM pesquisa LIMIT 1').fetchone()
    mapping=json.loads(aliases.read_text(encoding='utf-8'))
    if not isinstance(mapping,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in mapping.items()):raise ValueError('Aliases inválidos.')
    destination=ROOT/'base_mestre_rpg/busca'
    if destination.exists():raise ValueError('Biblioteca já existe; importação recusada para preservar os dados.')
    destination.mkdir()
    try:
        # Backup SQLite consistente, inclusive se a fonte estiver aberta.
        with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(destination/'livro.sqlite3')) as dst:
            src.backup(dst)
        shutil.copy2(aliases,destination/'aliases.json')
    except Exception:
        # Não apagar recursivamente: apenas os dois arquivos criados por esta operação.
        for name in ['livro.sqlite3','aliases.json']:(destination/name).unlink(missing_ok=True)
        destination.rmdir();raise
    print('Biblioteca importada localmente; ignorada pelo Git. Nenhuma IA iniciada.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('origem',help='Pasta base_mestre_rpg da biblioteca privada indexada')
    importar(parser.parse_args().origem)
