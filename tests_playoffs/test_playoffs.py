import copy
import json
import tempfile
import unittest
from pathlib import Path
from datetime import timedelta
import playoff_context as p
import calendar_locations as loc

FIX=Path(__file__).parent/'fixtures'
def data(name):return json.loads((FIX/(name+'.json')).read_text())

class PlayoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows={k:p.games(data(f),k,2025) for k,f in [('NFL','nfl'),('MLB','mlb'),('NCAA','cfp')]}
        cls.seeds={'NFL':p.nfl_seeds(data('nfl-standings'),2025),
                   'MLB':p.mlb_seeds(data('mlb-standings'),data('mlb-teams'),2025),
                   'NCAA':p.cfp_seeds(cls.rows['NCAA'])}

    def event(self,kind,game=None):
        g=game or self.rows[kind][0]
        home,away=[g['teams'][x]['team']['displayName'] for x in ('home','away')]
        uid=f"ncaa-espn-{g['id']}@sports-calendar" if kind=='NCAA' else 'stable@test'
        title=f'🏈 CFP Premier tour - {home} #8 [10W/2L] - {away} #9 [9W/3L]' if kind=='NCAA' else f'🔥 {kind} : {home} [62%] - {away} [50%]'
        lines=['BEGIN:VCALENDAR','VERSION:2.0','BEGIN:VEVENT','UID:'+uid,
               'DTSTART:'+g['start'].strftime('%Y%m%dT%H%M%SZ'),'DTEND:'+(g['start']+timedelta(hours=4)).strftime('%Y%m%dT%H%M%SZ'),
               'SUMMARY:'+title,'DESCRIPTION:beIN SPORTS 1','LOCATION:Stade','SEQUENCE:0']
        if kind=='NCAA':lines.append('X-CFB-STAGE:CFP — College Football Playoff First Round')
        return '\r\n'.join(lines+['END:VEVENT','END:VCALENDAR'])+'\r\n'

    def enrich(self,kind,text=None,path='missing-calendar-test.ics',provider=None):
        g=self.rows[kind][0]
        return p.enrich(text or self.event(kind),path,kind,provider or (lambda k,s:(self.rows[k],self.seeds[k])),g['start']-timedelta(days=1))

    def test_real_brackets(self):
        self.assertEqual(len(self.seeds['NFL']),14)
        self.assertEqual(self.seeds['NFL']['denver broncos'],'AFC #1')
        self.assertEqual(self.seeds['MLB']['new york yankees'],'AL #4')
        self.assertEqual(self.seeds['MLB']['cleveland guardians'],'AL #3')
        self.assertEqual(self.seeds['NCAA']['james madison'],'CFP #12')
        self.assertEqual(len(self.rows['NCAA']),11)
        self.assertEqual(len(self.rows['NFL']),13) # Pro Bowl exclu.

    def test_duplicate_schedule_not_counted_twice(self):
        d=data('mlb');d['events']+=copy.deepcopy(d['events'])
        self.assertEqual(len(p.games(d,'MLB',2025)),len(self.rows['MLB']))

    def test_nfl_wild_card_and_both_seeds(self):
        result=self.enrich('NFL')
        s=p.decode(p.core.prop(p.core.blocks(result)[0],'SUMMARY'))
        self.assertIn('NFL Wild Card :',s);self.assertIn('[NFC #4]',s);self.assertIn('[NFC #5]',s)
        self.assertNotIn('%',s);self.assertIn('🔥',s)

    def test_mlb_wc_and_series(self):
        result=self.enrich('MLB');event=p.core.blocks(result)[0]
        self.assertIn('Wild Card Series',p.core.prop(event,'SUMMARY'))
        self.assertIn('[AL #3]',p.core.prop(event,'SUMMARY'))
        self.assertIn('Série :',p.decode(p.core.prop(event,'DESCRIPTION')))
        self.assertTrue(p.decode(p.core.prop(event,'DESCRIPTION')).startswith('beIN SPORTS 1\n'))

    def test_cfp_replaces_ap_and_record(self):
        s=p.core.prop(p.core.blocks(self.enrich('NCAA'))[0],'SUMMARY')
        self.assertIn('[CFP #8]',s);self.assertIn('[CFP #9]',s)
        self.assertNotIn('W/',s);self.assertNotIn(' #8 -',s)

    def test_not_cfp_unchanged(self):
        text=self.event('NCAA').replace('X-CFB-STAGE:CFP — College Football Playoff First Round','X-CFB-STAGE:Finale SEC')
        self.assertEqual(p.core.unfold(text),p.core.unfold(self.enrich('NCAA',text)))

    def test_unknown_cfp_seed_omits_other_rank(self):
        result=self.enrich('NCAA',provider=lambda k,s:(self.rows[k],{}))
        s=p.core.prop(p.core.blocks(result)[0],'SUMMARY')
        self.assertNotIn('#',s);self.assertNotIn('W/',s)

    def test_cfp_incomplete_and_conflicting(self):
        with self.assertRaises(ValueError):p.cfp_seeds(self.rows['NCAA'][:1])
        rows=copy.deepcopy(self.rows['NCAA']);rows.append(copy.deepcopy(rows[0]))
        rows[-1]['teams']['home']['curatedRank']['current']=1
        with self.assertRaises(ValueError):p.cfp_seeds(rows)

    def test_not_provisional_nfl(self):
        d=data('nfl-standings')
        entry=d['children'][0]['standings']['entries'][0]
        next(s for s in entry['stats'] if s['name']=='overall')['displayValue']='10-2'
        with self.assertRaises(ValueError):p.nfl_seeds(d,2025)
        with self.assertRaises(ValueError):p.nfl_seeds(data('nfl-standings'),2026)

    def test_not_provisional_mlb(self):
        d=data('mlb-standings');d['records'][0]['teamRecords'][0]['gamesPlayed']=150
        with self.assertRaises(ValueError):p.mlb_seeds(d,data('mlb-teams'),2025)

    def test_frozen_seeds_and_outage(self):
        first=self.enrich('NFL')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'a.ics';path.write_text(first)
            changed=dict(self.seeds['NFL']);changed['carolina panthers']='NFC #1'
            second=self.enrich('NFL',path=path,provider=lambda k,s:(self.rows[k],changed))
            self.assertIn('[NFC #4]',second);self.assertNotIn('[NFC #1]',second)
            failure=self.enrich('NFL',path=path,provider=lambda *a:([],{}))
            self.assertEqual(p.core.prop(p.core.blocks(first)[0],'SUMMARY'),p.core.prop(p.core.blocks(failure)[0],'SUMMARY'))

    def test_regular_season_no_change(self):
        self.assertEqual(self.event('NFL'),self.enrich('NFL',provider=lambda *a:([],{})))

    def test_mlb_official_postseason_no_regular_percentage_on_outage(self):
        text=self.event('MLB').replace('END:VEVENT','X-MLB-POSTSEASON:TRUE\r\nEND:VEVENT')
        result=self.enrich('MLB',text,provider=lambda *a:([],{}))
        self.assertNotIn('%',p.core.prop(p.core.blocks(result)[0],'SUMMARY'))

    def test_location_writer_sets_sequence_and_preserves_uid(self):
        text=self.event('NFL')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'a.ics';path.write_text(text)
            annotated=self.enrich('NFL',path=path)
            final=loc.normalize_calendar(annotated,path,'NFL',{'stade':'Ville'})
            self.assertEqual(p.core.prop(p.core.blocks(final)[0],'SEQUENCE'),'1')
            self.assertEqual(p.core.prop(p.core.blocks(final)[0],'UID'),'stable@test')
            path.write_text(final)
            again=loc.normalize_calendar(self.enrich('NFL',path=path),path,'NFL',{'stade':'Ville'})
            self.assertEqual(final,again)

    def test_main_reader_keeps_broadcaster(self):
        import sys,types
        try:import requests
        except ImportError:sys.modules['requests']=types.ModuleType('requests')
        import main
        event=p.core.blocks(self.enrich('MLB'))[0]
        sport=next(s for s in main.SPORTS if s['prefixe']=='MLB')
        self.assertEqual(main.extraire_chaines_calendrier_existant(event,sport),['beIN SPORTS 1'])
        match=main.extraire_match_calendrier_existant(event,sport)
        self.assertNotIn('#',match);self.assertNotIn('[',match)

if __name__=='__main__':unittest.main()
