import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import team_context as tc
NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


def calendar(summary='⚽ Premier League : Arsenal - Chelsea', start='20261010T190000Z'):
    return '\r\n'.join(['BEGIN:VCALENDAR','VERSION:2.0','BEGIN:VEVENT','UID:stable@example',
        'DTSTAMP:20260901T000000Z','DTSTART:'+start,'DTEND:20261010T210000Z',
        'SUMMARY:'+summary,'DESCRIPTION:CANAL+','LOCATION:Stade','STATUS:CONFIRMED',
        'END:VEVENT','END:VCALENDAR'])+'\r\n'


def espn(kind, games=4):
    count={'PL':20,'L1':18,'UCL':36,'NFL':32}[kind]
    entries=[]
    for i in range(count):
        entries.append({'team':{'id':str(i),'displayName':f'Team {i}', 'abbreviation':f'T{i}'},
            'stats':[{'name':k,'value':v} for k,v in {'rank':i+1,'gamesPlayed':games,
            'wins':3,'losses':1,'ties':0,'divisionWins':1}.items()]})
    return {'season':{'year':2026},'children':[{'standings':{'name':'overall','entries':entries}}]}


class ContextTests(unittest.TestCase):
    def test_league_ranks(self):
        for kind in ('PL','L1','UCL'):
            self.assertEqual(tc.espn_labels(espn(kind),kind,2026)['team 1'],'#2')

    def test_no_preseason_ranks(self):
        self.assertEqual(tc.espn_labels(espn('UCL',0),'UCL',2026),{})

    def test_wrong_season(self):
        with self.assertRaises(ValueError):tc.espn_labels(espn('PL'),'PL',2025)

    def test_incomplete_table(self):
        d=espn('PL');d['children'][0]['standings']['entries'].pop()
        with self.assertRaises(ValueError):tc.espn_labels(d,'PL',2026)

    def test_nfl_overall_and_ties(self):
        d=espn('NFL')
        d['children'][0]['standings']['entries'][0]['stats'].append({'name':'ties','value':1})
        m=tc.espn_labels(d,'NFL',2026)
        self.assertEqual(m['team 0'],'3W/1L/1T')
        self.assertEqual(m['team 1'],'3W/1L')

    def test_mlb_percentage(self):
        d={'records':[{'standingsType':'regularSeason','teamRecords':[
            {'team':{'id':1},'season':'2026','leagueRecord':{'wins':62,'losses':38}}]}]}
        teams={'teams':[{'id':1,'name':'New York Yankees','teamName':'Yankees'}]}
        self.assertEqual(tc.mlb_labels(d,teams,2026)['new york yankees'],'62%')
        d['records'][0]['teamRecords'][0]['leagueRecord']={'wins':0,'losses':0}
        self.assertEqual(tc.mlb_labels(d,teams,2026),{})

    def test_aliases(self):
        self.assertEqual(tc.norm('PSG'),tc.norm('Paris Saint-Germain'))
        self.assertEqual(tc.norm('FC Barcelone'),tc.norm('Barcelona'))
        self.assertEqual(tc.norm('Le Havre'),tc.norm('Le Havre AC'))
        self.assertNotEqual(tc.norm('Paris FC'),tc.norm('PSG'))

    def test_ambiguous_alias_rejected(self):
        self.assertEqual(tc.indexed([(1,['United'],'#1'),(2,['United'],'#2')]),{})

    def test_decorate_rivalry(self):
        s='🔥🔥🔥 ⚽ Premier League : Arsenal - Tottenham Hotspur — North London Derby'
        decorated=tc.decorate(s,{'arsenal':'#2','tottenham hotspur':'#5'})
        self.assertIn('Arsenal [#2] - Tottenham Hotspur [#5]',decorated)
        self.assertEqual(tc.strip_labels(decorated),s)
        self.assertEqual(tc.decorate(decorated,{'arsenal':'#2','tottenham hotspur':'#5'}),decorated)

    def test_sequence_stability(self):
        provider=lambda *args:{'arsenal':'#2','chelsea':'#5'}
        first=tc.enrich_calendar(calendar(),calendar(),'PL',NOW,provider)
        self.assertEqual(tc.prop(tc.blocks(first)[0],'SEQUENCE'),'1')
        second=tc.enrich_calendar(calendar(),first,'PL',NOW,provider)
        self.assertEqual(first,second)
        changed=tc.enrich_calendar(calendar(),second,'PL',NOW,lambda *args:{'arsenal':'#1'})
        self.assertEqual(tc.prop(tc.blocks(changed)[0],'SEQUENCE'),'2')
        for key in ('UID','DTSTART','DTEND','DESCRIPTION','LOCATION','STATUS'):
            self.assertEqual(tc.prop(tc.blocks(changed)[0],key),tc.prop(tc.blocks(first)[0],key))

    def test_history(self):
        original=calendar('⚽ Premier League : Arsenal [#2] - Chelsea [#5]','20260901T190000Z')
        new=calendar(start='20260901T190000Z')
        def forbidden(*args):raise AssertionError('No current ranks on history')
        self.assertEqual(tc.blocks(tc.enrich_calendar(new,original,'PL',NOW,forbidden)),tc.blocks(original))

    def test_failure_preserves_labels(self):
        old=calendar('⚽ Premier League : Arsenal [#2] - Chelsea [#5]')
        result=tc.enrich_calendar(calendar(),old,'PL',NOW,lambda *a:None)
        self.assertEqual(tc.prop(tc.blocks(result)[0],'SUMMARY'),tc.prop(tc.blocks(old)[0],'SUMMARY'))

    def test_psg_competition(self):
        calls=[]
        def provider(kind,season):
            calls.append(kind)
            return {'paris saint germain':'#1' if kind=='UCL' else '#3'}
        for title,expected in [('Ligue 1','#3'),('Ligue des Champions','#1')]:
            result=tc.enrich_calendar(calendar(f'⚽ {title} : PSG - Lyon'),'','PSG',NOW,provider)
            self.assertIn('PSG ['+expected+']',result)
        self.assertEqual(calls,['L1','UCL'])
        result=tc.enrich_calendar(calendar('⚽ Coupe de France : PSG - Lyon'),'','PSG',NOW,provider)
        self.assertNotIn('PSG [',result)
        self.assertEqual(len(calls),2)

    def test_utf8_fold(self):
        result=tc.enrich_calendar(calendar('🔥'*70+' ⚽ Premier League : Arsenal - Chelsea'),'','PL',NOW,lambda *a:{})
        self.assertTrue(all(len(l.encode())<=75 for l in result.splitlines()))
        self.assertIn('🔥'*70,'\n'.join(tc.unfold(result)))

    def test_source_failure(self):
        tc.standings.cache_clear()
        with patch.object(tc,'fetch',side_effect=OSError('offline')):
            self.assertIsNone(tc.standings('PL',2026))
        tc.standings.cache_clear()

    def test_reader_roundtrip(self):
        # requests n’est pas utilisé par ces tests de lecture ; aucun réseau.
        if 'requests' not in sys.modules and importlib.util.find_spec('requests') is None:
            sys.modules.setdefault('requests',types.ModuleType('requests'))
        import main
        import football
        event=tc.blocks(calendar('🔥🔥 🏈 NFL : Buffalo Bills [3W/1L] - Miami Dolphins [2W/2L]'))[0]
        nfl=next(s for s in main.SPORTS if s['prefixe']=='NFL')
        self.assertEqual(main.extraire_match_calendrier_existant(event,nfl),'Buffalo Bills - Miami Dolphins')
        psg=next(e for e in football.EQUIPES if e['nom']=='PSG')
        event=tc.blocks(calendar('⚽ Ligue 1 : PSG [#1] - Lyon [#4]'))[0]
        self.assertEqual(football.parser_evenement_existant(event,psg)['match'],'PSG - Lyon')

if __name__=='__main__':unittest.main()
