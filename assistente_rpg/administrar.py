"""Backup e importação explícita. Nunca chamado pelo modelo ou por jogadores."""
import argparse
from contextlib import closing
import datetime
import json
from pathlib import Path
import sqlite3
import uuid

from core import ROOT, Store, fresh
from materiais import ids_catalogo


def campanha_tem_registros(db):
    guides=ids_catalogo()
    return any(record_id not in guides or json.loads(raw)['kind']!='cheat_sheet'
               for record_id,raw in db.execute('SELECT id,data FROM records'))


def importar(store, source_path, snapshot_folder=None):
    source_path = Path(source_path).resolve(strict=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    snapshot = Path(snapshot_folder or ROOT/'backups')/('origem_importacao_'+stamp+'.sqlite3')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with (closing(sqlite3.connect(source_path.as_uri()+'?mode=ro', uri=True)) as source,
          closing(sqlite3.connect(snapshot)) as target):
        source.backup(target)
    with closing(sqlite3.connect(snapshot)) as db:
        state = json.loads(db.execute('SELECT dados FROM estado WHERE id=1').fetchone()[0])
    with store.db() as db:
        row = db.execute("SELECT id,name,role FROM users WHERE role='mestre' AND active=1").fetchone()
        if not row or campanha_tem_registros(db):
            raise ValueError('Crie o acesso do mestre e use uma campanha vazia para importar.')
    actor = dict(zip(['id', 'name', 'role'], row))
    mapping = {'personagens':'personagem','npcs':'npc','locais':'local','faccoes':'faccao',
               'relacoes':'relacao','fatos':'acontecimento','segredos':'segredo',
               'tramas':'trama','regras_da_casa':'regra','eventos':'acontecimento','pendencias':'nota'}
    imported = []
    for collection, kind in mapping.items():
        for old in state.get(collection, []):
            data = fresh(kind)
            data['name'] = old.get('nome') or old.get('id') or 'Importado'
            data['summary'] = old.get('descricao', '')[:1000]
            data['content'] = json.dumps(old, ensure_ascii=False, indent=2)
            data['origin'] = 'adaptacao'
            data['state'] = 'confirmado' if kind == 'acontecimento' else 'rascunho'
            data['owners'] = [actor['id']] if kind == 'nota' else []
            # Source metadata is preserved in content for review, not fabricated as a complete ficha.
            imported.append((old.get('id'), data))
    ids = {old_id: data['id'] for old_id, data in imported if old_id}
    # Validate and insert atomically so interrupted imports leave no partial campaign.
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if campanha_tem_registros(db):
            raise ValueError('A campanha recebeu registros durante a importação.')
        for _, data in imported:
            data['version'] = 1
            store.validate(db, data)
            db.execute('INSERT INTO records VALUES(?,?)', (data['id'], json.dumps(data)))
        for old_id, data in imported:
            old = json.loads(data['content'])
            references = old.get('referencias', [])
            if data['kind'] == 'relacao':
                references += [old.get('origem'), old.get('destino')]
            data['links'] = list(dict.fromkeys(ids[x] for x in references if x in ids and ids[x] != data['id']))
            store.validate(db, data)
            db.execute('UPDATE records SET data=? WHERE id=?', (json.dumps(data), data['id']))
            db.execute('INSERT INTO revisions(record_id,actor,created,before,after) VALUES(?,?,strftime("%s","now"),?,?)',
                       (data['id'], actor['id'], 'null', json.dumps(data)))
    return {'snapshot':str(snapshot),'registros_importados':len(imported),
            'nota':'Todos privados. Revise e converta as fichas antes de atribuir jogadores.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('acao', choices=['backup','importar'])
    parser.add_argument('--origem', type=Path)
    parser.add_argument('--confirmar-importacao', action='store_true')
    args = parser.parse_args()
    store = Store(ROOT/'dados')
    if args.acao == 'backup':
        path = ROOT/'backups'/('assistente_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.sqlite3')
        store.backup(path)
        print(path)
    else:
        if not args.origem or not args.confirmar_importacao:
            parser.error('Importação exige --origem CAMINHO e --confirmar-importacao.')
        print(json.dumps(importar(store, args.origem), ensure_ascii=False, indent=2))
