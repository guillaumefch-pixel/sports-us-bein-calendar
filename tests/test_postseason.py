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
        self.assertEqual(c.prop(events[0],'STATUS'),'CONFIRMED')

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

    def test_live_game_added_on_first_run(self):
        self.g.start=base.NOW - c.timedelta(hours=1)
        self.g.status='STATUS_IN_PROGRESS'
        games={self.g.id:self.g}
        self.assertEqual(len(c.reconcile([],games,{self.g.id:{c.TV}},self.poll,base.NOW)),1)

    def test_finished_game_not_invented_in_history(self):
        self.g.start=base.NOW - c.timedelta(hours=6)
        self.g.status='STATUS_FINAL'
        games={self.g.id:self.g}
        self.assertEqual(c.reconcile([],games,{self.g.id:{c.TV}},self.poll,base.NOW),[])

    def test_all_power4_finals_without_ap_or_tv(self):
        for conference in ('SEC', 'Big Ten', 'Big 12', 'ACC'):
            self.g.stage=c.competition_stage({'notes':[{'headline':conference+' Championship'}]})
            games={self.g.id:self.g}
            events=c.reconcile([],games,{},self.poll,base.NOW)
            self.assertEqual(len(events),1)
            self.assertTrue(c.prop(events[0],'SUMMARY').startswith('🏈 '+conference+' Final - '))

    def test_all_cfp_games_without_ap_or_tv(self):
        games=c.schedule((Path(__file__).parent/'fixtures/postseason.json').read_text())
        games={k:g for k,g in games.items() if g.stage.startswith('CFP')}
        events=c.reconcile([],games,{},self.poll,c.instant('2025-12-01T00:00:00Z'))
        self.assertEqual(len(events),11)
        titles=[c.prop(e,'SUMMARY') for e in events]
        self.assertEqual(sum('Premier tour' in t for t in titles),4)
        self.assertEqual(sum('Quart de finale' in t for t in titles),4)
        self.assertEqual(sum('Demi-finale' in t for t in titles),2)
        self.assertEqual(sum('Finale nationale' in t for t in titles),1)
        for bowl in ('Rose','Sugar','Orange','Cotton','Fiesta','Peach'):
            self.assertEqual(sum(bowl+' Bowl' in t for t in titles),1)
