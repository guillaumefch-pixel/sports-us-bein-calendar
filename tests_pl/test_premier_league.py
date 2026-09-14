import copy
import json
from pathlib import Path
import unittest
import premier_league as p

FIX=Path(__file__).parent/'fixtures'
NOW=p.instant('2026-09-01T10:00:00Z')

class Tests(unittest.TestCase):
    def setUp(self):
        self.games=p.parse_schedule((FIX/'espn.json').read_text())
        self.g=copy.deepcopy(next(g for g in self.games.values() if {g.home,g.away}=={'Manchester City','Manchester United'}))
        self.g.status='STATUS_SCHEDULED';self.g.state='pre'
    def test_only_big_six(self):
        events=p.reconcile([],self.games,{},NOW)
        self.assertTrue(events)
        self.assertTrue(all({p.prop(e,'X-PL-HOME'),p.prop(e,'X-PL-AWAY')}&p.BIG_SIX for e in events))
    def test_canal_detail(self):
        found=p.tv_channels((FIX/'tv.ics').read_text(),self.games)
        self.assertEqual(found[self.g.id],{'CANAL+'})
    def test_not_foreign_channel(self):
        text=(FIX/'tv.ics').read_text().replace('Canal+','Sky Sports')
        self.assertEqual(p.tv_channels(text,self.games),{})
    def test_bigsix_match_once(self):
        events=p.reconcile([],{self.g.id:self.g},{},NOW)
        self.assertEqual(len(events),1)
        self.assertIn('🔥🔥🔥',p.prop(events[0],'SUMMARY'))
        self.assertIn('Derby de Manchester',p.prop(events[0],'SUMMARY'))
    def test_postponed(self):
        old=p.make_event(self.g,set(),NOW)
        self.g.status='STATUS_POSTPONED'
        self.assertEqual(p.reconcile([old],{self.g.id:self.g},{},NOW),[])
    def test_history(self):
        old=p.make_event(self.g,set(),NOW)
        later=self.g.start+p.timedelta(days=1)
        self.assertEqual(p.reconcile([old],{self.g.id:self.g},{},later),[old])
    def test_update_same_uid(self):
        old=p.make_event(self.g,set(),NOW)
        self.g.start+=p.timedelta(days=1)
        new=p.make_event(self.g,{'CANAL+ FOOT'},NOW,old)
        self.assertEqual(p.prop(old,'UID'),p.prop(new,'UID'))
        self.assertEqual(p.prop(new,'SEQUENCE'),'1')
        self.assertEqual(p.prop(new,'DESCRIPTION'),'CANAL+ FOOT')
    def test_idempotent(self):
        old=p.make_event(self.g,set(),NOW)
        self.assertEqual(p.make_event(self.g,set(),NOW+p.timedelta(hours=6),old),old)
    def test_unknown_hour_then_announced(self):
        self.g.known=False
        old=p.make_event(self.g,set(),NOW)
        self.assertTrue(any(x.startswith('DTSTART;VALUE=DATE:') for x in old))
        self.g.known=True
        new=p.make_event(self.g,set(),NOW,old)
        self.assertEqual(p.prop(new,'UID'),p.prop(old,'UID'))
        self.assertTrue(any(x.startswith('DTSTART:') and x.endswith('Z') for x in new))
    def test_invalid_league(self):
        data=json.loads((FIX/'espn.json').read_text());data['leagues']=[]
        with self.assertRaises(ValueError):p.parse_schedule(json.dumps(data))
    def test_fold_and_read(self):
        self.g.venue='É'*100
        data=p.serialize([p.make_event(self.g,set(),NOW)])
        self.assertTrue(all(len(x)<=75 for x in data.split(b'\r\n')))
        self.assertEqual(len(p.read_ics(data.decode())),1)
    def test_duplicate_history_rejected(self):
        old=p.make_event(self.g,set(),NOW)
        with self.assertRaises(ValueError):p.reconcile([old,old],{},{},NOW)
    def test_alias(self):
        self.assertEqual(p.canonical('Tottenham'),'Tottenham Hotspur')
        self.assertEqual(p.canonical('Man Utd'),'Manchester United')
    def test_no_cups_or_other_teams_added(self):
        self.g.home='Everton';self.g.away='Leeds United'
        self.assertEqual(p.reconcile([],{self.g.id:self.g},{},NOW),[])
    def test_rights_end(self):
        self.g.season=2028
        self.assertEqual(p.reconcile([],{self.g.id:self.g},{},NOW),[])

if __name__=='__main__':unittest.main()
