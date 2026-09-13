#!/usr/bin/env python3
"""Agenda NCAA / AP Top 10 / Disney+ France. Python 3.11+, sans dépendances.

Les sélections déduites des droits sont TENTATIVE, les annonces FR CONFIRMED.
Voir README_COLLEGE.md pour la limite actuelle des sources de diffusion.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

UTC = timezone.utc
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
NCAA = "https://www.ncaa.com/rankings/football/fbs/associated-press"
TV = "https://tv-sports.fr/calendrier/competition/162/ncaa?direct=1"
DISNEY = "https://www.disneyplus.com/fr-fr/browse/page-15961e0d-00e3-4ff5-90b1-eb71a0f9457c"
RIGHTS = "https://www.thebluepennant.com/dossier/comment-regarder-le-college-football-en-france-en-2026/"
RIGHTS_MARKER = "rights-inference:2026"
# Périmètre 2026 : saison régulière SEC/ACC/Big12, finales et CFP ci-dessous.
# Les déductions restent provisoires, notamment pour les droits internationaux.
RIGHTS_NETWORKS = {"ABC", "ESPN", "ESPN2", "ESPNU", "SEC Network", "SECN", "ACC Network", "ACCN"}
LOG = logging.getLogger("college-football")


def instant(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Horaire sans fuseau")
    return dt.astimezone(UTC)


def stamp(dt):
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def norm(value):
    value = re.sub(r"^\s*#\d+\s+", "", value)
    value = re.sub(r"\s*\(\d+\)\s*$", "", value)
    value = unicodedata.normalize("NFKD", unescape(value)).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    aliases = {"miami fl": "miami", "miami florida": "miami", "southern cal": "usc",
               "southern california": "usc", "mississippi": "ole miss",
               "ohio st": "ohio state", "penn st": "penn state",
               "oklahoma st": "oklahoma state", "florida st": "florida state",
               "michigan st": "michigan state", "louisiana state": "lsu"}
    return aliases.get(value, value)


def fetch(url):
    if not url.startswith("https://"):
        raise ValueError("Source HTTPS requise")
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SportsCalendarBot/1.0)", "Accept-Language": "fr-FR,fr;q=0.9"})
            with urlopen(req, timeout=25) as response:
                data = response.read(15_000_001)
                if len(data) > 15_000_000:
                    raise ValueError("Réponse trop volumineuse")
                return data.decode("utf-8-sig")
        except HTTPError as exc:
            # Certains serveurs refusent urllib alors que leur contenu public
            # reste accessible à curl. Ce n'est pas une source indépendante.
            if exc.code == 403 and shutil.which("curl"):
                response = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                                           "--proto", "=https", "--proto-redir", "=https", "--max-time", "25", url],
                                          capture_output=True, timeout=30, check=True)
                if len(response.stdout) > 15_000_000:
                    raise ValueError("Réponse trop volumineuse")
                return response.stdout.decode("utf-8-sig")
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.rows, self.jsons = [], []
        self.row, self.cell, self.script = None, None, None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in ("td", "th"):
            self.cell = []
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.script = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            if self.row is not None:
                self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "script" and self.script is not None:
            self.jsons.append(json.loads("".join(self.script)))
            self.script = None


@dataclass
class Poll:
    published: datetime
    ranks: dict
    source: str


def validate_poll(poll, now):
    # Après la sélection, AP ne publie pas nécessairement chaque semaine.
    season = now.year - (now.month == 1)
    final_window = (now.month == 1 or (now.month == 12 and now.day >= 8))
    final_poll = final_window and poll.published >= datetime(season, 12, 1, tzinfo=UTC)
    max_age = 62 if final_poll else 9
    if not timedelta(days=-1) <= now - poll.published <= timedelta(days=max_age):
        raise ValueError(f"Classement périmé ou futur : {poll.source}")
    values = sorted(poll.ranks.values())
    if not 10 <= len(values) <= 12 or values[0] != 1 or values[-1] > 10:
        raise ValueError(f"Top 10 AP incomplet : {poll.source}")
    previous = None
    for index, rank in enumerate(values, 1):
        if rank != previous and rank != index:
            raise ValueError(f"Rangs AP incohérents : {poll.source}")
        previous = rank
    return poll


def espn_poll(text):
    data = json.loads(text)
    ap = next(r for r in data["rankings"] if r.get("type") == "ap")
    ranks = {norm(r["team"]["location"]): int(r["current"]) for r in ap["ranks"] if 1 <= int(r["current"]) <= 10}
    return Poll(instant(ap["date"]), ranks, ESPN + "/rankings")


def ncaa_poll(text):
    page = Page(text)
    published = next(x["datePublished"] for x in page.jsons if isinstance(x, dict) and x.get("datePublished"))
    ranks = {}
    for row in page.rows:
        if len(row) >= 3 and re.fullmatch(r"T?\d+", row[0]):
            rank = int(row[0].lstrip("T"))
            if 1 <= rank <= 10:
                ranks[norm(row[1])] = rank
    return Poll(instant(published), ranks, NCAA)


def choose_poll(polls, now):
    valid = []
    for poll in polls:
        try:
            valid.append(validate_poll(poll, now))
        except ValueError as exc:
            LOG.warning("%s", exc)
    if not valid:
        raise ValueError("Aucun classement AP frais : calendrier inchangé")
    valid.sort(key=lambda p: p.published, reverse=True)
    newest = valid[0]
    for other in valid[1:]:
        if newest.ranks != other.ranks:
            if newest.published.date() == other.published.date():
                raise ValueError("Désaccord AP le même jour : calendrier inchangé")
            LOG.warning("Publication décalée entre sources AP ; utilisation de la plus récente")
    if len(valid) < 2:
        LOG.warning("Une seule source AP disponible")
    return newest


def read_ics(text):
    lines = re.sub(r"\r?\n[ \t]", "", text).splitlines()
    if not lines or lines[0] != "BEGIN:VCALENDAR" or lines[-1] != "END:VCALENDAR":
        raise ValueError("Flux ICS invalide ou tronqué")
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            if current is not None:
                raise ValueError("VEVENT imbriqué")
            current = []
        elif line == "END:VEVENT":
            if current is None:
                raise ValueError("VEVENT invalide")
            events.append(current)
            current = None
        elif current is not None:
            current.append(line)
    if current is not None:
        raise ValueError("VEVENT tronqué")
    return events


def prop(event, key, default=""):
    for line in event:
        left, sep, right = line.partition(":")
        if sep and left.split(";")[0] == key:
            return right
    return default


def ics_time(event, key="DTSTART"):
    line = next(x for x in event if x.startswith(key + ":") or x.startswith(key + ";"))
    left, value = line.split(":", 1)
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    tz = re.search(r'TZID="?([^;\"]+)', left)
    if not tz:
        raise ValueError("Horaire ICS flottant ou journée entière refusé")
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=ZoneInfo(tz[1])).astimezone(UTC)


def escape(value):
    return str(value).replace("\\", "\\\\").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold(line):
    chunks, current = [], ""
    for char in line:
        if len((current + char).encode("utf-8")) > 75:
            chunks.append(current)
            current = " "
        current += char
    return "\r\n".join(chunks + [current])


def serialize(events):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SportsCalendar//NCAA Disney FR//FR", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:NCAA — Top 10 AP — Disney+ France", "X-WR-TIMEZONE:UTC",
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for event in sorted(events, key=lambda e: (ics_time(e), prop(e, "UID"))):
        lines += ["BEGIN:VEVENT", *event, "END:VEVENT"]
    return ("\r\n".join(fold(x) for x in lines + ["END:VCALENDAR"]) + "\r\n").encode("utf-8")


@dataclass
class Game:
    id: str
    start: datetime
    home: str
    away: str
    location: str
    aliases: dict
    status: str
    networks: tuple = ()
    home_conference: str = ""
    season: int = 0
    season_type: int = 0
    neutral: bool = False
    stage: str = ""


def competition_stage(comp):
    """Utilise les notes ESPN, jamais le seul nom d'un bowl ou season.type."""
    for note in comp.get("notes", []):
        title = note.get("headline", "")
        normalized = norm(title)
        if "college football playoff" in normalized:
            return "CFP — " + title
        for conference in ("SEC", "ACC", "Big 12", "Big Ten", "American", "Sun Belt",
                           "Conference USA", "MAC", "Mountain West", "Pac-12"):
            if re.search(r"\b" + re.escape(norm(conference)) + r" (?:football )?championship\b", normalized):
                return "Finale " + conference
    return ""


