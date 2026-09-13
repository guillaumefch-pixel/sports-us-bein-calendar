import argparse
import copy
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import college_football as c

FIX = Path(__file__).parent / "fixtures"
NOW = c.instant("2026-09-12T10:00:00Z")


def fixture(name):
    return (FIX / name).read_text(encoding="utf-8")


class CollegeTests(unittest.TestCase):
    def setUp(self):
        self.poll = c.espn_poll(fixture("espn_poll.json"))
        self.games = c.schedule(fixture("espn_schedule.json"))
        self.game = next(g for g in self.games.values() if {c.norm(g.home), c.norm(g.away)} == {"texas", "ohio state"})

    def event(self, game=None):
        return c.make_event(game or self.game, self.poll, {"https://fixture.invalid/fr"}, NOW)

    def test_live_captured_ranking_sources_agree(self):
        ncaa = c.ncaa_poll(fixture("ncaa_poll.html"))
        self.assertEqual(self.poll.ranks, ncaa.ranks)
        self.assertEqual(len(c.choose_poll([ncaa, self.poll], NOW).ranks), 10)

    def test_stale_poll_rejected(self):
        with self.assertRaises(ValueError):
            c.choose_poll([self.poll], NOW + timedelta(days=20))

    def test_conflicting_same_day_polls_rejected(self):
        other = copy.deepcopy(self.poll)
        other.ranks["alabama"] = other.ranks.pop("texas")
        with self.assertRaises(ValueError):
            c.choose_poll([self.poll, other], NOW)

    def test_newer_week_wins(self):
        other = copy.deepcopy(self.poll)
        other.published += timedelta(days=1)
        other.ranks["alabama"] = other.ranks.pop("texas")
        self.assertIs(c.choose_poll([self.poll, other], NOW), other)

    def test_tenth_place_tie_included(self):
        self.poll.ranks["extra"] = 10
        c.validate_poll(self.poll, NOW)

    def test_real_tv_bein_is_not_disney(self):
        self.assertEqual(c.confirmed_broadcasts(fixture("tv_sports.ics"), self.games, c.TV), {})

    def test_real_disney_fr_without_ncaa_is_not_confirmation(self):
        self.assertEqual(c.disney_broadcasts(fixture("disney_fr.html"), self.games), {})

    def test_foreign_disney_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            c.disney_broadcasts(fixture("disney_fr.html").replace('"region": "fr"', '"region": "us"'), self.games)

    def test_two_sources_and_reversed_names_merge(self):
        # Synthétique : cette modification ne représente PAS une vraie diffusion.
        text = fixture("tv_sports.ics").replace("beIN SPORTS MAX 4", "Disney+")
        one = c.confirmed_broadcasts(text, self.games, "https://fixture.invalid/one")
        two = c.confirmed_broadcasts(text.replace("Texas – Ohio State", "Ohio State – Texas"), self.games, "https://fixture.invalid/two")
        merged = {k: one[k] | two[k] for k in one}
        events = c.reconcile([], self.games, merged, self.poll, NOW)
        self.assertEqual(len(events), 1)
        self.assertIn("one", c.prop(events[0], "DESCRIPTION"))
        self.assertIn("two", c.prop(events[0], "DESCRIPTION"))

    def test_replay_excluded(self):
        text = fixture("tv_sports.ics").replace("beIN SPORTS MAX 4", "Disney+").replace("En direct", "rediffusion")
        self.assertEqual(c.confirmed_broadcasts(text, self.games, c.TV), {})

    def test_two_similar_teams_not_confused(self):
        self.assertNotEqual(c.norm("Miami (FL)"), c.norm("Miami (OH)"))
        self.assertNotEqual(c.norm("Texas"), c.norm("Texas A&M"))

    def test_rank_exit_removes_future_not_past(self):
        past = copy.deepcopy(self.game)
        past.id = "past"
        past.start = NOW - timedelta(days=1)
        old = [self.event(), self.event(past)]
        self.poll.ranks.pop("texas")
        self.poll.ranks.pop("ohio state")
        events = c.reconcile(old, self.games, {}, self.poll, NOW)
        self.assertEqual(events, [old[1]])

    def test_one_remaining_top10_team_keeps_match(self):
        old = self.event()
        self.poll.ranks.pop("texas")
        self.assertEqual(len(c.reconcile([old], self.games, {}, self.poll, NOW)), 1)

    def test_rank_entry_adds_match(self):
        polls = copy.deepcopy(self.poll)
        polls.ranks.clear()
        proofs = {self.game.id: {c.TV}}
        self.assertEqual(c.reconcile([], self.games, proofs, polls, NOW), [])
        polls.ranks["texas"] = 10
        self.assertEqual(len(c.reconcile([], self.games, proofs, polls, NOW)), 1)

    def test_time_update_keeps_uid_increments_sequence(self):
        old = self.event()
        self.game.start += timedelta(hours=1)
        new = c.make_event(self.game, self.poll, {"https://fixture.invalid/fr"}, NOW, old)
        self.assertEqual(c.prop(old, "UID"), c.prop(new, "UID"))
        self.assertEqual(c.prop(new, "SEQUENCE"), "1")
        self.assertNotEqual(c.prop(old, "DTSTART"), c.prop(new, "DTSTART"))

    def test_unchanged_run_is_byte_identical(self):
        old = self.event()
        new = c.make_event(self.game, self.poll, {"https://fixture.invalid/fr"}, NOW + timedelta(hours=1), old)
        self.assertEqual(c.serialize([old]), c.serialize([new]))

    def test_explicit_cancellation_removes_future(self):
        old = self.event()
        self.game.status = "STATUS_CANCELED"
        self.assertEqual(c.reconcile([old], self.games, {self.game.id: {c.TV}}, self.poll, NOW), [])

    def test_postponed_game_with_old_start_in_past_is_updated(self):
        old_game = copy.deepcopy(self.game)
        old_game.start = NOW - timedelta(hours=1)
        old = self.event(old_game)
        self.game.status = "STATUS_SCHEDULED"
        events = c.reconcile([old], self.games, {self.game.id: {c.TV}}, self.poll, NOW)
        self.assertEqual(len(events), 1)
        self.assertEqual(c.ics_time(events[0]), self.game.start)
        self.assertEqual(c.prop(events[0], "UID"), c.prop(old, "UID"))

    def test_unknown_kickoff_is_not_invented(self):
        data = json.loads(fixture("espn_schedule.json"))
        data["events"] = [data["events"][0]]
        data["events"][0]["competitions"][0]["timeValid"] = False
        self.assertEqual(c.schedule(json.dumps(data)), {})

    def test_disney_synthetic_ncaa_card(self):
        # Cas positif synthétique dérivé de la structure EventCard réelle.
        date = self.game.start.astimezone(c.ZoneInfo("Europe/Paris"))
        card = {"_type": "EventCard", "locale": "fr-fr", "title": f"{self.game.home} - {self.game.away}",
                "metadata": {"subtitle": "NCAA - Football • 2026", "eventLiveTime": f"{date.day} sept. 2026",
                             "eventBadge": {"state": "upcoming"}}}
        data = {"props": {"pageProps": {"region": "fr", "stitchDocument": {"mainContent": [card]}}}}
        text = '<script id="__NEXT_DATA__">' + json.dumps(data) + '</script>'
        self.assertEqual(c.disney_broadcasts(text, self.games), {self.game.id: {c.DISNEY}})

    def test_missing_confirmation_keeps_previous(self):
        old = self.event()
        self.assertEqual(c.reconcile([old], {}, {}, self.poll, NOW), [old])

    def test_utc_and_dst(self):
        self.assertEqual(c.ics_time(["DTSTART;TZID=Europe/Paris:20261024T190000"]), c.instant("2026-10-24T17:00Z"))
        self.assertEqual(c.ics_time(["DTSTART;TZID=Europe/Paris:20261025T190000"]), c.instant("2026-10-25T18:00Z"))
        with self.assertRaises(ValueError):
            c.ics_time(["DTSTART:20261025T190000"])

    def test_ics_unicode_folding_and_roundtrip(self):
        event = self.event()
        event.append("X-TEST:" + c.escape("é🏈," * 100 + "\nfin;"))
        data = c.serialize([event])
        self.assertTrue(all(len(line) <= 75 for line in data.split(b"\r\n")))
        self.assertEqual(c.read_ics(data.decode()), [event])
        self.assertTrue(c.prop(event, "DTSTART").endswith("Z"))

    def test_truncated_ics_rejected(self):
        with self.assertRaises(ValueError):
            c.read_ics("BEGIN:VCALENDAR\nBEGIN:VEVENT\nEND:VCALENDAR")

    def test_duplicate_history_uid_refused(self):
        with self.assertRaises(ValueError):
            c.reconcile([self.event(), self.event()], self.games, {}, self.poll, NOW)

    def test_atomic_write_failure_keeps_old_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "calendar.ics"
            path.write_bytes(b"old")
            with patch.object(c.os, "replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    c.atomic_write(path, b"new")
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_public_http403_transport_fallback(self):
        error = c.HTTPError(c.ESPN, 403, "Forbidden", {}, None)
        response = c.subprocess.CompletedProcess([], 0, b'{"events": []}', b'')
        with patch.object(c, "urlopen", side_effect=error), patch.object(c.shutil, "which", return_value="/usr/bin/curl"), patch.object(c.subprocess, "run", return_value=response) as run:
            self.assertEqual(c.fetch(c.ESPN), '{"events": []}')
            self.assertIn("--fail", run.call_args[0][0])
            self.assertNotIn("shell", run.call_args[1])

    def test_default_captured_sources_do_not_invent_calendar(self):
        def get(url):
            if url.endswith("/rankings"):
                return fixture("espn_poll.json")
            if url == c.NCAA:
                return fixture("ncaa_poll.html")
            if url == c.TV:
                return fixture("tv_sports.ics")
            if url == c.DISNEY:
                return fixture("disney_fr.html")
            return fixture("espn_schedule.json")
        with tempfile.TemporaryDirectory() as folder, patch.object(c, "fetch", side_effect=get), patch.object(c, "choose_poll", return_value=self.poll):
            path = Path(folder) / "calendar.ics"
            with self.assertRaisesRegex(ValueError, "Aucune diffusion"):
                c.run(argparse.Namespace(output=str(path), dry_run=False))
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
