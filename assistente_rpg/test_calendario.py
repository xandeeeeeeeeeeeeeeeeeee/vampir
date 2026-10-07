from test_assistente import Fixture
from core import fresh, Problem
import calendario


class CampaignCalendar(Fixture):
    def test_dates_references_visibility_and_export(self):
        known=self.create('local',name='Biblioteca',all_players=True)
        hidden=self.create('segredo',name='SEGREDO_DO_TESTE')
        event=self.create('acontecimento',name='Encontro',date='2026-10-07 · 22h',all_players=True,master_notes='PLANO_PRIVADO',links=[known['id'],hidden['id']])
        self.create('sessao',name='Sessão privada',date='2026-10-09',master_notes='SEGREDO_SESSAO')
        self.create('sessao',name='Sem dia escolhido',date='amanhã',all_players=True)
        self.create('sessao',name='Novembro',date='2026-11-01',all_players=True)
        self.create('nota',name='Nota pessoal',date='2026-10-07',owners=[self.p1['id']])
        gm=calendario.obter(self.store,self.master,'2026-10')
        p1=calendario.obter(self.store,self.p1,'2026-10')
        p2=calendario.obter(self.store,self.p2,'2026-10')
        self.assertEqual(31,gm['dias']);self.assertEqual(3,len(gm['eventos']))
        self.assertEqual(2,len(p1['eventos']));self.assertEqual(1,len(p2['eventos']))
        ref=next(e for e in p1['eventos'] if e['registro']['name']=='Encontro')['referencias']
        self.assertEqual(['Biblioteca'],[r['nome'] for r in ref])
        export=calendario.exportar(p1)
        for secret in ['PLANO_PRIVADO','SEGREDO_DO_TESTE','SEGREDO_SESSAO']:self.assertNotIn(secret,export)
        self.assertEqual(1,len(p1['sem_data']))
        self.assertEqual(p2['eventos'],calendario.obter(self.store,self.master,'2026-10','jogadores')['eventos'])
        with self.assertRaises(Problem):calendario.obter(self.store,self.p1,'2026-10','jogadores')

    def test_invalid_month_and_archived_items(self):
        for month in ['2026-13','0000-01','<script>','2026-1']:
            with self.assertRaises(Problem):calendario.obter(self.store,self.master,month)
        self.create('sessao',name='Arquivada',date='2026-10-07',archived=True)
        self.assertEqual([],calendario.obter(self.store,self.master,'2026-10')['eventos'])

    def test_player_can_date_own_note_without_changing_world(self):
        r=fresh('nota');r.update(name='Minha noite',date='2026-10-07')
        created=self.store.put(self.p1,r,0)['record']
        self.assertEqual('2026-10-07',created['date'])
        created['date']='2026-10-08';self.store.put(self.p1,created,1)
        p=self.store.get(self.p1,created['id']);self.assertEqual('2026-10-08',p['date'])
        self.assertEqual([],calendario.obter(self.store,self.p2,'2026-10')['eventos'])
