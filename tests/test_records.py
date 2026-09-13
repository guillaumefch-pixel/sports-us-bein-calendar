import json
import unittest
from pathlib import Path
from unittest.mock import patch
import college_football as c

NOW=c.instant('2026-09-12T10:00:00Z')
FIX=Path(__file__).parent/'fixtures'

class RecordTests(unittest.TestCase):
    def setUp(self):
        self.poll=c.espn_poll((FIX/'espn_poll.json').read_text())
        self.game=next(iter(c.schedule((FIX/'espn_schedule.json').read_text()).values()))
        self.game.start=NOW+c.timedelta(days=10)
        self.records={c.norm(self.game.home):'3W/0L',c.norm(self.game.away):'2W/1L'}

    def event(self,**kwargs):
        return c.make_event(self.game,self.poll,set(),NOW,**kwargs)

    def test_both_teams(self):
        s=c.prop(self.event(records=self.records),'SUMMARY')
        self.assertIn('[3W/0L]',s);self.assertIn('[2W/1L]',s)

    def test_change_keeps_uid_and_increments_sequence(self):
        old=self.event(records=self.records)
        new=self.event(previous=old,records={c.norm(self.game.home):'4W/0L'})
        self.assertEqual(c.prop(old,'UID'),c.prop(new,'UID'))
        self.assertEqual(int(c.prop(new,'SEQUENCE')),int(c.prop(old,'SEQUENCE'))+1)
        self.assertIn('[2W/1L]',c.prop(new,'SUMMARY'))

    def test_stable_and_failure(self):
        old=self.event(records=self.records)
        self.assertEqual(old,self.event(previous=old,records=self.records))
        self.assertEqual(old,self.event(previous=old,records={}))
        self.assertNotIn('[0W/0L]',c.prop(self.event(),'SUMMARY'))

    def test_history(self):
        self.game.start=NOW-c.timedelta(days=1)
        old=self.event(records=self.records)
        result=c.reconcile([old],{self.game.id:self.game},{},self.poll,NOW,{c.norm(self.game.home):'99W/0L'})
        self.assertEqual(result,[old])

    def test_global_not_conference(self):
        data={'children':[{'standings':{'name':'overall','season':2026,'entries':[
            {'team':{'location':'Ohio State'},'stats':[{'name':k,'value':v} for k,v in
            {'wins':5,'losses':1,'ties':0,'leagueWins':2,'leagueLosses':1}.items()]}]}}]}
        self.assertEqual(c.season_records(json.dumps(data),2026),{'ohio state':'5W/1L'})
        with self.assertRaises(ValueError):c.season_records(json.dumps(data),2025)
        with self.assertRaises(ValueError):c.season_records('{}',2026)

    def test_overall_precedes_home_away_and_conference(self):
        data={'standings':{'name':'overall','season':2026,'entries':[
            {'team':{'location':'Ohio State'},'stats':[
                {'name':'wins','value':5}, {'name':'overall','displayValue':'5-1'},
                {'name':'wins','value':3}, {'name':'Home','displayValue':'3-0'},
                {'name':'wins','value':1}, {'name':'vs. Conf.','displayValue':'1-0'}]}]}}
        self.assertEqual(c.season_records(json.dumps(data),2026),{'ohio state':'5W/1L'})

    def test_missing_sources(self):
        with patch.object(c,'fetch',side_effect=ValueError('offline')):
            self.assertEqual(c.load_records(2026),{})

if __name__=='__main__':unittest.main()
