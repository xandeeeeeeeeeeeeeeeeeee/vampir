"""HTTP local autenticado. Acesso remoto somente pelo proxy privado configurado."""
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import threading
import time
import urllib.parse

from core import ROOT, Problem, Store, consultar, require_master
from ai import Tasks
import biblioteca
import cartografia
import fichas
import calendario


def make_server(store, config, tasks=None, port=None):
    tasks = tasks or Tasks(store, config)
    attempts = {}
    attempts_lock = threading.Lock()
    configured_port = config['porta'] if port is None else port

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # No request bodies, passwords, tokens or model content in logs.
            if self.command != 'GET':
                super().log_message(fmt, *args)

        def reply(self, data, status=200, mime='application/json; charset=utf-8', cookie=None):
            body = (json.dumps(data, ensure_ascii=False) if mime.startswith('application/json') else data).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'same-origin')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(body)

        def origin_check(self, mutating=False):
            hosts = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
            remote = config.get('host_remoto', '').strip()
            if remote:
                hosts.add(remote)
            host = self.headers.get('Host', '')
            if host not in hosts:
                raise Problem('Host recusado.', 403)
            origin = self.headers.get('Origin')
            expected = ('https://' if remote and host == remote else 'http://')+host
            if origin is not None and origin != expected:
                raise Problem('Origem recusada.', 403)
            if mutating and self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise Problem('Solicitação externa recusada.', 403)

        def token(self):
            cookie = SimpleCookie()
            cookie.load(self.headers.get('Cookie', ''))
            return cookie['rpg_session'].value if 'rpg_session' in cookie else ''

        def user(self, mutating=False):
            user = store.authenticate(self.token())
            if mutating and not hmac.compare_digest(user['csrf'], self.headers.get('X-CSRF', '')):
                raise Problem('Sessão precisa ser atualizada.', 403)
            return user

        def read(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 250000:
                    raise Problem('Pedido muito grande ou vazio.')
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise Problem('Envie um objeto JSON.')
                return value
            except (ValueError, TypeError):
                raise Problem('JSON inválido.')

        def do_GET(self):
            try:
                self.origin_check()
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                if path in ['/', '/app.js', '/style.css']:
                    name = {'/': 'interface.html', '/app.js': 'app.js', '/style.css': 'style.css'}[path]
                    mime = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8', '/style.css': 'text/css; charset=utf-8'}[path]
                    return self.reply((ROOT/name).read_text(encoding='utf-8'), mime=mime)
                if path == '/api/status':
                    return self.reply({'configurado': store.initialized(), 'versao': 2, 'ia_jogadores': True})
                user = self.user()
                query = urllib.parse.parse_qs(parsed.query)
                if path == '/api/me':
                    return self.reply(user)
                if path == '/api/campanha':
                    return self.reply(store.campaign(user))
                if path in ['/api/mapa','/api/mapa/exportar']:
                    atlas=cartografia.obter(store,user,query.get('visao',['atual'])[0])
                    if path.endswith('/exportar'):return self.reply(cartografia.exportar(atlas),mime='text/html; charset=utf-8')
                    return self.reply(atlas)
                if path in ['/api/calendario','/api/calendario/exportar']:
                    value=calendario.obter(store,user,query.get('mes',[''])[0],query.get('visao',['atual'])[0])
                    if path.endswith('/exportar'):return self.reply(calendario.exportar(value),mime='text/html; charset=utf-8')
                    return self.reply(value)
                if path == '/api/registros':
                    return self.reply(store.records(user, query.get('arquivados') == ['1']))
                if path == '/api/contas':
                    return self.reply(store.users(user))
                if path == '/api/revisoes':
                    return self.reply(store.revisions(user, query.get('id', [''])[0]))
                if path == '/api/exportar':
                    text, mime = store.export(user, query.get('id', [''])[0], query.get('formato', ['md'])[0], query.get('privado') == ['1'])
                    # Export HTML uses no external resources; printing available via browser menu.
                    return self.reply(text, mime=mime)
                if path == '/api/mensagens':
                    return self.reply(store.messages(user))
                if path == '/api/propostas':
                    return self.reply(store.proposals(user))
                if path == '/api/ia':
                    return self.reply(tasks.state(user))
                if path.startswith('/api/tarefa/'):
                    return self.reply(tasks.get(user, path.rsplit('/', 1)[-1]))
                if path == '/api/buscar':
                    return self.reply(biblioteca.buscar(query.get('q', [''])[0]))
                if path == '/api/pagina':
                    return self.reply(biblioteca.pagina(int(query.get('numero',['0'])[0]),query.get('tipo',['impressa'])[0]))
                if path in ['/api/trecho','/api/contexto']:
                    context=biblioteca.contexto(query.get('id', [''])[0],query.get('escopo',['secao'])[0])
                    return self.reply(context['trechos'] if path=='/api/trecho' else context)
                raise Problem('Não encontrado.', 404)
            except Problem as error:
                self.reply({'erro': str(error)}, error.status)
            except (ValueError, KeyError, TypeError):
                self.reply({'erro': 'Parâmetros inválidos.'}, 400)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            try:
                self.origin_check(True)
                data = self.read()
                if self.path == '/api/setup':
                    # Bootstrap only through the local browser, never the remote proxy host.
                    if self.headers.get('Host') not in {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'} or self.headers.get('Tailscale-User-Login'):
                        raise Problem('Configure o primeiro acesso no computador do mestre.', 403)
                    return self.reply(store.create_user(None, data.get('name'), data.get('password')), 201)
                if self.path == '/api/login':
                    key = self.headers.get('Tailscale-User-Login', self.client_address[0])
                    with attempts_lock:
                        recent = [t for t in attempts.get(key, []) if time.time()-t < 60]
                        if len(recent) >= 8:
                            raise Problem('Aguarde um minuto antes de tentar novamente.', 429)
                        attempts[key] = recent + [time.time()]
                    token, user = store.login(data.get('name', ''), data.get('password', ''))
                    secure = '; Secure' if self.headers.get('Host') == config.get('host_remoto') else ''
                    return self.reply(user, cookie='rpg_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'+secure)
                user = self.user(True)
                if self.path == '/api/logout':
                    store.logout(self.token())
                    return self.reply({'ok': True}, cookie='rpg_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if self.path == '/api/campanha':
                    return self.reply(store.campaign(user, data))
                if self.path == '/api/registro':
                    return self.reply(store.put(user, data['registro'], data['versao']))
                if self.path == '/api/mapa/iniciar':
                    return self.reply(cartografia.iniciar(store,user))
                if self.path == '/api/ficha/completa':
                    from core import fresh
                    name=data.get('nome','');clan=data.get('cla','');concept=data.get('conceito','')
                    if not isinstance(name,str) or not name.strip() or len(name)>160 or clan not in fichas.CLANS or not isinstance(concept,str) or not concept.strip() or len(concept)>2000:
                        raise Problem('Informe nome, clã básico e conceito para a ficha completa.')
                    r=fresh('personagem');r.update(name=name.strip(),summary=concept, sheet=fichas.modelo(concept,clan))
                    r['sheet']['conceito']=concept;r['sources']=fichas.fontes(r['sheet'])
                    r['content']='Criação inicial completa por pacote local, sem inferência. Personalize escolhas e vínculos antes de aceitar.'
                    answer={'resposta':'Ficha inicial completa proposta. Confira as escolhas padrão antes de aceitar.','fontes':r['sources'],
                            'propostas':[{'alvo':'','versao':0,'motivo':'Criação completa solicitada; escolhas padrão revisáveis','registro':r}]}
                    from ai import apresentar_resposta
                    return self.reply(store.save_answer(user,'Ficha completa: '+name,apresentar_resposta(answer),r['sources'],0,'pacote-local'))
                if self.path == '/api/ficha/completar':
                    before=store.get(user,data.get('id',''))
                    if before['kind']!='personagem' or before['archived'] or (user['role']!='mestre' and user['id'] not in before['owners']):
                        raise Problem('Você só pode completar suas próprias fichas ativas.',403)
                    r=fichas.completar_existente(before)
                    answer={'resposta':'Complemento completo proposto; confira as novas escolhas.', 'fontes':r['sources'],
                            'propostas':[{'alvo':before['id'],'versao':before['version'],'motivo':'Completar etapas preservando escolhas iniciais existentes','registro':r}]}
                    from ai import apresentar_resposta
                    return self.reply(store.save_answer(user,'Completar ficha: '+r['name'],apresentar_resposta(answer),r['sources'],0,'pacote-local'))
                if self.path == '/api/restaurar':
                    return self.reply(store.restore(user, data['id'], data['revisao'], data['versao']))
                if self.path == '/api/conta':
                    return self.reply(store.create_user(user, data.get('name'), data.get('password')), 201)
                if self.path == '/api/revogar':
                    store.revoke(user, data['id'])
                    return self.reply({'ok': True})
                if self.path == '/api/decidir':
                    return self.reply(store.decide(user, data['id'], data['acao'], data.get('registro')))
                if self.path == '/api/ia/controle':
                    return self.reply(tasks.control(user, data['acao']))
                if self.path == '/api/ia/tarefa':
                    return self.reply(tasks.start(user, data), 202)
                raise Problem('Não encontrado.', 404)
            except Problem as error:
                self.reply({'erro': str(error)}, error.status)
            except (ValueError, KeyError, TypeError):
                self.reply({'erro': 'Parâmetros inválidos.'}, 400)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', configured_port), Handler)
    server.tasks = tasks
    return server


if __name__ == '__main__':
    config = json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    from materiais import instalar
    store = Store(ROOT/'dados')
    instalar(store)
    server = make_server(store, config)
    print(f'Assistente: http://127.0.0.1:{server.server_port} — IA sob demanda; nenhum modelo iniciado.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
