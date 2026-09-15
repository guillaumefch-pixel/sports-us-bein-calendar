#!/usr/bin/env python3
"""Agenda NCAA / AP Top 10, finales et playoffs. Python 3.11+, sans dépendances.

Tous les matchs sélectionnés sont inclus, indépendamment du diffuseur.
Seules les annonces françaises explicites ajoutent la note Disney+.
"""
from __future__ import annotations
import calendar_locations
import playoff_context

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
from dataclasses import dataclass, field
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
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SportsCalendarBot/1.0)", "Accept-Language": "fr-FR,fr;q=0.9"})
                with urlopen(req, timeout=25) as response:
                    data = response.read(15_000_001)
            except HTTPError as exc:
                if exc.code != 403 or not shutil.which("curl"):
                    raise
                response = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location", "--compressed",
                                           "--proto", "=https", "--proto-redir", "=https", "--max-time", "25", url],
                                          capture_output=True, timeout=30, check=True)
                data = response.stdout
            if len(data) > 15_000_000:
                raise ValueError("Réponse trop volumineuse")
            return data.decode("utf-8-sig")
        except Exception:
            # Cette reprise inclut les erreurs du transport de secours curl.
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def schedule_range(start, end):
    """Une plage refusée par ESPN est relue jour par jour, sans perte de dates."""
    from concurrent.futures import ThreadPoolExecutor
    base = ESPN + "/scoreboard?groups=80&limit=1000&dates="
    period = start.strftime("%Y%m%d") + "-" + end.strftime("%Y%m%d")
    try:
        return schedule(fetch(base + period))
    except Exception as exc:
        LOG.warning("Plage ESPN %s indisponible ; reprise jour par jour : %s", period, exc)
    days = []
    day = start.date()
    while day <= end.date():
        days.append(day.strftime("%Y%m%d"))
        day += timedelta(days=1)
    def read_day(date):
        return schedule(fetch(base + date))
    result = {}
    # Une journée toujours inaccessible fait échouer cette fonction avant
    # toute écriture : un calendrier partiel ne remplace jamais l'existant.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for part in pool.map(read_day, days):
            result.update(part)
    return result


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
    all_ranks: dict = field(default_factory=dict)


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
    if poll.all_ranks:
        full = sorted(poll.all_ranks.values())
        if len(full) < 25 or full[-1] > 25:
            raise ValueError("Top 25 AP incomplet : " + poll.source)
        prior = None
        for index, rank in enumerate(full, 1):
            if rank != prior and rank != index:
                raise ValueError("Top 25 AP incohérent : " + poll.source)
            prior = rank
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
    all_ranks = {norm(r["team"]["location"]): int(r["current"]) for r in ap["ranks"] if 1 <= int(r["current"]) <= 25}
    return Poll(instant(ap["date"]), ranks, ESPN + "/rankings", all_ranks)


def ncaa_poll(text):
    page = Page(text)
    published = next(x["datePublished"] for x in page.jsons if isinstance(x, dict) and x.get("datePublished"))
    ranks, all_ranks = {}, {}
    for row in page.rows:
        if len(row) >= 3 and re.fullmatch(r"T?\d+", row[0]):
            rank = int(row[0].lstrip("T"))
            if 1 <= rank <= 25:
                all_ranks[norm(row[1])] = rank
            if 1 <= rank <= 10:
                ranks[norm(row[1])] = rank
    return Poll(instant(published), ranks, NCAA, all_ranks)


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
        if newest.ranks != other.ranks or (newest.all_ranks and other.all_ranks and newest.all_ranks != other.all_ranks):
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
    if "VALUE=DATE" in left:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=UTC)
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
             "METHOD:PUBLISH", "X-WR-CALNAME:NCAA — Top 10 AP + finales et playoffs", "X-WR-TIMEZONE:UTC",
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
    home_display: str = ""
    away_display: str = ""
    time_known: bool = True


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
        if not cancelled and comp.get("dateValid") is False:
            continue
        teams = {t["homeAway"]: t["team"] for t in comp["competitors"]}
        if set(teams) != {"home", "away"}:
            continue
        if any(norm(t.get("location", "")) in {"", "tbd", "to be determined"} for t in teams.values()):
            continue
        if not cancelled and comp.get("timeValid") is not True and not watched(teams["home"]["location"], teams["away"]["location"]):
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
                    int(event.get("season", {}).get("type", 0)), bool(comp.get("neutralSite", False)), competition_stage(comp),
                    teams["home"].get("displayName", teams["home"]["location"]),
                    teams["away"].get("displayName", teams["away"]["location"]), comp.get("timeValid") is True)
        if not game.time_known:
            day = game.start.astimezone(ZoneInfo("America/New_York")).date()
            game.start = datetime(day.year, day.month, day.day, tzinfo=UTC)
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