def schedule(text):
    data = json.loads(text)
    games = {}
    for event in data["events"]:
        comp = event["competitions"][0]
        status = event.get("status", {}).get("type", {}).get("name", "")
        cancelled = status in {"STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_POSTPONED", "STATUS_SUSPENDED"}
        if not cancelled and (comp.get("timeValid") is not True or comp.get("dateValid") is False):
            continue
        teams = {t["homeAway"]: t["team"] for t in comp["competitors"]}
        if set(teams) != {"home", "away"}:
            continue
        if any(norm(t.get("location", "")) in {"", "tbd", "to be determined"} for t in teams.values()):
            continue
        aliases = {}
        for team in teams.values():
            name = norm(team["location"])
            for field in ("location", "displayName", "shortDisplayName"):
                if team.get(field):
                    aliases[norm(team[field])] = name
        game = Game(str(event["id"]), instant(comp["date"]), teams["home"]["location"], teams["away"]["location"],
                    comp.get("venue", {}).get("fullName", ""), aliases, status,
                    tuple(sorted({n for b in comp.get("broadcasts", []) for n in b.get("names", [])})),
                    str(teams["home"].get("conferenceId", "")),
                    int(event.get("season", {}).get("year", 0)),
                    int(event.get("season", {}).get("type", 0)), bool(comp.get("neutralSite", False)), competition_stage(comp))
        if game.id in games and games[game.id] != game:
            raise ValueError("Calendrier ESPN contradictoire")
        games[game.id] = game
    return games


