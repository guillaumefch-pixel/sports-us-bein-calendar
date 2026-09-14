import copy
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import tempfile
import tennis as t

NOW=datetime(2026,9,10,8,tzinfo=timezone.utc)
FIX=Path(__file__).parent/'fixtures'
class TennisTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((FIX/'us-open.json').read_text())
        self.r=t.rankings(json.loads((FIX/'atp-rank.json').read_text()),'atp',NOW)
        self.games=t.parse_schedule(self.data,'atp')
        self.final=next(m for m in self.games.values() if m.round=='Final')
        self.m=replace(self.final,state='pre',status='STATUS_SCHEDULED',start=NOW+timedelta(days=2))
    def test_only_singles_main_draw(self):
        self.assertEqual(len(self.games),4)
        self.assertTrue(all(m.round in t.ROUNDS for m in self.games.values()))
    def test_wta_separate(self):
        self.data['leagues']=[{'slug':'wta'}]
        matches=t.parse_schedule(self.data,'wta')
        self.assertEqual(len(matches),4)
        self.assertTrue(all(m.tour=='wta' for m in matches.values()))
        self.assertFalse(set(self.games)&set(matches))
    def test_top5_entry_exit_and_all_semis(self):
        early=replace(self.m,round='Quarterfinal')
        p,q=[x[0] for x in early.players]
        self.assertTrue(t.selected(early,{p:5,q:18}))
        self.assertFalse(t.selected(early,{p:6,q:18}))
        self.assertTrue(t.selected(replace(early,round='Semifinal'),{p:80,q:90}))
    def test_global_rank_not_tournament_seed(self):
        e=t.make_event(self.m,self.r,NOW)
        self.assertIn('Alexander Zverev [#2]',t.cal.prop(e,'SUMMARY'))
        self.assertNotIn('Zverev [#1]',t.cal.prop(e,'SUMMARY'))
    def test_unknown_rank_display_nc(self):
        self.assertIn('[NC]',t.cal.prop(t.make_event(self.m,{},NOW),'SUMMARY'))
    def test_rank_stale_or_truncated(self):
        d=json.loads((FIX/'atp-rank.json').read_text())
        with self.assertRaises(ValueError):t.rankings(d,'atp',NOW+timedelta(days=40))
        d['rankings'][0]['ranks']=d['rankings'][0]['ranks'][:4]
        with self.assertRaises(ValueError):t.rankings(d,'atp',NOW)
    def test_unknown_time_then_confirmed_uid_stable(self):
        e=t.make_event(replace(self.m,known=False),self.r,NOW)
        self.assertTrue(any(x.startswith('DTSTART;VALUE=DATE:') for x in e))
        f=t.make_event(self.m,self.r,NOW,e)
        self.assertEqual(t.cal.prop(e,'UID'),t.cal.prop(f,'UID'))
        self.assertEqual(t.cal.prop(f,'SEQUENCE'),'1')
    def test_repeat_no_change(self):
        e=t.make_event(self.m,self.r,NOW)
        self.assertEqual(e,t.make_event(self.m,self.r,NOW+timedelta(hours=1),e))
    def test_history_and_dynamic_removal(self):
        m=replace(self.m,round='Round 1');r={m.players[0][0]:5}
        e=t.make_event(m,r,NOW)
        out=t.reconcile([e],{m.uid:m},{'atp':{m.players[0][0]:6}},NOW)
        self.assertEqual(out,[])
        self.assertEqual(t.reconcile([e],{}, {'atp':{}},m.start+timedelta(days=1)),[e])
    def test_failed_rank_preserves_old(self):
        e=t.make_event(self.m,self.r,NOW)
        self.assertEqual(t.reconcile([e],{}, {},NOW),[e])
    def test_cancel_and_dedup(self):
        e=t.make_event(self.m,self.r,NOW)
        out=t.reconcile([e],{self.m.uid:replace(self.m,status='STATUS_CANCELED')},{'atp':self.r},NOW)
        self.assertEqual(out,[])
        with self.assertRaises(ValueError):t.reconcile([e,e],{}, {},NOW)
    def test_rights_fr_not_espn_us(self):
        self.assertEqual(t.broadcaster(self.m),'Eurosport')
        self.assertEqual(t.broadcaster(replace(self.m,tournament='wimbledon')),'beIN SPORTS')
        self.assertEqual(t.broadcaster(replace(self.m,channels=('Eurosport 2',))),'Eurosport 2')
    def test_rg_night_and_finals(self):
        m=replace(self.m,tournament='french open',round='Quarterfinal',court='Court Philippe-Chatrier',start=datetime(2026,6,2,19,tzinfo=timezone.utc))
        self.assertEqual(t.broadcaster(m),'Prime Video')
        self.assertIn('france.tv + Prime Video',t.broadcaster(replace(m,round='Final')))
        self.assertIn('france.tv',t.broadcaster(replace(m,court='Court Suzanne-Lenglen')))
    def test_rights_expire(self):
        self.assertEqual(t.broadcaster(replace(self.m,start=self.m.start.replace(year=2040))),'Diffusion à confirmer')
    def test_ics_roundtrip_utf8_utc(self):
        e=t.make_event(self.m,self.r,NOW);raw=t.serialize([e])
        self.assertEqual(t.cal.read_ics(raw.decode()),[e])
        self.assertTrue(all(len(x)<=75 for x in raw.split(b'\r\n')))
        self.assertTrue(t.cal.prop(e,'DTSTART').endswith('Z'))
        self.assertIn('Arthur Ashe Stadium\\, New York',t.cal.prop(e,'LOCATION'))
    def test_empty_schedule_is_normal(self):
        self.assertEqual(t.parse_schedule({'leagues':[{'slug':'atp'}],'events':[]},'atp'),{})
    def test_malformed_schedule_fails(self):
        with self.assertRaises(ValueError):t.parse_schedule({},'atp')
    def test_no_tbd_players(self):
        for g in self.data['events'][0]['groupings']:
            for c in g['competitions']:
                for p in c['competitors']:p['id']='-1'
        self.assertEqual(t.parse_schedule(self.data,'atp'),{})
    def test_full_outage_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'tennis.ics';raw=t.serialize([t.make_event(self.m,self.r,NOW)]);path.write_bytes(raw)
            with patch.object(t.cal,'fetch',side_effect=OSError('offline')):
                with self.assertRaises(RuntimeError):t.run(path)
            self.assertEqual(path.read_bytes(),raw)
