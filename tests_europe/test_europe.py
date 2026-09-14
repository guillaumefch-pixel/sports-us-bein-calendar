import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import europe_football as e
import calendar_locations as v

FIX=Path(__file__).parent/'fixtures'
NOW=e.cal.instant('2026-09-13T10:00:00Z')

class EuropeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games={}
        for league in e.LEAGUES:
            cls.games.update(e.parse_schedule(json.loads((FIX/(league+'.json')).read_text()),league,2026))

    def test_complete_club_selection(self):
        liga=[g for g in self.games.values() if g.league=='esp.1' and e.selected(g)]
        self.assertEqual(len(liga),108)
        for team in ('83','86','1068'):
            self.assertEqual(sum(team in (g.home_id,g.away_id) for g in liga),38)
        self.assertEqual(sum(g.league=='ger.1' and e.selected(g) for g in self.games.values()),34)

    def test_fires(self):
        for pair in [('83','86'),('83','1068'),('86','1068'),('132','124'),('132','131'),('132','11420')]:
            g=next(g for g in self.games.values() if {g.home_id,g.away_id}==set(pair))
            self.assertIn('🔥',e.cal.prop(e.individual(g,{},NOW),'SUMMARY'))

    def test_no_psg_in_slots(self):
        result=e.reconcile([],self.games,{},NOW,set(e.LEAGUES))
        grouped=[x for x in result if e.cal.prop(x,'X-EU-GROUPED')=='TRUE']
        self.assertTrue(grouped)
        for event in grouped:
            self.assertEqual(e.cal.prop(event,'SUMMARY'),'Ligue des champions')
            ids=e.cal.prop(event,'X-EU-MATCHES').split(',')
            self.assertEqual(len({self.games[i].start for i in ids}),1)
            for i in ids:self.assertNotIn(e.PSG,(self.games[i].home_id,self.games[i].away_id))
            self.assertFalse(e.cal.prop(event,'LOCATION'))

    def test_knockout_individual_and_psg_excluded(self):
        g=copy.deepcopy(next(g for g in self.games.values() if g.league=='uefa.champions' and e.selected(g)))
        g.start=NOW+e.timedelta(days=10);g.stage='knockout-round-playoffs';g.state='pre';g.status='STATUS_SCHEDULED'
        result=e.reconcile([],{g.id:g},{},NOW,{'uefa.champions'})
        self.assertEqual(len(result),1);self.assertIn('Barrages',e.cal.prop(result[0],'SUMMARY'))
        self.assertFalse(e.cal.prop(result[0],'X-EU-GROUPED'))
        g.home_id=e.PSG
        self.assertEqual(e.reconcile([],{g.id:g},{},NOW,{'uefa.champions'}),[])

    def test_group_ranks_notes(self):
        g=next(g for g in self.games.values() if g.league=='uefa.champions' and e.selected(g))
        ranks={e.context.norm(g.raw_home):'#5',e.context.norm(g.raw_away):'#32'}
        desc=v.decode(e.cal.prop(e.grouped([g],ranks,NOW),'DESCRIPTION'))
        self.assertIn('[#5] - ',desc);self.assertIn('[#32], ',desc);self.assertIn(g.stadium,desc)

    def test_foreign_tv_not_accepted(self):
        g=next(g for g in self.games.values() if g.league=='ger.1' and e.selected(g))
        self.assertEqual(e.cal.prop(e.individual(g,{},NOW),'DESCRIPTION'),'beIN SPORTS (chaîne à confirmer)')
        g=next(g for g in self.games.values() if g.league=='esp.1' and e.selected(g))
        self.assertEqual(e.cal.prop(e.individual(g,{},NOW),'DESCRIPTION'),'Disney+')

    def test_stable_run(self):
        first=e.reconcile([],self.games,{},NOW,set(e.LEAGUES))
        second=e.reconcile(first,self.games,{},NOW,set(e.LEAGUES))
        self.assertEqual(first,second)
        self.assertEqual(len(first),len({e.cal.prop(x,'UID') for x in first}))

    def test_source_failure_preserves(self):
        first=e.reconcile([],self.games,{},NOW,set(e.LEAGUES))
        self.assertEqual(first,e.reconcile(first,{}, {},NOW,set()))

    def test_unknown_time_and_cancellation(self):
        g=copy.deepcopy(next(g for g in self.games.values() if g.league=='ger.1' and e.selected(g)))
        g.start=NOW+e.timedelta(days=4);g.known=False;g.state='pre';g.status='STATUS_SCHEDULED'
        result=e.reconcile([],{g.id:g},{},NOW,{'ger.1'})
        self.assertTrue(any(x.startswith('DTSTART;VALUE=DATE:') for x in result[0]))
        g.status='STATUS_CANCELED'
        self.assertEqual(e.reconcile(result,{g.id:g},{},NOW,{'ger.1'}),[])

    def test_history(self):
        first=e.reconcile([],self.games,{},NOW,set(e.LEAGUES))
        first=[first[0]]
        later=e.cal.ics_time(first[0])+e.timedelta(hours=4)
        self.assertEqual(first,e.reconcile(first,{}, {},later,set(e.LEAGUES)))

    def test_run_keeps_ranks_on_outage(self):
        class Frozen(e.datetime):
            @classmethod
            def now(cls,tz=None):return NOW
        def fetch(url):
            league=next(k for k in e.LEAGUES if '/'+k+'/' in url)
            return (FIX/(league+'.json')).read_text()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'europe.ics'
            with patch.object(e,'datetime',Frozen),patch.object(e.cal,'fetch',side_effect=fetch):
                with patch.object(e.context,'standings',return_value={'barcelona':'#1'}):e.run(p)
                first=p.read_bytes()
                with patch.object(e.context,'standings',return_value=None):e.run(p)
                self.assertEqual(first,p.read_bytes())

    def test_ics_roundtrip(self):
        events=e.reconcile([],self.games,{},NOW,set(e.LEAGUES));data=e.serialize(events)
        self.assertEqual(e.cal.read_ics(data.decode()),events)
        self.assertTrue(all(len(x)<=75 for x in data.split(b'\r\n')))

