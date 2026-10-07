import copy
from test_assistente import Fixture
from core import fresh, Problem
import fichas
import cartografia
import biblioteca


class CompleteSheets(Fixture):
    def test_seven_clans_have_every_stage_and_matching_sources(self):
        for clan in fichas.CLANS:
            s=fichas.modelo('desenvolvedor',clan);fichas.validar(s)
            self.assertEqual(27,len(s['habilidades']))
            self.assertEqual(3,len(s['criacao']['poderes']))
            for v in s['criacao']['vantagens']:
                self.assertIn(v['nome'],fichas.consultar.obter(v['fonte'])[0]['titulo'])
            r=fresh('personagem');r.update(name='Completo '+clan,sheet=s)
            self.store.put(self.master,r,0)

    def test_rejects_missing_steps_and_wrong_budgets(self):
        for mutate in [lambda s:s['criacao'].pop('conviccoes'),lambda s:s['criacao']['vantagens'][0].update(pontos=7),lambda s:s['habilidades'].pop('Ofícios'),lambda s:s['criacao']['especializacoes'].clear(),lambda s:s['recursos'].update(vitalidade=12),lambda s:s['criacao']['poderes'][0].update(nome='Poder inventado')]:
            s=fichas.modelo('software','Malkavian');mutate(s)
            with self.assertRaises(Problem):fichas.validar(s)

    def test_full_request_is_default_partial_is_explicit(self):
        self.assertTrue(fichas.completa('Crie uma ficha de Malkavian'))
        self.assertTrue(fichas.completa('Complete uma ficha'))
        self.assertFalse(fichas.completa('Crie uma ficha parcial'))
        self.assertFalse(fichas.completa('Crie uma ficha; preencha apenas Tecnologia 3'))
        with self.assertRaises(Problem):fichas.perfil('Crie uma ficha ancilla Ventrue')

    def test_persona_only_transport_cannot_invent_mechanics(self):
        persona={'nome':'Jorge','conceito':'Desenvolvedor','historico':'Jorge trabalhava como desenvolvedor de software e valorizava a precisão dos sistemas que construía. Depois do Abraço, deseja compreender sua nova condição e preservar as amizades humanas que lhe davam perspectiva. Seu passado pessoal é uma proposta para revisão, sem determinar os acontecimentos futuros da campanha.'}
        answer=fichas.finalizar(fichas.da_persona(persona,'Crie uma ficha Malkavian de software',[],[]),'Crie uma ficha Malkavian de software')
        self.assertEqual(27,len(answer['propostas'][0]['registro']['sheet']['habilidades']))
        with self.assertRaises(Problem):fichas.da_persona({'nome':'Jorge','conceito':'Dev','historico':''},'Crie uma ficha',[],[])

    def test_complete_existing_keeps_attributes_skills_and_notes(self):
        r=fresh('personagem');r['sheet']={'cla':'Malkavian','atributos':{'Força':2},'habilidades':{'Tecnologia':3,'Investigação':2},'notas':'Minha nota','notas_mestre':'Segredo'}
        full=fichas.completar_existente(r)
        self.assertEqual(2,full['sheet']['atributos']['Força'])
        self.assertEqual(2,full['sheet']['habilidades']['Investigação'])
        self.assertEqual('Segredo',full['sheet']['notas_mestre'])
        self.assertEqual('Minha nota',full['sheet']['notas'])
        fichas.validar(full['sheet'])

    def test_ai_note_edit_does_not_remove_complete_creation(self):
        r=self.create(owners=[self.p1['id']],sheet=fichas.modelo('software','Malkavian'))
        edit=copy.deepcopy(r);edit['sheet']={'notas':'Minha nova nota'}
        answer={'resposta':'Nota proposta','fontes':[],'propostas':[{'alvo':r['id'],'versao':r['version'],'motivo':'Editar nota','registro':edit}]}
        self.store.save_answer(self.p1,'Anote',answer,[],1,'fake')
        p=self.store.proposals(self.p1)[0]
        self.store.decide(self.p1,p['id'],'aceitar')
        actual=self.store.get(self.p1,r['id'])
        fichas.validar(actual['sheet']);self.assertEqual('Minha nova nota',actual['sheet']['notas'])

    def test_finalizer_and_player_export_preserve_complete_fields(self):
        r=fresh('personagem');r.update(name='Renato',sheet={'cla':'Malkavian','conceito':'Desenvolvedor','historico':'Abraço recente.','habilidades':{'Tecnologia':4}})
        answer=fichas.finalizar({'resposta':'Ficha','fontes':[],'propostas':[{'alvo':'','versao':0,'motivo':'Criação completa','registro':r}]},'Crie uma ficha de desenvolvedor Malkavian')
        result=self.store.save_answer(self.p1,'Ficha',answer,r['sources'],1,'fake')
        p=self.store.proposals(self.p1)[0]
        record=self.store.decide(self.p1,p['id'],'aceitar')['resultado']['record']
        exported=self.store.export(self.p1,record['id'],'md')[0]
        for key in ['especializacoes','conviccoes','poderes','vantagens','defeitos']:self.assertIn(key,exported)
        self.assertEqual([],self.store.records(self.p2))


class CityMap(Fixture):
    def test_city_is_idempotent_and_private_sites_stay_hidden(self):
        cartografia.iniciar(self.store,self.master)
        self.assertEqual([],cartografia.iniciar(self.store,self.master)['criados'])
        gm=cartografia.obter(self.store,self.master)
        player=cartografia.obter(self.store,self.p1)
        preview=cartografia.obter(self.store,self.master,'jogadores')
        self.assertEqual(12,len(gm['registros']));self.assertEqual(11,len(player['registros']))
        self.assertEqual(player['registros'],preview['registros'])
        self.assertNotIn('Refúgio Oculto',cartografia.exportar(player))
        self.assertNotIn('rota subterrânea',cartografia.exportar(player))
        self.assertIn('rota subterrânea',cartografia.exportar(gm))
        with self.assertRaises(Problem):cartografia.obter(self.store,self.p1,'jogadores')
        with self.assertRaises(Problem):cartografia.iniciar(self.store,self.p1)

    def test_targeted_sharing_archiving_and_geometry(self):
        r=fresh('local');r.update(name='Local de Ana',audience=[self.p1['id']],master_notes='SEGREDO',sheet={'cartografia':{'tipo':'local','x':1,'y':2}})
        self.store.put(self.master,r,0)
        self.assertEqual(1,len(cartografia.obter(self.store,self.p1)['registros']))
        self.assertEqual([],cartografia.obter(self.store,self.p2)['registros'])
        self.assertEqual([],cartografia.obter(self.store,self.master,'jogadores')['registros'])
        r=self.store.get(self.master,r['id']);r['archived']=True;self.store.put(self.master,r,1)
        self.assertEqual([],cartografia.obter(self.store,self.p1)['registros'])
        with self.assertRaises(Problem):cartografia.validar({'tipo':'distrito','x':90,'y':50,'largura':20})
        with self.assertRaises(Problem):cartografia.validar({'tipo':'local','x':float('nan')})

    def test_printed_references_open_page_and_can_expand_section(self):
        page=biblioteca.pagina(172)
        self.assertTrue(page['trechos'])
        self.assertEqual('pagina',page['escopo'])
        for r in page['trechos']:self.assertTrue(biblioteca.contexto(r['id'])['trechos'])
        with self.assertRaises(Problem):biblioteca.pagina(999)
