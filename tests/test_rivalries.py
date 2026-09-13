import unittest
from pathlib import Path
import college_football as c

class RivalryTests(unittest.TestCase):
    def test_all_19_independent_of_ap(self):
        now=c.instant('2026-09-01T00:00:00Z')
        poll=c.Poll(now,{},'test')
        for pair, (level,name) in c.RIVALRY_INFO.items():
            home,away=sorted(pair)
            g=c.Game('test',now+c.timedelta(days=1),home,away,'',{},'STATUS_SCHEDULED')
            result=c.reconcile([],{g.id:g},{},poll,now)
            self.assertEqual(len(result),1)
            self.assertTrue(c.prop(result[0],'SUMMARY').startswith('🔥'*level+' '))
            if name:self.assertIn(c.escape(name),c.prop(result[0],'SUMMARY'))
        self.assertEqual(len(c.RIVALRY_INFO),19)

    def test_all_day_then_hour_same_uid(self):
        now=c.instant('2026-10-01T00:00:00Z')
        poll=c.Poll(now,{},'test')
        g=c.Game('test',c.instant('2026-10-10T00:00:00Z'),'Alabama','Georgia','',{},'STATUS_SCHEDULED',time_known=False)
        old=c.make_event(g,poll,set(),now)
        self.assertIn('DTSTART;VALUE=DATE:20261010',old)
        self.assertEqual(c.ics_time(old,'DTEND'),c.instant('2026-10-11T00:00:00Z'))
        g.time_known=True;g.start=c.instant('2026-10-10T19:30:00Z')
        result=c.reconcile([old],{g.id:g},{},poll,c.instant('2026-10-10T10:00:00Z'))
        self.assertEqual(len(result),1)
        self.assertIn('DTSTART:20261010T193000Z',result[0])
        self.assertEqual(c.prop(old,'UID'),c.prop(result[0],'UID'))
        self.assertNotIn('horaire à confirmer',c.prop(result[0],'SUMMARY'))
        self.assertEqual(c.prop(result[0],'DESCRIPTION'),'')
