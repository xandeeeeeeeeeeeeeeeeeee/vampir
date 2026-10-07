"""Dados e autorização do assistente; nenhuma inferência ou processo ao importar."""
from contextlib import contextmanager, closing
import copy
import hashlib
import hmac
import html
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'base_mestre_rpg'))
import consultar

KINDS = ['personagem', 'npc', 'local', 'faccao', 'relacao', 'regra', 'segredo',
         'sessao', 'acontecimento', 'trama', 'cheat_sheet', 'nota']
ORIGINS = ['criacao', 'publicado', 'adaptacao', 'rumor']
STATES = ['rascunho', 'alternativa', 'planejado', 'confirmado']
ATTRS = ['Força', 'Destreza', 'Vigor', 'Carisma', 'Manipulação', 'Autocontrole',
         'Inteligência', 'Raciocínio', 'Determinação']
SKILLS = ['Armas Brancas', 'Armas de Fogo', 'Atletismo', 'Briga', 'Condução',
          'Furtividade', 'Ladinagem', 'Ofícios', 'Sobrevivência', 'Empatia', 'Etiqueta',
          'Intimidação', 'Liderança', 'Manha', 'Performance', 'Persuasão', 'Subterfúgio',
          'Trato com Animais', 'Ciência', 'Erudição', 'Finanças', 'Investigação',
          'Medicina', 'Ocultismo', 'Percepção', 'Política', 'Tecnologia']


class Problem(Exception):
    def __init__(self, text, status=400):
        super().__init__(text)
        self.status = status


def require_master(user):
    if user['role'] != 'mestre':
        raise Problem('Acesso exclusivo do mestre.', 403)


def player_ai_record(user, record):
    personal=record['kind'] in ['personagem','nota','cheat_sheet'] and user['id'] in record['owners']
    reference=record['kind'] in ['cheat_sheet','regra'] and (record['all_players'] or user['id'] in record['audience'])
    return not record['archived'] and (personal or reference)


def password_hash(password, salt=None):
    if not isinstance(password, str) or not 10 <= len(password) <= 200:
        raise Problem('Use uma senha de 10 a 200 caracteres.')
    salt = salt or secrets.token_hex(16)
    return salt, hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()


def fresh(kind='npc'):
    return {'id': str(uuid.uuid4()), 'kind': kind, 'name': '', 'summary': '',
            'origin': 'criacao', 'state': 'rascunho', 'date': '', 'links': [],
            'owners': [], 'audience': [], 'all_players': False, 'archived': False,
            'sheet': {}, 'content': '', 'master_notes': '', 'sources': [], 'version': 0}