def match_broadcast(event, games):
    title = unescape(prop(event, "SUMMARY"))
    # Suffixe chaîne TV-Sports ; un (FL) au milieu du nom reste significatif.
    title = re.sub(r"\s*\([^)]*(?:Disney|ESPN|beIN)[^)]*\)\s*$", "", title, flags=re.I)
    title = re.sub(r"^(?:🏈\s*)?(?:NCAA|College Football)\s*:\s*", "", title, flags=re.I)
    parts = re.split(r"\s+(?:[-–—@]|vs\.?|at)\s+", title, flags=re.I)
    if len(parts) != 2:
        raise ValueError(f"Affiche non reconnue : {title}")
    start = ics_time(event)
    matches = []
    for game in games.values():
        names = {game.aliases.get(norm(p), norm(p)) for p in parts}
        if names == {norm(game.home), norm(game.away)} and abs(game.start - start) <= timedelta(minutes=90):
            matches.append(game)
    if len(matches) != 1:
        raise ValueError(f"Rapprochement absent ou ambigu : {title}")
    return matches[0]


def confirmed_broadcasts(text, games, source):
    """Source préalablement identifiée comme grille FR/direct NCAA football.

    Ne jamais passer ici une grille américaine, même avec Disney+ dans le titre.
    """
    found = {}
    for event in read_ics(text):
        summary = prop(event, "SUMMARY")
        description = prop(event, "DESCRIPTION")
        # Ne pas prendre en compte URL/publicités/liens généraux du flux.
        label = summary + " " + description.split("\\n")[0]
        if not re.search(r"disney\s*\+|disney\s*plus", label, re.I):
            continue
        if re.search(r"rediff|différé|replay|re-air|highlights", label, re.I):
            continue
        game = match_broadcast(event, games)
        if prop(event, "STATUS") == "CANCELLED":
            continue
        found.setdefault(game.id, set()).add(source)
    return found


def disney_broadcasts(text, games, source=DISNEY):
    """Cartes de diffusion du catalogue PUBLIC France, pas le catalogue US.

    Structure EventCard constatée sur la page française. La page d'accueil
    n'est pas une grille exhaustive ; son silence n'annule pas une annonce.
    """
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not match:
        raise ValueError("Structure Disney+ publique absente")
    page = json.loads(match[1])["props"]["pageProps"]
    if str(page.get("region", "")).upper() != "FR":
        raise ValueError("Catalogue Disney+ hors France refusé")
    found = {}
    months = {"janv": 1, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6,
              "juil": 7, "aout": 8, "sept": 9, "oct": 10, "nov": 11, "dec": 12}

    def walk(node):
        if isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, dict):
            if node.get("_type") == "EventCard":
                metadata = node.get("metadata", {})
                subtitle = norm(metadata.get("subtitle", ""))
                if "ncaa" not in subtitle or "football" not in subtitle:
                    return
                if node.get("locale") != "fr-fr":
                    raise ValueError("Carte Disney+ hors locale française")
                if metadata.get("eventBadge", {}).get("state") == "replay":
                    return
                date_text = norm(metadata.get("eventLiveTime", ""))
                date_match = re.search(r"\b(\d{1,2}) ([a-z]+) (20\d{2})\b", date_text)
                if not date_match or date_match[2] not in months:
                    raise ValueError("Date de diffusion NCAA Disney+ non reconnue")
                date = datetime(int(date_match[3]), months[date_match[2]], int(date_match[1])).date()
                parts = re.split(r"\s+(?:[-–—@]|vs\.?|at)\s+", node.get("title", ""), flags=re.I)
                candidates = [g for g in games.values() if len(parts) == 2
                              and {g.aliases.get(norm(p), norm(p)) for p in parts} == {norm(g.home), norm(g.away)}
                              and g.start.astimezone(ZoneInfo("Europe/Paris")).date() == date]
                if len(candidates) != 1:
                    raise ValueError("Affiche NCAA Disney+ absente ou ambiguë dans ESPN")
                found.setdefault(candidates[0].id, set()).add(source)
                return
            for value in node.values():
                walk(value)
    walk(page["stitchDocument"]["mainContent"])
    return found


