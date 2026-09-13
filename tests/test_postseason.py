import copy
import json
import unittest
from pathlib import Path
import college_football as c
import test_college_football as base

class PostseasonTests(unittest.TestCase):
    def setUp(self):
        helper=base.CollegeTests(); helper.setUp()
        self.g=copy.deepcopy(helper.game)
        self.g.season=2026
        self.g.season_type=3
        self.g.neutral=True
        self.g.networks=('ESPN',)
        self.g.stage='CFP — College Football Playoff Quarterfinal'
        self.poll=c.Poll(base.NOW, {}, 'test')

    def test_cfp_without_top10_and_neutral(self):
        games={self.g.id:self.g}
        events=c.reconcile([], games, c.rights_broadcasts(games), self.poll, base.NOW)
        self.assertEqual(len(events),1)
        self.assertIn('CFP', c.prop(events[0],'SUMMARY'))
        self.assertEqual(c.prop(events[0],'STATUS'),'TENTATIVE')

    def test_conference_final_outside_top10(self):
        self.g.stage='Finale ACC'; self.g.season_type=2
        games={self.g.id:self.g}
        self.assertEqual(len(c.reconcile([],games,c.rights_broadcasts(games),self.poll,base.NOW)),1)

    def test_tnt_requires_explicit_french_listing(self):
        self.g.networks=('TNT',)
        games={self.g.id:self.g}
        self.assertFalse(c.rights_broadcasts(games))
        events=c.reconcile([],games,{self.g.id:{c.TV}},self.poll,base.NOW)
        self.assertEqual(c.prop(events[0],'STATUS'),'CONFIRMED')

    def test_unrelated_bowl_not_playoff(self):
        self.g.stage=''
        self.assertFalse(c.rights_broadcasts({self.g.id:self.g}))
        self.assertEqual(c.competition_stage({'notes':[{'headline':'Rose Bowl'}]}),'')
        self.assertEqual(c.competition_stage({'notes':[{'headline':'FCS Championship - Second Round'}]}),'')

    def test_classification_captured_2025(self):
        games=c.schedule((Path(__file__).parent/'fixtures/postseason.json').read_text())
        self.assertEqual(sum(g.stage.startswith('CFP') for g in games.values()),11)
        self.assertEqual(sum(g.stage.startswith('Finale ') for g in games.values()),9)

    def test_final_ap_poll_in_january(self):
        poll=c.Poll(c.instant('2026-12-07T18:00:00Z'),{str(i):i for i in range(1,11)},'test')
        self.assertIs(c.validate_poll(poll,c.instant('2027-01-24T12:00:00Z')),poll)
        poll.published=c.instant('2026-11-29T18:00:00Z')
        with self.assertRaises(ValueError): c.validate_poll(poll,c.instant('2027-01-24T12:00:00Z'))

    def test_history_preserved_after_rank_exit(self):
        self.g.start=base.NOW
        old=c.make_event(self.g,self.poll,{c.TV},base.NOW)
        self.assertEqual(c.reconcile([old],{}, {},self.poll,base.NOW),[old])

    def test_tbd_excluded(self):
        data=json.loads(base.fixture('espn_schedule.json'))
        for event in data['events']:
            for team in event['competitions'][0]['competitors']:
                team['team']['location']='TBD'
        self.assertFalse(c.schedule(json.dumps(data)))
