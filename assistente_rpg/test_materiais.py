from test_assistente import Fixture
from materiais import instalar, GUIDES
from ai import record_schema, conferir_regra_observada, apresentar_resposta
from core import Problem


class MaterialsTests(Fixture):
    def test_player_guide_policy_update_preserves_customizations(self):
        from materiais import LEGACY_GUIDE,atualizar_guia_uso
        instalar(self.store)
        record=next(r for r in self.store.records(self.master) if r['name'].startswith('Ateliê'))
        record['content']=LEGACY_GUIDE
        record=self.store.put(self.master,record,record['version'])['record']
        self.assertTrue(atualizar_guia_uso(self.store))
        changed=self.store.get(self.master,record['id'])
        self.assertIn('Jogadores usam apenas Gemma 12B',changed['content'])
        self.assertFalse(atualizar_guia_uso(self.store))
        changed['content']='Personalização do mestre'
        self.store.put(self.master,changed,changed['version'])
        self.assertFalse(atualizar_guia_uso(self.store))

    def test_ready_guides_visible_exportable_and_idempotent(self):
        ids=instalar(self.store)
        self.assertEqual(len(GUIDES),len(ids))
        self.assertEqual(len(GUIDES),len(self.store.records(self.p1)))
        for id in ids:
            record=self.store.get(self.p1,id)
            self.assertEqual('cheat_sheet',record['kind'])
            text,_=self.store.export(self.p1,id,'md')
            self.assertGreater(len(text),400)
        self.assertEqual([],instalar(self.store))
        record=self.store.get(self.master,ids[0]);record['content']='Personalizado pelo mestre'
        self.store.put(self.master,record,1)
        instalar(self.store)
        self.assertEqual('Personalizado pelo mestre',self.store.get(self.master,ids[0])['content'])

    def test_hunger_sheet_has_complete_conditions_and_verified_sources(self):
        ids=instalar(self.store)
        record=next(r for r in self.store.records(self.master) if 'Fome, críticos' in r['name'])
        self.assertIn('VITÓRIA CRÍTICA',record['content'])
        self.assertIn('teste FALHOU',record['content'])
        self.assertIn('p0209-t001',record['sources'])
        self.assertIn('p0209-t002',record['sources'])

    def test_model_schema_blocks_unknown_sheet_fields_and_invented_citations(self):
        schema=record_schema([],['uuid-visible'])
        self.assertFalse(schema['properties']['sheet']['additionalProperties'])
        self.assertEqual(0,schema['properties']['sources']['maxItems'])
        self.assertEqual(['uuid-visible'],schema['properties']['links']['items']['enum'])

    def test_observed_wrong_critical_definition_is_rejected(self):
        with self.assertRaises(Problem):
            conferir_regra_observada('consultor',{'resposta':'Vitória crítica (vitória por uma margem significativa).'})
        conferir_regra_observada('consultor',{'resposta':'Vitória crítica exige vencer o teste com pelo menos um par de 10.'})

    def test_observed_missing_session_paths_is_rejected(self):
        with self.assertRaises(Problem):
            conferir_regra_observada('planejador',{'resposta':'Caminho 1: apenas o começo'},'Planeje três caminhos distintos')
        conferir_regra_observada('planejador',{'resposta':'Caminho 1: A. Caminho 2: B. Caminho 3: C.'},'Planeje três caminhos distintos')

    def test_practical_sheet_with_statistics_only_in_prose_is_rejected(self):
        answer={'resposta':'Ficha','propostas':[{'registro':{'kind':'personagem','sheet':{'conceito':'Programador'},'content':'Força: 2'}}]}
        with self.assertRaises(Problem):conferir_regra_observada('criador',answer,'Crie uma ficha parcial com nove atributos')

    def test_practical_sheet_must_include_both_requested_skills(self):
        sheet={'cla':'Malkavian','atributos':{'Força':2},'habilidades':{'Tecnologia':3}}
        answer={'resposta':'Ficha','propostas':[{'registro':{'kind':'personagem','sheet':sheet}}]}
        question='Crie uma ficha parcial. Preencha apenas Tecnologia 3 e Investigação 2 nas habilidades; diga o que falta.'
        with self.assertRaises(Problem):conferir_regra_observada('criador',answer,question)
        sheet['habilidades']['Investigação']=2
        conferir_regra_observada('criador',answer,question)

    def test_actual_prose_junk_is_removed_without_changing_proposals(self):
        answer={'resposta':'Terceiro caminho e sua consequência.", 1, [], {} 2024-05-22T10:00:00Z','fontes':[],'propostas':[]}
        shown=apresentar_resposta(answer)
        self.assertEqual('Terceiro caminho e sua consequência.',shown['resposta'])
        self.assertEqual([],shown['propostas'])

    def test_sheet_preview_uses_structured_values_instead_of_hallucinated_prose(self):
        from core import fresh
        record=fresh('personagem');record.update(name='Jorge',sheet={'habilidades':{'Tecnologia':3}})
        answer={'resposta':'Cognição 3, Subtileza 2, Tímpano (Humanidade)','fontes':[],
                'propostas':[{'alvo':'','versao':0,'motivo':'Ficha','registro':record}]}
        shown=apresentar_resposta(answer)
        self.assertIn('Tecnologia: 3',shown['resposta'])
        for invented in ['Cognição','Subtileza','Tímpano']:self.assertNotIn(invented,shown['resposta'])
        self.assertEqual(answer['propostas'],shown['propostas'])

    def test_ready_guides_do_not_block_explicit_import_into_empty_campaign(self):
        import json,sqlite3
        from pathlib import Path
        from contextlib import closing
        from administrar import importar
        ids=instalar(self.store)
        source=Path(self.tmp.name)/'origem.sqlite3'
        with closing(sqlite3.connect(source)) as db:
            db.execute('CREATE TABLE estado(id INTEGER,dados TEXT)')
            db.execute('INSERT INTO estado VALUES(1,?)',(json.dumps({'personagens':[{'id':'pj','nome':'Importado'}]}),))
            db.commit()
        result=importar(self.store,source,Path(self.tmp.name)/'snapshots')
        self.assertEqual(1,result['registros_importados'])
        for id in ids:self.assertEqual('cheat_sheet',self.store.get(self.p1,id)['kind'])
        with self.assertRaises(ValueError):importar(self.store,source,Path(self.tmp.name)/'snapshots')