# Affiches demandées par l'utilisateur : ne modifie jamais la sélection AP.
MUST_WATCH = {frozenset(pair) for pair in (
    ("ohio state", "michigan"), ("texas", "oklahoma"),
    ("texas", "texas a m"), ("alabama", "auburn"),
    ("alabama", "georgia"), ("georgia", "florida"),
    ("georgia", "auburn"), ("georgia", "georgia tech"),
    ("ole miss", "mississippi state"), ("lsu", "alabama"),
    ("lsu", "texas"), ("notre dame", "usc"),
    ("notre dame", "michigan"), ("indiana", "purdue"),
    ("indiana", "ohio state"), ("miami", "florida state"),
    ("miami", "florida"), ("oregon", "oregon state"),
    ("oregon", "washington"),
)}


# Barème éditorial fixe (1 à 3), distinct du classement AP dynamique.
RIVALRY_INFO = {frozenset((a,b)):(level,name) for a,b,level,name in (
    ('ohio state','michigan',3,'The Game'),
    ('texas','oklahoma',3,'Red River Rivalry'),
    ('texas','texas a m',3,'Lone Star Showdown'),
    ('alabama','auburn',3,'Iron Bowl'),
    ('alabama','georgia',3,''),
    ('georgia','florida',3,"World’s Largest Outdoor Cocktail Party"),
    ('georgia','auburn',2,"Deep South’s Oldest Rivalry"),
    ('georgia','georgia tech',2,'Clean, Old-Fashioned Hate'),
    ('ole miss','mississippi state',3,'Egg Bowl'),
    ('lsu','alabama',3,''), ('lsu','texas',2,''),
    ('notre dame','usc',3,'Jeweled Shillelagh'),
    ('notre dame','michigan',2,''), ('indiana','purdue',1,'Old Oaken Bucket'),
    ('indiana','ohio state',2,''), ('miami','florida state',3,''),
    ('miami','florida',2,''), ('oregon','oregon state',2,''),
    ('oregon','washington',3,''),
)}

def watched(home, away):
    return frozenset((norm(home), norm(away))) in MUST_WATCH


def event_title(game, home, away):
    level, rivalry = RIVALRY_INFO.get(frozenset((norm(game.home), norm(game.away))), (0, ""))
    marker = ("🔥" * level + " ") if level else ""
    suffix = (" — " + rivalry if rivalry else "") + (" — horaire à confirmer" if not game.time_known else "")
    stage = game.stage
    if stage.startswith("Finale "):
        prefix = stage.removeprefix("Finale ") + " Final"
    elif stage.startswith("CFP"):
        text = norm(stage)
        if "national championship" in text:
            round_name = "Finale nationale"
        elif "semifinal" in text:
            round_name = "Demi-finale"
        elif "quarterfinal" in text:
            round_name = "Quart de finale"
        elif "first round" in text:
            round_name = "Premier tour"
        else:
            round_name = "Playoffs"
        bowl = next((name + " Bowl" for name in ("Rose", "Sugar", "Orange", "Cotton", "Fiesta", "Peach")
                     if re.search(r"\b" + name.lower() + r" bowl\b", text)), "")
        prefix = "CFP " + round_name + (" — " + bowl if bowl else "")
    else:
        return f"{marker}🏈 NCAA : {home} - {away}{suffix}"
    return f"{marker}🏈 {prefix} - {home} - {away}{suffix}"


