import copy
from test_assistente import Fixture
from core import fresh, Problem


class PlayerProposals(Fixture):
    def answer(self, record, target='', version=0):
        return {'resposta':'Proposta pessoal','fontes':[], 'propostas':[
            {'alvo':target,'versao':version,'motivo':'Pedido do jogador','registro':record}]}

    def test_player_creates_accepts_private_sheet_and_material(self):
        for kind in ['personagem','cheat_sheet','nota']:
            record=fresh(kind);record.update(name='Meu material',all_players=True,owners=[self.p2['id']])
            record['sheet']={'atributos':{'Força':2}} if kind=='personagem' else {}
            self.store.save_answer(self.p1,'Criar',self.answer(record),[],1,'fake')
            proposal=self.store.proposals(self.p1)[-1]
            self.assertEqual([],self.store.proposals(self.p2))
            with self.assertRaises(Problem):self.store.decide(self.p2,proposal['id'],'aceitar')
            result=self.store.decide(self.p1,proposal['id'],'aceitar')['resultado']['record']
            self.assertEqual([self.p1['id']],result['owners'])
            self.assertFalse(result['all_players'])
            self.assertEqual([],self.store.records(self.p2))

    def test_other_world_changes_require_master(self):
        record=fresh('npc');record['name']='Ideia de NPC'
        with self.assertRaises(Problem):self.store.save_answer(self.p1,'Ideia',self.answer(record),[],1,'fake')
        self.assertEqual([],self.store.messages(self.p1))
        self.assertEqual([],self.store.records(self.master))
        self.store.save_answer(self.master,'Ideia',self.answer(record),[],1,'fake')
        proposal=self.store.proposals(self.master)[0]
        self.store.decide(self.master,proposal['id'],'aceitar')
        self.assertEqual('Ideia de NPC',self.store.records(self.master)[0]['name'])

    def test_ai_cannot_edit_other_shared_character(self):
        record=self.create(owners=[self.p2['id']],all_players=True)
        with self.assertRaises(Problem):self.store.save_answer(self.p1,'Editar',self.answer(record,record['id'],1),[],1,'fake')
        self.assertEqual([],self.store.messages(self.p1))

    def test_player_proposal_edit_preserves_master_notes_and_assignments(self):
        record=self.create(owners=[self.p1['id']],master_notes='SEGREDO',sheet={'notas_mestre':'PRIVADO'})
        shown=self.store.get(self.p1,record['id'])
        proposed=copy.deepcopy(record);proposed['summary']='Minha edição'
        self.store.save_answer(self.p1,'Editar',self.answer(proposed,record['id'],1),[],1,'fake')
        proposal=self.store.proposals(self.p1)[0]
        self.assertNotIn('SEGREDO',str(proposal));self.assertNotIn('PRIVADO',str(proposal))
        self.store.decide(self.p1,proposal['id'],'aceitar')
        actual=self.store.get(self.master,record['id'])
        self.assertEqual('SEGREDO',actual['master_notes'])
        self.assertEqual('PRIVADO',actual['sheet']['notas_mestre'])
        self.assertEqual([self.p1['id']],actual['owners'])

    def test_invisible_links_rejected_and_legacy_conversations_hidden(self):
        hidden=self.create('segredo')
        note=fresh('nota');note.update(name='Nota',links=[hidden['id']])
        with self.assertRaises(Problem):self.store.save_answer(self.p1,'Q',self.answer(note),[],1,'fake')
        self.store.save_answer(self.master,'Plano privado',{'resposta':'SEGREDO','fontes':[],'propostas':[]},[],1,'fake')
        self.assertEqual([],self.store.messages(self.p1))
