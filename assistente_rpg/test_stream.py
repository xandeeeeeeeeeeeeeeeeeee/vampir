"""Ollama simulado por HTTP: valida streaming e descarregamento sem GPU."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import tempfile
import threading
import time
import unittest

from core import ROOT, Store
from ai import Tasks


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.master = self.store.create_user(None,'teste','somente-testes-123')
        self.requests=[];self.release=threading.Event();self.mode='ok'
        fixture=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.requests.append((self.path,body))
                self.send_response(200);self.end_headers()
                if self.path=='/api/generate':self.wfile.write(b'{}');return
                if fixture.mode=='cancel':
                    fixture.release.wait(2)
                answer={'resposta':'Resposta de teste','fontes':[],'propostas':[]}
                if fixture.mode=='bad_source':answer['fontes']=['inventada']
                raw=json.dumps(answer)
                try:
                    for chunk in [{'message':{'content':raw[:12]}},
                                  {'message':{'content':raw[12:]}},
                                  {'done':True,'done_reason':'length' if fixture.mode=='length' else 'stop'}]:
                        self.wfile.write((json.dumps(chunk)+'\n').encode());self.wfile.flush()
                except (BrokenPipeError,ConnectionResetError):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        config=json.loads(((ROOT/'config.json') if (ROOT/'config.json').exists() else ROOT/'config.example.json').read_text(encoding='utf-8'))
        config['ollama']='http://127.0.0.1:'+str(self.server.server_port)
        self.tasks=Tasks(self.store,config)

    def stop(self):
        self.release.set();self.server.shutdown();self.server.server_close();self.thread.join()

    def start(self,profile='conversa'):
        return self.tasks.start(self.master,{'pergunta':'Planeje','perfil':profile})['id']

    def wait(self,id):
        for _ in range(400):
            if self.tasks.active is None:return self.tasks.get(self.master,id)
            time.sleep(.01)
        self.fail('Tarefa não terminou')

    def test_stream_and_unload(self):
        job=self.wait(self.start())
        self.assertEqual('concluido',job['status'])
        self.assertIn('Resposta de teste',job['parcial'])
        self.assertEqual(['/api/chat','/api/generate'],[x[0] for x in self.requests])
        self.assertEqual(0,self.requests[0][1]['keep_alive'])
        self.assertEqual(0,self.requests[1][1]['keep_alive'])
        self.assertFalse(self.requests[0][1]['think'])

    def test_extensive_profile_is_explicit(self):
        self.wait(self.start('extenso'))
        self.assertEqual('gemma4:26b-a4b-it-qat',self.requests[0][1]['model'])
        self.assertTrue(self.requests[0][1]['think'])
        self.assertEqual(6000,self.requests[0][1]['options']['num_predict'])

    def test_player_schema_only_allows_personal_creation(self):
        player=self.store.create_user(self.master,'jogador','somente-testes-123')
        for tool in ['consultor','criador','conversa']:
            id=self.tasks.start(player,{'pergunta':'Ajude minha ficha','papel':tool})['id']
            self.wait(id)
            schema=self.requests[-2][1]['format']['properties']['propostas']
            self.assertEqual(['personagem','nota','cheat_sheet'],schema['items']['properties']['registro']['properties']['kind']['enum'])
            if tool!='criador':self.assertEqual(0,schema['maxItems'])

    def test_invalid_source_and_truncation_do_not_save(self):
        for mode in ['bad_source','length']:
            self.mode=mode
            job=self.wait(self.start())
            self.assertEqual('falhou',job['status'])
            self.assertEqual([],self.store.messages(self.master))
            self.assertEqual([],self.store.records(self.master))

    def test_cancel_before_first_token_closes_and_unloads(self):
        self.mode='cancel';id=self.start()
        for _ in range(100):
            if self.requests:break
            time.sleep(.01)
        self.tasks.control(self.master,'cancelar')
        job=self.wait(id)
        self.assertEqual('cancelado',job['status'])
        self.assertEqual([],self.store.messages(self.master))
        self.assertEqual('/api/generate',self.requests[-1][0])

    def test_schema_limits_citations_to_actually_supplied_sources(self):
        self.wait(self.start())
        body=self.requests[0][1]
        self.assertEqual(0,body['format']['properties']['fontes']['maxItems'])
        sheet=body['format']['properties']['propostas']['items']['properties']['registro']['properties']['sheet']
        self.assertFalse(sheet['additionalProperties'])
        self.assertEqual([''],body['format']['properties']['propostas']['items']['properties']['alvo']['enum'])

    def test_explicit_text_only_request_disallows_proposals(self):
        task=self.tasks.start(self.master,{'pergunta':'Identifique a contradição. Não altere o passado.', 'papel':'continuidade'})['id']
        self.wait(task)
        self.assertEqual(0,self.requests[0][1]['format']['properties']['propostas']['maxItems'])

    def test_context_budget_preserves_selected_record_and_primary_rule(self):
        job={'modelo':'gemma4:26b-a4b-it-qat'}
        data={'pedido':'Planeje','perfil_usuario':'mestre','campanha':{},
            'selecao_explicita':['principal'],'registros':[{'id':'principal','content':'Selecionado'}],
            'historico':[{'resposta':'histórico '*1800}],
            'fontes':[{'id':'regra-principal','texto':'Texto completo da regra.'},
                      {'id':'secundaria','texto':'secundário '*2500}]}
        self.tasks.ollama(job,'consultor','extenso',data)
        sent=json.loads(self.requests[0][1]['messages'][1]['content'])
        self.assertEqual('principal',sent['registros'][0]['id'])
        self.assertEqual(['regra-principal'],job['fontes_enviadas'])
        self.assertEqual(['regra-principal'],self.requests[0][1]['format']['properties']['fontes']['items']['enum'])

    def test_context_budget_drops_whole_secondary_sections(self):
        job={'modelo':'gemma4:26b-a4b-it-qat'}
        data={'pedido':'Consulte','perfil_usuario':'mestre','campanha':{},'registros':[],'historico':[],
              'fontes':[{'id':'a','grupo_contexto':'principal','texto':'Regra.'},
                        {'id':'b','grupo_contexto':'principal','texto':'Exceção.'},
                        {'id':'c','grupo_contexto':'secundario','texto':'Outros '*4000},
                        {'id':'d','grupo_contexto':'secundario','texto':'Exemplo.'}]}
        self.tasks.ollama(job,'consultor','extenso',data)
        self.assertEqual(['a','b'],job['fontes_enviadas'])

    def test_practical_hunger_context_fits_without_cutting_rule(self):
        import biblioteca
        sources=biblioteca.recuperar(['p0207-t003','p0122-t004','p0208-t001','p0209-t001','p0209-t002'])
        job={'modelo':'gemma4:12b-it-qat'}
        data={'pedido':'Explique os dados de Fome','perfil_usuario':'mestre','campanha':{},
              'selecao_explicita':['ficha','regra'],'registros':[{'id':'ficha','content':'Ficha pessoal '*180},
              {'id':'regra','content':'Acordo de interpretação'}]+[{'id':str(i),'content':'Contexto secundário '*130} for i in range(6)],
              'historico':[{'resposta':'Histórico '*200}],'fontes':sources}
        self.tasks.ollama(job,'consultor','conversa',data)
        sent=json.loads(self.requests[0][1]['messages'][1]['content'])
        ids={s['id'] for s in sent['fontes']}
        self.assertTrue({'p0208-t002','p0209-t001','p0209-t002'}<=ids)
        for source in sent['fontes']:
            self.assertEqual(next(s['texto'] for s in sources if s['id']==source['id']),source['texto'])


if __name__=='__main__':unittest.main()