def season_records(text, season):
    """Bilans globaux ESPN, jamais le seul bilan de conférence."""
    data = json.loads(text)
    result = {}
    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            if node.get("name") == "overall" and "entries" in node:
                if int(node.get("season", 0)) != season:
                    raise ValueError("Bilans NCAA d’une autre saison")
                for entry in node["entries"]:
                    overall = [x.get("displayValue", "") for x in entry["stats"] if x.get("name") == "overall"]
                    if overall:
                        match = re.fullmatch(r"(\d+)-(\d+)(?:-(\d+))?", overall[0].strip())
                        if len(set(overall)) != 1 or not match:
                            raise ValueError("Bilan global NCAA invalide")
                        w, l, t = (int(match.group(i) or 0) for i in (1, 2, 3))
                    else:
                        stats = {}
                        for stat in entry["stats"]:
                            key = stat.get("name")
                            if key in ("wins", "losses", "ties"):
                                if key in stats:
                                    raise ValueError("Bilan global NCAA ambigu")
                                stats[key] = stat.get("value")
                        values = [stats.get("wins"), stats.get("losses"), stats.get("ties", 0)]
                        if any(v is None or float(v) < 0 or not float(v).is_integer() for v in values):
                            raise ValueError("Bilan NCAA invalide")
                        w, l, t = map(int, values)
                    label = f"{w}W/{l}L" + (f"/{t}T" if t else "")
                    key = norm(entry["team"]["location"])
                    if key in result and result[key] != label:
                        raise ValueError("Bilans NCAA contradictoires")
                    result[key] = label
            for key in ("children", "standings"):
                if key in node:
                    walk(node[key])
    walk(data)
    if not result:
        raise ValueError("Tableau des bilans NCAA vide")
    return result


def load_records(season):
    result = {}
    for group in (80, 81):  # FBS et FCS : inclure aussi les adversaires FCS.
        url = "https://site.api.espn.com/apis/v2/sports/football/college-football/standings?group=" + str(group)
        try:
            found = season_records(fetch(url), season)
            if any(k in result and result[k] != v for k, v in found.items()):
                raise ValueError("Deux bilans différents pour la même équipe")
            result.update(found)
            LOG.info("Bilans NCAA groupe %s : %d équipes", group, len(found))
        except Exception as exc:
            LOG.warning("Bilans NCAA groupe %s indisponibles : %s ; anciens bilans conservés si disponibles", group, exc)
    return result


def make_event(game, poll, sources, now, previous=None, records=None):
    uid = f"ncaa-espn-{game.id}@sports-calendar"
    confirmed = set(sources) - {RIGHTS, RIGHTS_MARKER}
    desc = "Disney+" if confirmed else ""
    def label(location, display):
        name = "LSU" if norm(location) == "lsu" else (display or location)
        # Top 10 et affichage complet restent séparés.
        rank = poll.ranks.get(norm(location))
        if rank is None:
            rank = {k:v for k,v in poll.all_ranks.items() if v > 10}.get(norm(location))
        return f"{name} #{rank}" if rank is not None and 1 <= rank <= 25 else f"{name} (NC)"
    records = records or {}
    home_record = records.get(norm(game.home), prop(previous or [], "X-CFB-HOME-RECORD"))
    away_record = records.get(norm(game.away), prop(previous or [], "X-CFB-AWAY-RECORD"))
    home = label(game.home, game.home_display) + (f" [{home_record}]" if home_record else "")
    away = label(game.away, game.away_display) + (f" [{away_record}]" if away_record else "")
    dates = [f"DTSTART:{stamp(game.start)}", f"DTEND:{stamp(game.start + timedelta(hours=4))}"] if game.time_known else [f"DTSTART;VALUE=DATE:{game.start:%Y%m%d}", f"DTEND;VALUE=DATE:{game.start + timedelta(days=1):%Y%m%d}"]
    body = [f"UID:{uid}", *dates,
            "SUMMARY:" + escape(event_title(game, home, away)), "DESCRIPTION:" + escape(desc),
            "LOCATION:" + escape(game.location), f"URL:https://www.espn.com/college-football/game/_/gameId/{game.id}",
            "STATUS:CONFIRMED", "TRANSP:OPAQUE", "X-CFB-HOME:" + norm(game.home), "X-CFB-AWAY:" + norm(game.away),
            "X-CFB-SOURCES:" + " ".join(sorted(sources))]
    body.append("X-CFB-HOME-DISPLAY:" + escape("LSU" if norm(game.home)=="lsu" else (game.home_display or game.home)))
    if home_record:
        body.append("X-CFB-HOME-RECORD:" + home_record)
    if away_record:
        body.append("X-CFB-AWAY-RECORD:" + away_record)
    if game.stage:
        body.append("X-CFB-STAGE:" + escape(game.stage))
    ignored = ("DTSTAMP:", "LAST-MODIFIED:", "SEQUENCE:")
    if previous and [x for x in previous if not x.startswith(ignored)] == body:
        return previous
    seq = int(prop(previous or [], "SEQUENCE", "0")) + (1 if previous else 0)
    return body + [f"DTSTAMP:{stamp(now)}", f"LAST-MODIFIED:{stamp(now)}", f"SEQUENCE:{seq}"]