def rights_broadcasts(games):
    """Déduction documentée, jamais une confirmation de grille française."""
    result = {}
    for g in games.values():
        if g.season != 2026 or not set(g.networks) & RIGHTS_NETWORKS:
            continue
        if g.stage.startswith("CFP"):
            eligible = g.season_type == 3 and not set(g.networks) & {"TNT", "truTV", "TBS", "HBO Max"}
        elif g.stage:
            eligible = g.stage in {"Finale SEC", "Finale ACC", "Finale Big 12", "Finale American",
                                   "Finale Sun Belt", "Finale MAC", "Finale Conference USA"}
        else:
            eligible = g.season_type == 2 and not g.neutral and g.home_conference in {"1", "4", "8"}
        if eligible:
            result[g.id] = {RIGHTS_MARKER, RIGHTS}
    return result


def make_event(game, poll, sources, now, previous=None):
    uid = f"ncaa-espn-{game.id}@sports-calendar"
    inferred = RIGHTS_MARKER in sources and not (set(sources) - {RIGHTS_MARKER, RIGHTS})
    desc = ("Disney+ (ESPN) — France" + (" — diffusion à confirmer" if inferred else "") + "\n") + " / ".join(f"{name} : AP #{poll.ranks[norm(name)]}" for name in (game.home, game.away) if norm(name) in poll.ranks)
    if game.stage:
        desc += "\n" + game.stage + " — suivi indépendamment du Top 10 AP"
    desc += "\nClassement AP publié le " + poll.published.date().isoformat()
    if inferred:
        desc += "\nSélection déduite des droits français 2026 et du réseau US : " + ", ".join(game.networks)
        desc += "\nPas de confirmation individuelle dans une grille Disney+ France."
    desc += "\nSources diffusion : " + " | ".join(sorted(set(sources) - {RIGHTS_MARKER}))
    desc += "\nHoraire : ESPN. Durée indicative : 4 h."
    body = [f"UID:{uid}", f"DTSTART:{stamp(game.start)}", f"DTEND:{stamp(game.start + timedelta(hours=4))}",
            "SUMMARY:" + escape(f"🏈 NCAA : {game.home} - {game.away}" + (" — " + game.stage if game.stage else "")), "DESCRIPTION:" + escape(desc),
            "LOCATION:" + escape(game.location), f"URL:https://www.espn.com/college-football/game/_/gameId/{game.id}",
            ("STATUS:TENTATIVE" if inferred else "STATUS:CONFIRMED"), "TRANSP:OPAQUE", "X-CFB-HOME:" + norm(game.home), "X-CFB-AWAY:" + norm(game.away),
            "X-CFB-SOURCES:" + " ".join(sorted(sources))]
    if game.stage:
        body.append("X-CFB-STAGE:" + escape(game.stage))
    ignored = ("DTSTAMP:", "LAST-MODIFIED:", "SEQUENCE:")
    if previous and [x for x in previous if not x.startswith(ignored)] == body:
        return previous
    seq = int(prop(previous or [], "SEQUENCE", "0")) + (1 if previous else 0)
    return body + [f"DTSTAMP:{stamp(now)}", f"LAST-MODIFIED:{stamp(now)}", f"SEQUENCE:{seq}"]