class LocationTests(unittest.TestCase):
    def test_city_and_team(self):
        self.assertEqual(v.location('Emirates Stadium','London','Arsenal'),'Emirates Stadium, Londres — Arsenal')
        self.assertEqual(v.location('Etihad Stadium','Manchester','Manchester City'),'Etihad Stadium, Manchester')
        self.assertEqual(v.location('Allianz Arena','München','Bayern Munich'),'Allianz Arena, Munich')
        self.assertEqual(v.location('SoFi Stadium','Inglewood','Los Angeles Rams'),'SoFi Stadium, Inglewood — Los Angeles Rams')

    def test_metadata_and_repeat(self):
        text='\r\n'.join(['BEGIN:VCALENDAR','VERSION:2.0','BEGIN:VEVENT','UID:x','DTSTART:20261001T120000Z',
            'DTEND:20261001T140000Z','SUMMARY:⚽ PL : Arsenal [#1] - Chelsea [#2]','DESCRIPTION:CANAL+',
            'LOCATION:Emirates Stadium','SEQUENCE:2','END:VEVENT','END:VCALENDAR'])+'\r\n'
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.ics';p.write_text(text)
            out=v.normalize_calendar(text,p,'PL',{'emirates stadium':'London'},NOW)
            self.assertIn('SEQUENCE:3',out);self.assertIn('Londres — Arsenal',v.decode(out))
            p.write_text(out)
            self.assertEqual(out,v.normalize_calendar(text,p,'PL',{'emirates stadium':'London'},NOW))
            self.assertIn('DESCRIPTION:CANAL+',out);self.assertIn('UID:x',out)

    def test_neutral_and_multivenue(self):
        self.assertEqual(v.location('Cotton Bowl','Dallas','Texas Longhorns'),'Cotton Bowl, Dallas — Texas Longhorns')
        self.assertEqual(v.location('','',''), '')

if __name__=='__main__':unittest.main()