class Store:
    def __init__(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / 'assistente.sqlite3'
        self.proposal_lock = threading.Lock()
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT UNIQUE,
                  role TEXT,salt TEXT,password TEXT,active INTEGER);
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT,
                  csrf TEXT,expires REAL);
                CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,data TEXT);
                CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY AUTOINCREMENT,
                  record_id TEXT,actor TEXT,created REAL,before TEXT,after TEXT);
                CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,created REAL,data TEXT);
                CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,data TEXT);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
                INSERT OR IGNORE INTO settings VALUES('campaign','{"titulo":"Nova crônica V5","sistema":"Vampiro: A Máscara V5"}');
            ''')

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=FULL')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialized(self):
        with self.db() as db:
            return bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone())

    def create_user(self, actor, name, password, role='jogador'):
        if actor is not None:
            require_master(actor)
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 60:
            raise Problem('Nome de acesso deve ter 2 a 60 caracteres.')
        salt, hashed = password_hash(password)
        user_id = str(uuid.uuid4())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if actor is None:
                if db.execute('SELECT 1 FROM users').fetchone():
                    raise Problem('Primeiro acesso já configurado.', 409)
                role = 'mestre'
            elif role != 'jogador':
                raise Problem('Novas contas são de jogadores.')
            try:
                db.execute('INSERT INTO users VALUES(?,?,?,?,?,1)',
                           (user_id, name.strip(), role, salt, hashed))
            except sqlite3.IntegrityError:
                raise Problem('Nome de acesso já utilizado.', 409)
        return {'id': user_id, 'name': name.strip(), 'role': role, 'active': True}

    def users(self, actor):
        require_master(actor)
        with self.db() as db:
            return [dict(zip(['id', 'name', 'role', 'active'], r)) for r in
                    db.execute('SELECT id,name,role,active FROM users ORDER BY name')]

    def revoke(self, actor, user_id):
        require_master(actor)
        with self.db() as db:
            db.execute("UPDATE users SET active=0 WHERE id=? AND role='jogador'", (user_id,))
            db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))

    def login(self, name, password):
        with self.db() as db:
            row = db.execute('SELECT id,name,role,salt,password,active FROM users WHERE name=?', (name,)).fetchone()
            # Derive even for nonexistent accounts to avoid a cheap user enumeration path.
            _, hashed = password_hash(password, row[3] if row else 'invalid-account')
            if not row or not row[5] or not hmac.compare_digest(row[4], hashed):
                raise Problem('Acesso inválido.', 401)
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), row[0], csrf, time.time()+43200))
        return token, {'id': row[0], 'name': row[1], 'role': row[2], 'csrf': csrf}

    def authenticate(self, token):
        with self.db() as db:
            row = db.execute('''SELECT u.id,u.name,u.role,s.csrf FROM sessions s
                JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1''',
                (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            raise Problem('Entre para continuar.', 401)
        return dict(zip(['id', 'name', 'role', 'csrf'], row))

    def logout(self, token):
        with self.db() as db:
            db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(token.encode()).hexdigest(),))

    @staticmethod
    def visible(user, record):
        if user['role'] == 'mestre':
            return True
        if record['kind'] == 'segredo':
            return False
        if record['kind'] == 'nota':
            return user['id'] in record['owners']
        return user['id'] in record['owners'] or record['all_players'] or user['id'] in record['audience']

    @staticmethod
    def project(user, record):
        result = copy.deepcopy(record)
        if user['role'] != 'mestre':
            result.pop('master_notes', None)
            result['sheet'].pop('notas_mestre', None)
            result.pop('sources', None)
        return result

    def records(self, user, archived=False):
        with self.db() as db:
            all_records = [json.loads(r[0]) for r in db.execute('SELECT data FROM records')]
        visible_ids = {r['id'] for r in all_records if self.visible(user, r)}
        result = []
        for record in all_records:
            if self.visible(user, record) and (archived or not record['archived']):
                shown = self.project(user, record)
                shown['links'] = [x for x in shown['links'] if x in visible_ids]
                result.append(shown)
        return result

    def get(self, user, record_id):
        result = next((r for r in self.records(user, True) if r['id'] == record_id), None)
        if result is None:
            raise Problem('Registro não encontrado.', 404)
        return result

    def validate(self, db, data):
        if set(data) != set(fresh()):
            raise Problem('Campos do registro inválidos.')
        if data['kind'] not in KINDS or data['origin'] not in ORIGINS or data['state'] not in STATES:
            raise Problem('Tipo, origem ou estado inválido.')
        for field in ['id', 'name', 'summary', 'date', 'content', 'master_notes']:
            if not isinstance(data[field], str) or len(data[field]) > 50000:
                raise Problem('Texto inválido: '+field)
        if not data['name'].strip() or len(data['name']) > 160 or len(data['id']) > 100:
            raise Problem('Nome obrigatório, até 160 caracteres.')
        try:
            uuid.UUID(data['id'])
        except ValueError:
            raise Problem('ID de registro inválido.')
        if type(data['version']) is not int or data['version'] < 0:
            raise Problem('Versão inválida.')
        for field in ['owners', 'audience', 'links', 'sources']:
            if not isinstance(data[field], list) or len(data[field]) > 100 or any(not isinstance(x, str) for x in data[field]):
                raise Problem('Lista inválida: '+field)
        if type(data['all_players']) is not bool or type(data['archived']) is not bool or not isinstance(data['sheet'], dict):
            raise Problem('Ficha ou visibilidade inválida.')
        for user_id in data['owners'] + data['audience']:
            if not db.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
                raise Problem('Conta atribuída inexistente.')
        for link in data['links']:
            if link == data['id'] or not db.execute('SELECT 1 FROM records WHERE id=?', (link,)).fetchone():
                raise Problem('Referência inexistente ou circular para o próprio registro.')
        for source in data['sources']:
            try:
                consultar.obter(source)
            except ValueError:
                raise Problem('Referência do livro inexistente.')
        if data['origin'] == 'publicado' and not data['sources']:
            raise Problem('Origem publicada exige uma referência verificável do livro.')
        self.validate_sheet(db, data['sheet'])
        if data['kind'] == 'regra' and 'limites' in data['sheet']:
            limits = data['sheet']['limites']
            if not isinstance(limits, dict):
                raise Problem('Limites de regra da casa devem ser um objeto.')
            for key, value in limits.items():
                if key not in ['atributos', 'habilidades', 'disciplinas', 'fome', 'humanidade', 'potencia_sangue'] or type(value) is not int or not 0 <= value <= 20:
                    raise Problem('Limite de regra da casa inválido.')

    @staticmethod
    def validate_sheet(db, sheet):
        if set(sheet)-{'atributos', 'habilidades', 'disciplinas', 'recursos', 'cla', 'papel',
                       'conceito', 'historico', 'condicoes', 'notas', 'notas_mestre',
                       'regra_da_casa', 'limites', 'cartografia', 'criacao'}:
            raise Problem('Campos desconhecidos na ficha.')
        if 'cartografia' in sheet:
            from cartografia import validar
            validar(sheet['cartografia'])
        if 'criacao' in sheet:
            from fichas import validar as validar_criacao
            validar_criacao(sheet)
        limits = {'atributos': 5, 'habilidades': 5, 'disciplinas': 5,
                  'fome': 5, 'humanidade': 10, 'potencia_sangue': 10}
        if sheet.get('regra_da_casa'):
            row = db.execute('SELECT data FROM records WHERE id=?', (sheet['regra_da_casa'],)).fetchone()
            rule = json.loads(row[0]) if row else None
            if not rule or rule['kind'] != 'regra' or rule['archived']:
                raise Problem('Exceção exige regra da casa ativa definida pelo mestre.')
            limits.update(rule['sheet'].get('limites', {}))
        for key in ['atributos', 'habilidades', 'disciplinas']:
            entries = sheet.get(key, {})
            if not isinstance(entries, dict):
                raise Problem(key+': use pares de nome e valor.')
            if key == 'atributos' and set(entries)-set(ATTRS):
                raise Problem('Atributo V5 desconhecido.')
            if key == 'habilidades' and set(entries)-set(SKILLS):
                raise Problem('Habilidade V5 desconhecida.')
            for name, value in entries.items():
                if not isinstance(name, str) or type(value) is not int or not (1 if key == 'atributos' else 0) <= value <= limits[key]:
                    raise Problem(key+': valor fora dos limites.')
        resources = sheet.get('recursos', {})
        if not isinstance(resources, dict):
            raise Problem('Recursos devem ser um objeto.')
        for key, value in resources.items():
            if type(value) is not int or not 0 <= value <= limits.get(key, 100):
                raise Problem('Recurso inválido: '+key)
        for key in ['cla', 'papel', 'conceito', 'historico', 'condicoes', 'notas', 'notas_mestre']:
            if key in sheet and (not isinstance(sheet[key], str) or len(sheet[key]) > 50000):
                raise Problem('Campo de ficha inválido: '+key)

    def put(self, user, record, expected):
        data = copy.deepcopy(record)
        if type(expected) is not int:
            raise Problem('Informe a versão esperada.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM records WHERE id=?', (data.get('id'),)).fetchone()
            before = json.loads(row[0]) if row else None
            if user['role'] != 'mestre':
                if before:
                    if user['id'] not in before['owners'] or before['kind'] not in ['personagem', 'nota', 'cheat_sheet'] or before['archived']:
                        raise Problem('Você só pode editar suas fichas e notas ativas.', 403)
                    safe = copy.deepcopy(before)
                    for field in ['name', 'summary', 'content', 'sheet']+(['date'] if before['kind']=='nota' else []):
                        if field in data:
                            safe[field] = data[field]
                    # Assignment and mechanical exceptions are controlled by the master.
                    for key in ['regra_da_casa', 'notas_mestre']:
                        if data.get('sheet', {}).get(key) != self.project(user, before)['sheet'].get(key):
                            raise Problem('Exceções e notas do mestre não são editáveis pelo jogador.', 403)
                        if key in before['sheet']:
                            safe['sheet'][key] = before['sheet'][key]
                    data = safe
                elif data.get('kind') in ['personagem', 'nota', 'cheat_sheet']:
                    safe = fresh(data['kind'])
                    for field in ['id', 'name', 'summary', 'content', 'sheet']+(['date'] if data['kind']=='nota' else []):
                        safe[field] = data[field]
                    if safe['sheet'].get('regra_da_casa') or safe['sheet'].get('notas_mestre'):
                        raise Problem('Exceções e notas do mestre não são editáveis pelo jogador.', 403)
                    safe['owners'] = [user['id']]
                    data = safe
                else:
                    raise Problem('Crie fichas, notas ou cheat sheets; mudanças do mundo precisam do mestre.', 403)
            version = before['version'] if before else 0
            if version != expected:
                raise Problem('Registro mudou. Reabra e reconcilie suas alterações.', 409)
            data['version'] = version + 1
            self.validate(db, data)
            db.execute('INSERT INTO records VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                       (data['id'], json.dumps(data, ensure_ascii=False)))
            db.execute('INSERT INTO revisions(record_id,actor,created,before,after) VALUES(?,?,?,?,?)',
                       (data['id'], user['id'], time.time(), json.dumps(before), json.dumps(data)))
        result = self.get(user, data['id'])
        affected = [r['id'] for r in self.records(user) if data['id'] in r['links']]
        return {'record': result, 'afetados': affected}

    def revisions(self, user, record_id):
        self.get(user, record_id)
        with self.db() as db:
            rows = db.execute('SELECT id,created,actor,before,after FROM revisions WHERE record_id=? ORDER BY id DESC', (record_id,)).fetchall()
        result = []
        for rid, stamp, actor, before, after in rows:
            old, new = json.loads(before), json.loads(after)
            if user['role'] != 'mestre' and (not self.visible(user, new) or (old and not self.visible(user, old))):
                continue
            # Historical links may reference records that are private now; never leak them.
            allowed = {r['id'] for r in self.records(user, True)}
            values = []
            for value in [old, new]:
                view = self.project(user, value) if value else None
                if view:
                    view['links'] = [x for x in view['links'] if x in allowed]
                values.append(view)
            result.append({'id': rid, 'created': stamp, 'before': values[0], 'after': values[1]})
        return result

    def restore(self, user, record_id, revision_id, expected):
        require_master(user)
        revision = next((x for x in self.revisions(user, record_id) if x['id'] == revision_id), None)
        if not revision:
            raise Problem('Revisão inexistente.', 404)
        data = revision['after']
        return self.put(user, data, expected)

    def campaign(self, user, value=None):
        if value is not None:
            require_master(user)
            if not isinstance(value, dict) or set(value) != {'titulo', 'sistema'} or not isinstance(value['titulo'], str) or not 1 <= len(value['titulo']) <= 160 or value['sistema'] != 'Vampiro: A Máscara V5':
                raise Problem('Campanha inválida.')
            with self.db() as db:
                db.execute("UPDATE settings SET value=? WHERE key='campaign'", (json.dumps(value),))
        with self.db() as db:
            return json.loads(db.execute("SELECT value FROM settings WHERE key='campaign'").fetchone()[0])

    def messages(self, user):
        with self.db() as db:
            rows = [json.loads(x[0]) for x in db.execute('SELECT data FROM messages ORDER BY created')]
        return [r for r in rows if r.get('usuario') == user['id'] or (not r.get('usuario') and user['role'] == 'mestre')]

    def proposals(self, user):
        with self.db() as db:
            rows = [json.loads(x[0]) for x in db.execute('SELECT data FROM proposals')]
        if user['role'] == 'mestre':
            return rows
        result = []
        allowed = {r['id'] for r in self.records(user, True)}
        for proposal in rows:
            if proposal.get('usuario') != user['id']:
                continue
            if proposal['after']['kind'] not in ['personagem','nota','cheat_sheet']:
                continue
            if proposal['before'] and user['id'] not in proposal['before']['owners']:
                continue
            if proposal['before'] and proposal['before']['id'] not in allowed:
                continue
            proposal = copy.deepcopy(proposal)
            for field in ['before', 'after']:
                if proposal[field]:
                    proposal[field] = self.project(user, proposal[field])
                    proposal[field]['links'] = [x for x in proposal[field]['links'] if x in allowed]
            proposal['afetados'] = [x for x in proposal['afetados'] if x in allowed]
            result.append(proposal)
        return result

    def decide(self, user, proposal_id, action, edited=None):
        with self.proposal_lock:
            return self._decide(user, proposal_id, action, edited)

    def _decide(self, user, proposal_id, action, edited=None):
        with self.db() as db:
            row = db.execute('SELECT data FROM proposals WHERE id=?', (proposal_id,)).fetchone()
        if not row:
            raise Problem('Proposta não encontrada.', 404)
        proposal = json.loads(row[0])
        if user['role'] != 'mestre' and proposal.get('usuario') != user['id']:
            raise Problem('Proposta não encontrada.', 404)
        if user['role'] != 'mestre' and (proposal['after']['kind'] not in ['personagem','nota','cheat_sheet'] or
                                        (proposal['before'] and user['id'] not in proposal['before']['owners'])):
            raise Problem('Propostas da campanha são exclusivas do mestre.',403)
        if proposal['status'] != 'pendente':
            raise Problem('Proposta já decidida.', 409)
        if action not in ['aceitar', 'descartar']:
            raise Problem('Decisão inválida.')
        result = None
        if action == 'aceitar':
            data = edited or proposal['after']
            if data['id'] != proposal['after']['id']:
                raise Problem('Não altere o ID da proposta.')
            result = self.put(user, data, proposal['expected'])
        proposal['status'] = 'aceita' if action == 'aceitar' else 'descartada'
        with self.db() as db:
            db.execute('UPDATE proposals SET data=? WHERE id=?', (json.dumps(proposal), proposal_id))
        shown = next((p for p in self.proposals(user) if p['id'] == proposal_id), None)
        return {'proposta': shown, 'resultado': result}

    def save_answer(self, user, question, answer, supplied_sources, elapsed, model):
        if not isinstance(answer, dict) or set(answer) != {'resposta', 'fontes', 'propostas'}:
            raise Problem('Resposta estruturada inválida; nenhum registro foi alterado.')
        if not isinstance(answer['resposta'], str) or not isinstance(answer['fontes'], list) or any(x not in supplied_sources for x in answer['fontes']):
            raise Problem('Resposta ou citação não verificada.')
        if not isinstance(answer['propostas'], list) or len(answer['propostas']) > 8:
            raise Problem('Propostas inválidas.')
        proposals = []
        for change in answer['propostas']:
            if not isinstance(change, dict) or set(change) != {'alvo', 'versao', 'motivo', 'registro'}:
                raise Problem('Formato de proposta inválido.')
            current = self.get(user, change['alvo']) if change['alvo'] else None
            data = copy.deepcopy(change['registro'])
            if current and isinstance(data.get('sheet'),dict):
                old_sheet=self.project(user,current)['sheet']
                for key in ['criacao','cartografia']:
                    if old_sheet.get(key) and not data['sheet'].get(key):
                        data['sheet'][key]=copy.deepcopy(old_sheet[key])
                if old_sheet.get('criacao'):
                    for key in ['atributos','habilidades','disciplinas','recursos']:
                        if isinstance(data['sheet'].get(key,{}),dict):
                            data['sheet'][key]={**copy.deepcopy(old_sheet.get(key,{})),**data['sheet'].get(key,{})}
                    for key in ['cla','conceito','historico']:
                        if not data['sheet'].get(key):data['sheet'][key]=old_sheet.get(key,'')
            expected = current['version'] if current else 0
            if change['versao'] != expected:
                raise Problem('Contexto da proposta desatualizado.', 409)
            if current and data['id'] != current['id']:
                raise Problem('ID de proposta divergente.')
            if not current:
                data['id'] = str(uuid.uuid4())
            data['version'] = expected
            if user['role'] != 'mestre':
                if data['kind'] not in ['personagem','nota','cheat_sheet'] or (current and (user['id'] not in current['owners'] or current['archived'])):
                    raise Problem('A IA do jogador só pode propor fichas e materiais pessoais.', 403)
                allowed = {r['id'] for r in self.records(user) if player_ai_record(user,r)}
                if any(link not in allowed for link in data['links']):
                    raise Problem('Referência não disponível ao jogador.', 403)
                data['master_notes'] = ''
                data['sheet'].pop('notas_mestre', None)
            with self.db() as db:
                self.validate(db, data)
            # AI cannot silently publish material, assign players, or define exceptions.
            if current:
                for key in ['owners', 'audience', 'all_players']:
                    data[key] = current[key]
                if data['sheet'].get('regra_da_casa') != current['sheet'].get('regra_da_casa'):
                    raise Problem('Exceção mecânica requer edição explícita do mestre.')
            else:
                data['owners'] = [user['id']] if user['role'] != 'mestre' else []
                data['audience'], data['all_players'] = [], False
                if data['sheet'].get('regra_da_casa'):
                    raise Problem('Exceção mecânica requer edição explícita do mestre.')
            proposals.append({'id': str(uuid.uuid4()), 'before': current, 'after': data,
                              'expected': expected, 'motivo': change['motivo'], 'status': 'pendente',
                              'usuario': user['id'],
                              'afetados': [r['id'] for r in self.records(user) if data['id'] in r['links']]})
        message = {'id': str(uuid.uuid4()), 'pergunta': question, 'resposta': answer['resposta'],
                   'usuario': user['id'],
                   'fontes': answer['fontes'], 'modelo': model, 'duracao': elapsed,
                   'propostas': [p['id'] for p in proposals]}
        if user['role'] != 'mestre':message['escopo_ia']='pessoal'
        with self.db() as db:
            db.execute('INSERT INTO messages VALUES(?,?,?)', (message['id'], time.time(), json.dumps(message)))
            db.executemany('INSERT INTO proposals VALUES(?,?)', [(p['id'], json.dumps(p)) for p in proposals])
        return message

    def export(self, user, record_id, fmt, private=False):
        record = self.get(user, record_id)
        if private:
            require_master(user)
        else:
            record = self.project({'role': 'jogador'}, record)
        labels = {'atributos':'Atributos', 'habilidades':'Habilidades', 'disciplinas':'Disciplinas',
                  'recursos':'Recursos', 'cla':'Clã', 'papel':'Papel', 'conceito':'Conceito',
                  'historico':'Histórico', 'condicoes':'Condições', 'notas':'Notas pessoais',
                  'notas_mestre':'Notas privadas do mestre', 'regra_da_casa':'Regra da casa', 'limites':'Limites'}
        text = '# '+record['name']+'\n\n'+record['summary']+'\n\n'+record['content']+'\n\n'
        blocks = []
        for key, value in record['sheet'].items():
            if not value:
                continue
            title = labels.get(key, key.replace('_', ' ').capitalize())
            if key=='criacao':
                readable=json.dumps(value,ensure_ascii=False,indent=2)
                text+='## Criação completa e escolhas propostas\n\n```json\n'+readable+'\n```\n\n'
                blocks.append('<section><h2>Criação completa e escolhas propostas</h2><pre>'+html.escape(readable)+'</pre></section>')
            elif isinstance(value, dict):
                lines = [f'- {name.replace("_", " ")}: {number}' for name, number in value.items()]
                text += '## '+title+'\n\n'+'\n'.join(lines)+'\n\n'
                items = ''.join('<div class="stat"><span>'+html.escape(name.replace('_', ' '))+'</span><strong>'+html.escape(str(number))+'</strong></div>' for name, number in value.items())
                blocks.append('<section><h2>'+html.escape(title)+'</h2><div class="stats">'+items+'</div></section>')
            else:
                text += '## '+title+'\n\n'+str(value)+'\n\n'
                blocks.append('<section><h2>'+html.escape(title)+'</h2><p>'+html.escape(str(value))+'</p></section>')
        if private and record.get('master_notes'):
            text += '\n## Notas do mestre (privadas)\n\n'+record['master_notes']
        if fmt == 'md':
            return text, 'text/markdown; charset=utf-8'
        if fmt != 'html':
            raise Problem('Formato deve ser md ou html.')
        notes = '<section><h2>Notas privadas do mestre</h2><p>'+html.escape(record.get('master_notes', ''))+'</p></section>' if private else ''
        return ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>'+html.escape(record['name'])+
                '</title><style>body{max-width:850px;margin:auto;padding:24px;font:15px/1.6 system-ui;color:#182021}'
                'h1{font-family:Georgia,serif;font-size:32px}h2{font-size:18px}section{break-inside:avoid;border-top:1px solid #bbb;padding:10px 0}'
                'p{white-space:pre-wrap;overflow-wrap:anywhere}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}'
                '.stat{display:flex;justify-content:space-between;border:1px solid #ccc;border-radius:5px;padding:8px}'
                '@media(max-width:550px){.stats{grid-template-columns:1fr}}@media print{body{padding:0}.hint{display:none}}</style>'
                '<p class="hint">Use Imprimir no navegador para salvar em PDF.</p><h1>'+html.escape(record['name'])+'</h1><p>'+html.escape(record['summary'])+
                '</p><p>'+html.escape(record['content'])+'</p>'+''.join(blocks)+notes+'</html>'), 'text/html; charset=utf-8'

    def backup(self, target):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as source, closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