def reconcile(old, games, broadcasts, poll, now):
    by_uid = {}
    for event in old:
        uid = prop(event, "UID")
        if not uid or uid in by_uid:
            raise ValueError("Historique invalide : UID absent ou dupliqué")
        by_uid[uid] = event
    result = {uid: event for uid, event in by_uid.items() if ics_time(event) <= now}
    for game in games.values():
        if game.start > now and game.id in broadcasts and game.status == "STATUS_SCHEDULED":
            result.pop(f"ncaa-espn-{game.id}@sports-calendar", None)
    for game in games.values():
        uid = f"ncaa-espn-{game.id}@sports-calendar"
        if uid in result or game.start <= now:
            continue
        if game.status in {"STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_POSTPONED", "STATUS_SUSPENDED"}:
            continue
        if not game.stage and not {norm(game.home), norm(game.away)} & poll.ranks.keys():
            continue
        if game.id in broadcasts:
            result[uid] = make_event(game, poll, broadcasts[game.id], now, by_uid.get(uid))
    # Les grilles consultées ne garantissent pas une couverture exhaustive.
    # Une absence seule ne retire donc pas une annonce antérieure ; AP reste
    # appliqué et un statut explicite ESPN annule l'événement futur.
    for uid, event in by_uid.items():
        if ics_time(event) <= now or uid in result:
            continue
        if not prop(event, "X-CFB-STAGE") and not {prop(event, "X-CFB-HOME"), prop(event, "X-CFB-AWAY")} & poll.ranks.keys():
            continue
        game_id = uid.removeprefix("ncaa-espn-").split("@", 1)[0]
        game = games.get(game_id)
        if game and game.status in {"STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_POSTPONED", "STATUS_SUSPENDED"}:
            continue
        if RIGHTS_MARKER in prop(event, "X-CFB-SOURCES") and game:
            # Une sélection déduite disparaît si le réseau, le périmètre ou
            # l'horaire connus changent ; elle ne devient pas une preuve FR.
            if game_id not in broadcasts:
                continue
        LOG.warning("Annonce antérieure conservée sans nouvelle confirmation : %s", uid)
        result[uid] = event
    return list(result.values())


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        name = file.name
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            os.unlink(name)
            raise
    try:
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def run(args):
    now = datetime.now(UTC)
    polls = []
    for url, parser in ((ESPN + "/rankings", espn_poll), (NCAA, ncaa_poll)):
        try:
            polls.append(parser(fetch(url)))
        except Exception as exc:
            LOG.warning("Source AP %s : %s", url, exc)
    poll = choose_poll(polls, now)
    LOG.info("Top 10 AP : %s", poll.ranks)
    date_range = now.strftime("%Y%m%d") + "-" + (now + timedelta(days=21)).strftime("%Y%m%d")
    games = schedule(fetch(ESPN + "/scoreboard?groups=80&limit=1000&dates=" + date_range))
    if not games:
        raise ValueError("Aucun horaire ESPN confirmé : calendrier inchangé")
    urls = [TV] + [u.strip() for u in os.environ.get("CFB_FR_ICS_URLS", "").splitlines() if u.strip()]
    urls = list(dict.fromkeys(urls))
    broadcasts, successes = ({} if getattr(args, "confirmed_only", False) else rights_broadcasts(games)), []
    LOG.info("%d sélection(s) déduite(s) des droits, à confirmer individuellement", len(broadcasts))
    adapters = [(url, confirmed_broadcasts) for url in urls] + [(DISNEY, disney_broadcasts)]
    for url, adapter in adapters:
        try:
            found = adapter(fetch(url), games, url)
            if found:
                successes.append(url)
            LOG.info("%s : %d diffusion(s) Disney+ France reconnue(s)", url, len(found))
            for game_id, sources in found.items():
                broadcasts.setdefault(game_id, set()).update(sources)
        except Exception as exc:
            LOG.warning("Source diffusion %s : %s", url, exc)
    path = Path(args.output)
    if not broadcasts and not path.exists():
        raise ValueError("Aucune diffusion Disney+ France confirmée. Ce n'est pas une preuve d'absence de matchs. Calendrier inchangé.")
    if not broadcasts:
        LOG.warning("Aucune nouvelle confirmation : historique conservé et filtre AP appliqué aux annonces antérieures")
    if len(successes) < 2:
        LOG.warning("%d source(s) avec annonces FR explicites : exigence de confirmations multisources non satisfaite", len(successes))
    old = read_ics(path.read_text(encoding="utf-8")) if path.exists() else []
    if getattr(args, "confirmed_only", False):
        old = [e for e in old if ics_time(e) <= now or prop(e, "STATUS") == "CONFIRMED"]
    result = reconcile(old, games, broadcasts, poll, now)
    data = serialize(result)
    read_ics(data.decode("utf-8"))
    if not args.dry_run:
        atomic_write(path, data)
    LOG.info("%d événement(s), dont %d passé(s)%s", len(result), sum(ics_time(e) <= now for e in result), " (simulation)" if args.dry_run else "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="college_football_disney_calendar.ics")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed-only", action="store_true", help="Exclure les sélections déduites des droits")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run(args)
    except Exception as exc:
        LOG.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
