"""Tests hors réseau du marquage et des filtres de chaînes."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

# Ces tests n'appellent aucun accès réseau. Permet leur exécution sans requests.
try:
    import requests
except ModuleNotFoundError:
    sys.modules['requests'] = types.ModuleType('requests')
spec = importlib.util.spec_from_file_location('sports_main', Path(__file__).with_name('main.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class RivalitesTests(unittest.TestCase):
    def test_all_pairs_both_orders(self):
        for sport in m.SPORTS:
            for a,b,level in m.RIVALITES_IMPORTANCE[sport['prefixe']]:
                for match in (a+' - '+b,b+' - '+a):
                    with self.subTest(match=match):
                        self.assertEqual(m.emoji_rivalite(match,sport),'🔥'*level+' ')

    def test_roundtrip_no_accumulation_same_uid(self):
        for sport in m.SPORTS:
            a,b,_=m.RIVALITES_IMPORTANCE[sport['prefixe']][0]
            event={'match':a+' - '+b,'uid':'stable@test','dtstamp':'20260913T000000Z',
                   'dtstart':'20261001T000000Z','dtend':'20261001T040000Z','chaines':['beIN SPORTS 1']}
            lines=m.construire_evenement(event,sport)
            self.assertEqual(m.extraire_match_calendrier_existant(lines,sport),event['match'])
            event['match']=m.extraire_match_calendrier_existant(lines,sport)
            self.assertEqual(m.construire_evenement(event,sport),lines)
            self.assertEqual(m.valeur_propriete(lines,'UID'),'stable@test')
            self.assertEqual(m.valeur_propriete(lines,'DESCRIPTION'),'beIN SPORTS 1')

    def test_broadcasters_unchanged(self):
        for sport in m.SPORTS:
            self.assertTrue(m.est_diffuseur_autorise('beIN SPORTS 2',sport))
            for channel in ('Netflix',"L’Équipe"):
                self.assertEqual(m.est_diffuseur_autorise(channel,sport),sport['prefixe']=='NFL')
            for channel in ('Disney+','ESPN','FOX'):
                self.assertFalse(m.est_diffuseur_autorise(channel,sport))

    def test_unlisted_and_redzone(self):
        for sport in m.SPORTS:
            self.assertEqual(m.emoji_rivalite('NFL RedZone',sport),'')
            self.assertEqual(m.emoji_rivalite('Texas Rangers - Boston Red Sox',sport),'')

    def test_cardinals_punctuation(self):
        sport=next(x for x in m.SPORTS if x['prefixe']=='MLB')
        self.assertEqual(m.emoji_rivalite('St Louis Cardinals - Chicago Cubs',sport),'🔥🔥🔥 ')

if __name__=='__main__': unittest.main()
