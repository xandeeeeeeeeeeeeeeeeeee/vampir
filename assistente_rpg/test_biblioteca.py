import unittest
from biblioteca import contexto, buscar, recuperar
from core import consultar


class BibliotecaTests(unittest.TestCase):
    def test_hunger_rule_includes_conditions_examples_and_exceptions(self):
        context=contexto('p0209-t002')
        ids={r['id'] for r in context['trechos']}
        self.assertTrue({'p0207-t003','p0208-t001','p0208-t002','p0209-t001','p0209-t002'}<=ids)
        self.assertEqual([207,208,209],context['paginas_pdf'])
        for source in context['trechos']:
            self.assertEqual(consultar.obter(source['id'])[0]['texto'],source['texto'])

    def test_introductory_hunger_includes_dice_section(self):
        self.assertIn('p0209-t002',[r['id'] for r in contexto('p0207-t002')['trechos']])
        self.assertIn('p0207-t002',[r['id'] for r in contexto('p0207-t003')['trechos']])

    def test_power_keeps_continuation_and_discipline_characteristics(self):
        context=contexto('p0247-t007','topico')
        ids={r['id'] for r in context['trechos']}
        self.assertTrue({'p0247-t007','p0248-t001','p0247-t002'}<=ids)
        self.assertNotIn('p0251-t007',ids)

    def test_section_keeps_continuation_that_lost_index_heading(self):
        self.assertIn('p0250-t001',[r['id'] for r in contexto('p0249-t007')['trechos']])

    def test_chapter_and_cited_references_are_available(self):
        context=contexto('p0209-t002')
        chapter=contexto('p0209-t002','capitulo')
        self.assertGreater(len(chapter['trechos']),len(context['trechos']))
        self.assertTrue(context['relacionados'])
        self.assertTrue(all(r['contexto'][0]==chapter['caminho'][0] for r in chapter['trechos']))

    def test_search_returns_context_and_deduplicates_same_section(self):
        hits=buscar('Dados de Fome')
        sections=[tuple(r['id'] for r in h['contexto_completo']['trechos']) for h in hits]
        self.assertEqual(len(sections),len(set(sections)))
        self.assertTrue(any('p0208-t002' in s and 'p0209-t002' in s for s in sections))

    def test_ai_budget_never_truncates_primary_section(self):
        sources=recuperar(['p0209-t002','p0122-t004'],limite=1)
        self.assertEqual([r['id'] for r in contexto('p0209-t002','topico')['trechos']],[r['id'] for r in sources])
        for source in sources:
            self.assertEqual(consultar.obter(source['id'])[0]['texto'],source['texto'])

    def test_invalid_source_and_scope_are_rejected(self):
        for identifier,scope in [('inexistente','secao'),('p0209-t002','tudo')]:
            with self.assertRaises(ValueError):contexto(identifier,scope)
