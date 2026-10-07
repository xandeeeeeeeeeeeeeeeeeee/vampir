import copy
from contextlib import closing
import concurrent.futures
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from core import Problem, ROOT, Store, fresh
from ai import Tasks
from servidor import make_server


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.master = self.store.create_user(None, 'mestre', 'senha-segura-123')
        self.p1 = self.store.create_user(self.master, 'jogador1', 'senha-segura-123')
        self.p2 = self.store.create_user(self.master, 'jogador2', 'senha-segura-123')

    def create(self, kind='personagem', **fields):
        record = fresh(kind)
        record.update({'name': 'Nome', **fields})
        return self.store.put(self.master, record, 0)['record']


class DataTests(Fixture):
    def test_campaign_empty_and_independent(self):
        self.assertEqual([], self.store.records(self.master))
        self.assertEqual('Vampiro: A Máscara V5', self.store.campaign(self.master)['sistema'])
        self.assertNotEqual(ROOT.parent/'mestre_local/dados/campanha.sqlite3', self.store.path)

    def test_entity_lifecycle_all_types(self):
        from core import KINDS
        for kind in KINDS:
            r = self.create(kind)
            r['summary'] = 'Editado'
            self.store.put(self.master, r, 1)
            r = self.store.get(self.master, r['id'])
            r['archived'] = True
            self.store.put(self.master, r, 2)
            self.assertNotIn(r['id'], [x['id'] for x in self.store.records(self.master)])
            self.store.restore(self.master, r['id'], self.store.revisions(self.master, r['id'])[-1]['id'], 3)
            restored = self.store.get(self.master, r['id'])
            self.assertFalse(restored['archived'])
            self.assertEqual(4, restored['version'])

    def test_owner_edit_preserves_secrets_and_grants(self):
        r = self.create(owners=[self.p1['id']], master_notes='SEGREDO', sheet={'notas_mestre': 'OUTRO SEGREDO'})
        shown = self.store.get(self.p1, r['id'])
        self.assertNotIn('master_notes', shown)
        self.assertNotIn('notas_mestre', shown['sheet'])
        shown['name'] = 'Minha ficha'
        shown['all_players'] = True
        shown['owners'] = [self.p2['id']]
        self.store.put(self.p1, shown, 1)
        actual = self.store.get(self.master, r['id'])
        self.assertEqual('SEGREDO', actual['master_notes'])
        self.assertEqual('OUTRO SEGREDO', actual['sheet']['notas_mestre'])
        self.assertEqual([self.p1['id']], actual['owners'])
        self.assertFalse(actual['all_players'])

    def test_foreign_and_secret_denied(self):
        r = self.create(owners=[self.p1['id']])
        with self.assertRaises(Problem): self.store.get(self.p2, r['id'])
        with self.assertRaises(Problem): self.store.put(self.p2, r, 1)
        secret = self.create('segredo', all_players=True, audience=[self.p1['id']])
        with self.assertRaises(Problem): self.store.get(self.p1, secret['id'])

    def test_private_notes_only_owner_and_master(self):
        r = fresh('nota'); r.update(name='Nota', content='Privado')
        saved = self.store.put(self.p1, r, 0)['record']
        self.assertEqual([self.p1['id']], saved['owners'])
        self.assertEqual('Privado', self.store.get(self.master, r['id'])['content'])
        with self.assertRaises(Problem): self.store.get(self.p2, r['id'])

    def test_selected_audience(self):
        r = self.create('cheat_sheet', audience=[self.p2['id']])
        self.assertEqual(r['id'], self.store.get(self.p2, r['id'])['id'])
        with self.assertRaises(Problem): self.store.get(self.p1, r['id'])

    def test_revisions_and_exports_filter_private_fields(self):
        r = self.create(owners=[self.p1['id']], master_notes='NAO_REVELAR', sheet={'notas_mestre':'NAO_REVELAR'})
        r['summary'] = 'Público'; self.store.put(self.master, r, 1)
        for actor in [self.master, self.p1]:
            for fmt in ['md', 'html']:
                self.assertNotIn('NAO_REVELAR', self.store.export(actor, r['id'], fmt)[0])
        self.assertNotIn('NAO_REVELAR', json.dumps(self.store.revisions(self.p1, r['id'])))
        with self.assertRaises(Problem): self.store.export(self.p1, r['id'], 'md', True)
        self.assertIn('NAO_REVELAR', self.store.export(self.master, r['id'], 'md', True)[0])

    def test_hidden_connections_not_leaked(self):
        hidden = self.create('local')
        r = self.create(owners=[self.p1['id']], links=[hidden['id']])
        self.assertEqual([], self.store.get(self.p1, r['id'])['links'])
        self.assertNotIn(hidden['id'], json.dumps(self.store.revisions(self.p1, r['id'])))

    def test_conflicting_updates(self):
        r = self.create()
        def update(name):
            new = copy.deepcopy(r); new['name'] = name
            try: self.store.put(self.master, new, 1); return 'ok'
            except Problem as e: return e.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(update, ['A', 'B']))
        self.assertCountEqual(['ok', 409], result)

    def test_two_players_separate_records(self):
        a = self.create(owners=[self.p1['id']]); b = self.create(owners=[self.p2['id']])
        def update(item):
            user, record = item
            shown = self.store.get(user, record['id']); shown['summary'] = user['name']
            return self.store.put(user, shown, 1)['record']['summary']
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(update, [(self.p1, a), (self.p2, b)]))
        self.assertCountEqual(['jogador1', 'jogador2'], result)

    def test_bad_mechanics_and_explicit_house_rule(self):
        r = self.create(owners=[self.p1['id']])
        r['sheet'] = {'atributos': {'Força': 6}, 'recursos': {'fome': 6}}
        with self.assertRaises(Problem): self.store.put(self.master, r, 1)
        rule = self.create('regra', sheet={'limites': {'atributos': 6, 'fome': 6}})
        r['sheet']['regra_da_casa'] = rule['id']
        self.store.put(self.master, r, 1)
        shown = self.store.get(self.p1, r['id']); shown['sheet']['regra_da_casa'] = ''
        with self.assertRaises(Problem): self.store.put(self.p1, shown, 2)

    def test_past_change_returns_dependencies_without_rewriting(self):
        event = self.create('acontecimento', state='confirmado')
        plan = self.create('trama', links=[event['id']], content='Plano original')
        event['content'] = 'Passado alterado'
        changed = self.store.put(self.master, event, 1)
        self.assertEqual([plan['id']], changed['afetados'])
        self.assertEqual('Plano original', self.store.get(self.master, plan['id'])['content'])

    def test_revoke_account_sessions_and_preserve_history(self):
        r = self.create(owners=[self.p1['id']])
        token, _ = self.store.login('jogador1', 'senha-segura-123')
        self.store.revoke(self.master, self.p1['id'])
        with self.assertRaises(Problem): self.store.authenticate(token)
        r['archived'] = True
        self.store.put(self.master, r, 1)

    def test_snapshot_backup(self):
        r = self.create()
        path = Path(self.tmp.name)/'snapshot.sqlite3'
        self.store.backup(path)
        import sqlite3
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual('ok', db.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertEqual(r['id'], db.execute('SELECT id FROM records').fetchone()[0])

    def test_invalid_answer_atomic_no_proposal_or_message(self):
        answer = {'resposta':'Texto','fontes':['fonte-inventada'],'propostas':[]}
        with self.assertRaises(Problem): self.store.save_answer(self.master, 'Q', answer, [], 1, 'fake')
        self.assertEqual([], self.store.messages(self.master))
        self.assertEqual([], self.store.proposals(self.master))

    def test_proposal_edit_accept_and_stale_conflict(self):
        r = self.create()
        after = copy.deepcopy(r); after['summary'] = 'Proposto'
        answer = {'resposta':'Sugestão','fontes':[],'propostas':[{'alvo':r['id'],'versao':1,'motivo':'Melhorar','registro':after}]}
        self.store.save_answer(self.master, 'Q', answer, [], 1, 'fake')
        proposal = self.store.proposals(self.master)[0]
        self.assertEqual('', self.store.get(self.master, r['id'])['summary'])
        after['summary'] = 'Revisado pelo mestre'
        self.store.decide(self.master, proposal['id'], 'aceitar', after)
        self.assertEqual('Revisado pelo mestre', self.store.get(self.master, r['id'])['summary'])
        with self.assertRaises(Problem): self.store.decide(self.master, proposal['id'], 'aceitar')

    def test_pending_proposal_conflict_preserves_newer_record(self):
        r=self.create();after=copy.deepcopy(r);after['summary']='Proposta antiga'
        self.store.save_answer(self.master,'Q',{'resposta':'Texto','fontes':[],
            'propostas':[{'alvo':r['id'],'versao':1,'motivo':'M','registro':after}]},[],1,'fake')
        proposal=self.store.proposals(self.master)[0]
        r['summary']='Edição mais recente';self.store.put(self.master,r,1)
        with self.assertRaises(Problem) as error:self.store.decide(self.master,proposal['id'],'aceitar')
        self.assertEqual(409,error.exception.status)
        self.assertEqual('Edição mais recente',self.store.get(self.master,r['id'])['summary'])
        self.assertEqual('pendente',self.store.proposals(self.master)[0]['status'])

    def test_explicit_import_uses_snapshot_preserves_source_and_links(self):
        import hashlib,sqlite3
        from administrar import importar
        source=Path(self.tmp.name)/'origem.sqlite3'
        data={'personagens':[{'id':'pj-1','nome':'Original','descricao':'Ficha histórica'}],
              'locais':[{'id':'loc-1','nome':'Local','descricao':'Uma casa'}],
              'relacoes':[{'id':'rel-1','origem':'pj-1','destino':'loc-1'}]}
        with closing(sqlite3.connect(source)) as db:
            db.execute('CREATE TABLE estado(id INTEGER,dados TEXT)')
            db.execute('INSERT INTO estado VALUES(1,?)',(json.dumps(data),));db.commit()
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        result=importar(self.store,source,Path(self.tmp.name)/'snapshots')
        self.assertEqual(3,result['registros_importados'])
        self.assertEqual(before,hashlib.sha256(source.read_bytes()).hexdigest())
        relation=next(r for r in self.store.records(self.master) if r['kind']=='relacao')
        self.assertEqual(2,len(relation['links']))
        self.assertEqual([],self.store.records(self.p1))
        with self.assertRaises(ValueError):importar(self.store,source,Path(self.tmp.name)/'snapshots')


class AITests(Fixture):
    def setUp(self):
        super().setUp()
        self.calls = 0
        self.release = threading.Event()
        config = json.loads(((ROOT/'config.json') if (ROOT/'config.json').exists() else ROOT/'config.example.json').read_text())
        def fake(job, tool, profile, data):
            self.calls += 1
            while not self.release.wait(.01):
                if job.get('cancel_requested'):
                    return {'resposta':'Cancelado','fontes':[],'propostas':[]}
            return {'resposta':'Plano específico','fontes':[],'propostas':[]}
        self.tasks = Tasks(self.store, config, fake)
        self.addCleanup(self.release.set)

    def await_job(self, id):
        for _ in range(200):
            job = self.tasks.get(self.master, id)
            if self.tasks.active is None: return job
            time.sleep(.01)
        self.fail('Tarefa não encerrou')

    def test_no_implicit_inference(self):
        self.tasks.state(self.p1); self.store.records(self.master)
        self.assertEqual(0, self.calls)
        self.assertIsNone(self.tasks.active)

    def test_single_task_cancel_and_resume(self):
        id = self.tasks.start(self.master, {'pergunta':'Plano'})['id']
        with self.assertRaises(Problem): self.tasks.start(self.p1, {'pergunta':'Outro'})
        self.tasks.control(self.master, 'cancelar')
        self.assertEqual('cancelado', self.await_job(id)['status'])
        self.assertEqual([], self.store.messages(self.master))
        self.release.set()
        id = self.tasks.start(self.master, {'pergunta':'Outro'})['id']
        self.assertEqual('concluido', self.await_job(id)['status'])
        self.assertEqual(1, len(self.store.messages(self.master)))

    def test_player_can_use_ai_but_not_read_or_cancel_other_tasks(self):
        id = self.tasks.start(self.p1, {'pergunta':'Crie uma ficha'})['id']
        self.assertEqual(id,self.tasks.state(self.p1)['ativa'])
        self.assertIsNone(self.tasks.state(self.p2)['ativa'])
        self.assertTrue(self.tasks.state(self.p2)['ocupada'])
        with self.assertRaises(Problem): self.tasks.get(self.p2,id)
        with self.assertRaises(Problem): self.tasks.control(self.p2,'cancelar')
        self.release.set()
        self.assertEqual('concluido',self.await_job(id)['status'])
        self.assertEqual(1,len(self.store.messages(self.p1)))
        self.assertEqual([],self.store.messages(self.p2))
        self.assertEqual([],self.store.messages(self.master))

    def test_player_context_filters_secrets_and_conversation(self):
        own=self.create(owners=[self.p1['id']],master_notes='SECRET_MASTER',sheet={'notas_mestre':'SECRET_SHEET'})
        self.create('segredo',name='SECRET_ENTITY')
        self.create(owners=[self.p2['id']],name='SECRET_OTHER')
        world=self.create('npc',name='WORLD_NPC',all_players=True)
        self.create('sessao',name='WORLD_PLAN',all_players=True)
        captured=[]
        def fake(job,tool,profile,data):
            captured.append(data)
            return {'resposta':'Seguro','fontes':[],'propostas':[]}
        self.tasks.transport=fake
        id=self.tasks.start(self.p1,{'pergunta':'Planejar minha ficha','selecionados':[own['id']]})['id']
        self.await_job(id)
        raw=json.dumps(captured,ensure_ascii=False)
        for secret in ['SECRET_MASTER','SECRET_SHEET','SECRET_ENTITY','SECRET_OTHER','WORLD_NPC','WORLD_PLAN']:
            self.assertNotIn(secret,raw)
        self.assertNotIn('titulo',captured[0]['campanha'])
        with self.assertRaises(Problem):self.tasks.start(self.p2,{'pergunta':'Q','selecionados':[own['id']]})
        with self.assertRaises(Problem):self.tasks.start(self.p1,{'pergunta':'Q','selecionados':[world['id']]})

    def test_player_cannot_request_master_tools_or_large_model(self):
        for options in [{'papel':'planejador'},{'papel':'continuidade'},{'perfil':'extenso'}]:
            with self.assertRaises(Problem):self.tasks.start(self.p1,{'pergunta':'Q',**options})
        self.assertEqual(0,self.calls)
        self.assertEqual(['conversa'],list(self.tasks.state(self.p1)['modelos']))
        self.assertIn('extenso',self.tasks.state(self.master)['modelos'])

    def test_player_consultation_cannot_save_character_proposal(self):
        record=fresh('personagem');record['name']='Não solicitado'
        self.tasks.transport=lambda *args:{'resposta':'Proposta','fontes':[], 'propostas':[{'alvo':'','versao':0,'motivo':'Q','registro':record}]}
        id=self.tasks.start(self.p1,{'pergunta':'Explique esta regra','papel':'consultor'})['id']
        self.assertEqual('falhou',self.await_job(id)['status'])
        self.assertEqual([],self.store.messages(self.p1))

    def test_player_cannot_select_more_than_four_references(self):
        with self.assertRaises(Problem):self.tasks.start(self.p1,{'pergunta':'Q','selecionados':['x']*5})

    def test_observed_rule_error_gets_one_repair_before_save(self):
        calls=[]
        def fake(job,tool,profile,data):
            calls.append(data)
            text='Vitória crítica (vitória por uma margem significativa).' if len(calls)==1 else 'Vitória crítica exige vencer com um par de 10.'
            return {'resposta':text,'fontes':[],'propostas':[]}
        self.tasks.transport=fake
        id=self.tasks.start(self.p1,{'pergunta':'Explique um crítico','papel':'consultor'})['id']
        job=self.await_job(id)
        self.assertEqual('concluido',job['status'])
        self.assertEqual(1,job['reparos'])
        self.assertEqual(2,len(calls))
        self.assertIn('correcao_obrigatoria',calls[1])
        self.assertNotIn('margem significativa',self.store.messages(self.p1)[0]['resposta'])


class HTTPTests(Fixture):
    def setUp(self):
        super().setUp()
        config = json.loads(((ROOT/'config.json') if (ROOT/'config.json').exists() else ROOT/'config.example.json').read_text())
        self.server = make_server(self.store, config, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.base = 'http://127.0.0.1:'+str(self.server.server_port)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self, path, data=None, token=None, csrf=None, headers=None):
        options = {'Content-Type':'application/json'}
        if token: options['Cookie']='rpg_session='+token
        if csrf: options['X-CSRF']=csrf
        options.update(headers or {})
        req = urllib.request.Request(self.base+path, None if data is None else json.dumps(data).encode(), options)
        try:
            response = urllib.request.urlopen(req, timeout=5)
            return response.status, response.read().decode(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode(), error.headers

    def test_auth_csrf_origin_and_secrets_direct_api(self):
        r = self.create(owners=[self.p1['id']], master_notes='SECRETO')
        token, logged = self.store.login('jogador1','senha-segura-123')
        self.assertEqual(401, self.request('/api/registros')[0])
        status, body, _ = self.request('/api/registros', token=token)
        self.assertEqual(200, status); self.assertNotIn('SECRETO', body)
        self.assertEqual(403, self.request('/api/registro', {'registro':r,'versao':1}, token=token)[0])
        self.assertEqual(200, self.request('/api/buscar?q=fome', token=token)[0])
        self.assertEqual(200, self.request('/api/propostas', token=token)[0])
        self.assertEqual(403, self.request('/api/logout', {}, token, logged['csrf'], {'Origin':'http://evil.example'})[0])
        self.assertEqual(403, self.request('/api/me', token=token, headers={'Host':'evil.example'})[0])
        self.assertEqual(200, self.request('/api/logout', {}, token, logged['csrf'])[0])
        self.assertEqual(401, self.request('/api/me', token=token)[0])

    def test_interface_available_without_ollama(self):
        for path in ['/', '/app.js', '/style.css', '/api/status']:
            self.assertEqual(200, self.request(path)[0])
        self.assertIsNone(self.server.tasks.active)

    def test_player_master_capabilities_rejected_by_direct_http(self):
        token,logged=self.store.login('jogador1','senha-segura-123')
        npc=self.create('npc',all_players=True)
        for options in [{'papel':'planejador'},{'papel':'continuidade'},{'perfil':'extenso'},{'selecionados':[npc['id']]}]:
            status,_,_=self.request('/api/ia/tarefa',{'pergunta':'Q',**options},token,logged['csrf'])
            self.assertEqual(403,status)
        self.assertIsNone(self.server.tasks.active)

    def test_remote_setup_rejected(self):
        self.assertEqual(403, self.request('/api/setup', {'name':'new','password':'senha-segura-123'}, headers={'Tailscale-User-Login':'remote@example.org'})[0])

    def test_http_export_and_revision_visibility(self):
        r = self.create(owners=[self.p1['id']], master_notes='SECRETO')
        token, _ = self.store.login('jogador2','senha-segura-123')
        for path in ['/api/exportar?id='+r['id'], '/api/revisoes?id='+r['id']]:
            status, body, _ = self.request(path, token=token)
            self.assertEqual(404, status); self.assertNotIn('SECRETO', body)


if __name__ == '__main__':
    unittest.main()