def event_started(event, now):
    if any(line.startswith('DTSTART;VALUE=DATE:') for line in event):
        return ics_time(event, 'DTEND') <= now
    return ics_time(event) <= now


def reconcile(old, games, broadcasts, poll, now, records=None):
    by_uid = {}
    for event in old:
        uid = prop(event, "UID")
        if not uid or uid in by_uid:
            raise ValueError("Historique invalide : UID absent ou dupliqué")
        by_uid[uid] = event
    result = {uid: event for uid, event in by_uid.items() if event_started(event, now)}
    for game in games.values():
        if (game.start > now or not game.time_known) and game.status == "STATUS_SCHEDULED":
            result.pop(f"ncaa-espn-{game.id}@sports-calendar", None)
    for game in games.values():
        uid = f"ncaa-espn-{game.id}@sports-calendar"
        if uid in result or (game.start + (timedelta(days=1) if not game.time_known else timedelta()) <= now and game.status != "STATUS_IN_PROGRESS"):
            continue
        if game.status in {"STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_POSTPONED", "STATUS_SUSPENDED"}:
            continue
        if not game.stage and not watched(game.home, game.away) and not {norm(game.home), norm(game.away)} & poll.ranks.keys():
            continue
        result[uid] = make_event(game, poll, broadcasts.get(game.id, set()), now, by_uid.get(uid), records)
    # Les grilles consultées ne garantissent pas une couverture exhaustive.
    # Une absence seule ne retire donc pas une annonce antérieure ; AP reste
    # appliqué et un statut explicite ESPN annule l'événement futur.
    for uid, event in by_uid.items():
        if event_started(event, now) or uid in result:
            continue
        if not prop(event, "X-CFB-STAGE") and not watched(prop(event,"X-CFB-HOME"), prop(event,"X-CFB-AWAY")) and not {prop(event, "X-CFB-HOME"), prop(event, "X-CFB-AWAY")} & poll.ranks.keys():
            continue
        game_id = uid.removeprefix("ncaa-espn-").split("@", 1)[0]
        game = games.get(game_id)
        if game and game.status in {"STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_POSTPONED", "STATUS_SUSPENDED"}:
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
    games = {}
    season = now.year if now.month >= 2 else now.year - 1
    end = datetime(season + 1, 2, 1, tzinfo=UTC)
    cursor = now - timedelta(days=1)
    while cursor < end:
        stop = min(cursor + timedelta(days=30), end)
        games.update(schedule_range(cursor, stop))
        cursor = stop
    if not games:
        raise ValueError("Aucun horaire ESPN confirmé : calendrier inchangé")
    urls = [TV] + [u.strip() for u in os.environ.get("CFB_FR_ICS_URLS", "").splitlines() if u.strip()]
    urls = list(dict.fromkeys(urls))
    broadcasts, successes = {}, []
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
    old = read_ics(path.read_text(encoding="utf-8")) if path.exists() else []
    records = load_records(season)
    result = reconcile(old, games, broadcasts, poll, now, records)
    data = serialize(result)
    data = playoff_context.enrich(data.decode("utf-8"), path, "NCAA").encode("utf-8")
    data = calendar_locations.normalize_calendar(data.decode("utf-8"), path, "NCAA").encode("utf-8")
    read_ics(data.decode("utf-8"))
    if not args.dry_run:
        atomic_write(path, data)
    LOG.info("%d événement(s), dont %d déjà commencé(s)%s", len(result), sum(ics_time(e) <= now for e in result), " (simulation)" if args.dry_run else "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="college_football_disney_calendar.ics")
    parser.add_argument("--dry-run", action="store_true")
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
