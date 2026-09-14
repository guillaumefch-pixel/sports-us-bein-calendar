import sys
import types
import importlib.util
if 'requests' not in sys.modules and importlib.util.find_spec('requests') is None:
    sys.modules['requests']=types.SimpleNamespace(RequestException=OSError)
import f1
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
class F1Tests(unittest.TestCase):
    def setUp(self):
        self.s={'course':{'round':18,'location':'Bakou','name':'Azerbaïdjan'},'cle':'qualifying','nom':'Qualifications','horaire':datetime(2026,9,25,12,tzinfo=timezone.utc),'duree_minutes':60}
    def test_generic_canal(self):
        text='\n'.join(f1.construire_vevent(self.s,None,'20260914T000000Z'))
        self.assertIn('DESCRIPTION:Canal+ (chaîne à confirmer)',text)
        self.assertNotIn('non trouvée',text)
    def test_precise_channel(self):
        d={'chaine':'Canal+ Sport 360','lien':'https://tv-sports.fr/'}
        self.assertIn('DESCRIPTION:Canal+ Sport 360',f1.construire_vevent(self.s,d,'20260914T000000Z'))
    def test_phase_mismatch_and_three_hours_rejected(self):
        d={'horaire':self.s['horaire'],'seance':'gp'}
        self.assertEqual(f1.associer_diffusions([self.s],[d]),{})
        d={'horaire':self.s['horaire']+timedelta(hours=2),'seance':None}
        self.assertEqual(f1.associer_diffusions([self.s],[d]),{})
    def test_antenna_fifteen_minutes_accepted(self):
        d={'horaire':self.s['horaire']-timedelta(minutes=15),'seance':'qualifying'}
        self.assertEqual(f1.associer_diffusions([self.s],[d]),{id(self.s):d})
    def test_parser_phase_and_direct_only(self):
        row='<li class="schedule-item" data-is-live="1"><time datetime="2026-09-25T14:00:00+02:00"></time><h3>Qualifications Sprint</h3><img class="logoChaine" alt="Canal+ Sport 360"></li>'
        d=f1.extraire_diffusions_tv(row+row.replace('data-is-live="1"','data-is-live="0"'))
        self.assertEqual(len(d),1);self.assertEqual(d[0]['seance'],'sprintQualifying')
    def test_retain_previous_announcement(self):
        e=f1.construire_vevent(self.s,{'chaine':'Canal+ Sport','lien':'https://tv-sports.fr/'},'20260914T000000Z')
        old='\r\n'.join(['BEGIN:VCALENDAR','VERSION:2.0',*e,'END:VCALENDAR'])+'\r\n'
        with TemporaryDirectory() as folder:
            p=Path(folder)/'f1.ics';p.write_text(old)
            fresh=old.replace('DESCRIPTION:Canal+ Sport','DESCRIPTION:Canal+ (chaîne à confirmer)')
            self.assertIn('DESCRIPTION:Canal+ Sport',f1.conserver_diffusions(fresh,p))
