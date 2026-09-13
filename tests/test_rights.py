import copy
import test_college_football as base_tests
NOW = base_tests.NOW
import college_football as c
import unittest

class RightsTests(unittest.TestCase):
    def setUp(self):
        base = base_tests.CollegeTests()
        base.setUp()
        self.g = copy.deepcopy(base.game)
        self.poll = base.poll
        self.g.season, self.g.season_type = 2026, 2
        self.g.home_conference, self.g.networks = '8', ('ABC',)
        self.g.neutral = False

    def proof(self):
        return c.rights_broadcasts({self.g.id: self.g})

    def test_rights_are_tentative(self):
        event = c.make_event(self.g, self.poll, self.proof()[self.g.id], NOW)
        self.assertEqual(c.prop(event, 'STATUS'), 'TENTATIVE')
        self.assertIn('confirmer', c.prop(event, 'DESCRIPTION'))

    def test_french_listing_upgrades_confirmation(self):
        sources = self.proof()[self.g.id] | {c.TV}
        self.assertEqual(c.prop(c.make_event(self.g, self.poll, sources, NOW), 'STATUS'), 'CONFIRMED')

    def test_excluded_packages(self):
        for networks in [('FOX',), ('NBC',), ('TNT',), ('ESPN+',), ('Disney+',), ()]:
            self.g.networks = networks
            self.assertFalse(self.proof())

    def test_season_and_home_rights_boundaries(self):
        for field, value in [('season', 2027), ('season_type', 3), ('home_conference', '5'), ('neutral', True)]:
            original = getattr(self.g, field)
            setattr(self.g, field, value)
            self.assertFalse(self.proof())
            setattr(self.g, field, original)

    def test_network_change_removes_future_inference(self):
        old = c.make_event(self.g, self.poll, self.proof()[self.g.id], NOW)
        self.g.networks = ('FOX',)
        self.assertEqual(c.reconcile([old], {self.g.id:self.g}, self.proof(), self.poll, NOW), [])

    def test_rank_prefix(self):
        self.assertEqual(c.norm('#1 Ohio State'), 'ohio state')
