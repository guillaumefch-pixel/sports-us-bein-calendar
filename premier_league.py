#!/usr/bin/env python3
"""Premier League Big Six / Canal+ France. Script autonome Python 3.11+."""
from __future__ import annotations
import team_context
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
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
UTC = timezone.utc
LOG = logging.getLogger("premier-league")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
TV = "https://tv-sports.fr/calendrier/competition/3/premier-league?direct=1"
RIGHTS = "https://www.canalplusgroup.com/fr/press/renouvellement-de-la-premier-league-jusqu-en-2028"
BIG_SIX = {"Manchester City", "Manchester United", "Liverpool", "Arsenal", "Chelsea", "Tottenham Hotspur"}
CANCELLED = {"STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_POSTPONED", "STATUS_SUSPENDED"}


def instant(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Horaire sans fuseau")
    return dt.astimezone(UTC)

def stamp(dt):
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

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

def canonical(name):
    key = unicodedata.normalize('NFKD', name).encode('ascii','ignore').decode().lower()
    key = re.sub(r'[^a-z0-9]+',' ',key).strip()
    aliases = {'manchester city':'Manchester City', 'man city':'Manchester City',
               'manchester united':'Manchester United', 'man united':'Manchester United',
               'man utd':'Manchester United','liverpool':'Liverpool','arsenal':'Arsenal',
               'chelsea':'Chelsea','tottenham':'Tottenham Hotspur','tottenham hotspur':'Tottenham Hotspur',
               'spurs':'Tottenham Hotspur','wolves':'Wolverhampton Wanderers',
               'wolverhampton':'Wolverhampton Wanderers','brighton':'Brighton & Hove Albion',
               'brighton hove albion':'Brighton & Hove Albion', 'leeds':'Leeds United',
               'newcastle':'Newcastle United','west ham':'West Ham United',
               'nottingham':'Nottingham Forest','nottm forest':'Nottingham Forest',
               'ipswich':'Ipswich Town','coventry':'Coventry City','leicester':'Leicester City'}
    return aliases.get(key, name.strip())


@dataclass
class Game:
    id: str
    start: datetime
    home: str
    away: str
    venue: str
    known: bool
    state: str
    status: str
    season: int


def parse_schedule(text):
    data=json.loads(text)
    if not isinstance(data.get('events'),list):
        raise ValueError('Calendrier ESPN invalide')
    if not any(l.get('slug')=='eng.1' for l in data.get('leagues',[])):
        raise ValueError('Compétition différente de la Premier League')
    games={}
    for e in data['events']:
        comp=e['competitions'][0]
        teams={t['homeAway']:t['team'] for t in comp['competitors']}
        if set(teams)!={'home','away'} or comp.get('dateValid') is False:
            continue
        if any(not t.get('id') or t.get('displayName','').lower() in ('','tbd') for t in teams.values()):
            continue
        status=comp.get('status',e.get('status',{})).get('type',{})
        start=instant(comp['date'])
        known=comp.get('timeValid') is True
        if not known:
            day=start.astimezone(ZoneInfo('Europe/London')).date()
            start=datetime(day.year,day.month,day.day,tzinfo=UTC)
        g=Game(str(e['id']),start,canonical(teams['home']['displayName']),
               canonical(teams['away']['displayName']),comp.get('venue',{}).get('fullName',''),
               known,status.get('state','pre'),status.get('name',''),int(e['season']['year']))
        if g.id in games and games[g.id]!=g:
            raise ValueError('Deux versions contradictoires du même match')
        games[g.id]=g
    return games


# Hiérarchie éditoriale : trois vrais derbies majeurs, puis rivalités et grandes affiches.
RIVALRIES={frozenset(pair):(level,name) for pair,level,name in (
    (('Manchester United','Manchester City'),3,'Derby de Manchester'),
    (('Arsenal','Tottenham Hotspur'),3,'North London Derby'),
    (('Liverpool','Manchester United'),3,'Liverpool–Manchester United'),
    (('Liverpool','Manchester City'),2,''),
    (('Arsenal','Manchester United'),2,''),
    (('Chelsea','Tottenham Hotspur'),2,''),
    (('Arsenal','Chelsea'),2,''),
)}


def title(g):
    pair=frozenset((g.home,g.away))
    level,name=RIVALRIES.get(pair,(1 if pair<=BIG_SIX and len(pair)==2 else 0,''))
    # Pas de répétition pour Liverpool–Manchester United.
    suffix=' — '+name if name and name!='Liverpool–Manchester United' else ''
    return ('🔥'*level+' ' if level else '')+f'⚽ Premier League : {g.home} - {g.away}'+suffix+(' — horaire à confirmer' if not g.known else '')


def tv_channels(text,games):
    found={}
    for event in read_ics(text):
        summary=prop(event,'SUMMARY')
        label=summary+' '+prop(event,'DESCRIPTION').split('\\n')[0]
        if re.search(r'rediff|différé|replay',label,re.I):
            continue
        match=re.search(r'\s*\((Canal\+[^)]*)\)\s*$',summary,re.I)
        if not match:
            continue
        channel=match[1].replace('Canal+','CANAL+')
        # Accepter uniquement une chaîne Canal, pas un autre bouquet ajouté au texte.
        if not re.fullmatch(r'CANAL\+(?:\s+(?:FOOT|SPORT(?:\s+360)?|LIVE(?:\s+\d+)?|PREMIER LEAGUE|DECALE))?',channel,re.I):
            continue
        names=re.split(r'\s+[–—-]\s+',summary[:match.start()].strip())
        if len(names)!=2:
            continue
        pair={canonical(n) for n in names}
        start=ics_time(event)
        candidates=[g for g in games.values() if {g.home,g.away}==pair and
                    ((g.known and abs(g.start-start)<=timedelta(minutes=90)) or
                     (not g.known and g.start.date()==start.astimezone(ZoneInfo('Europe/London')).date()))]
        if len(candidates)==1:
            found.setdefault(candidates[0].id,set()).add(channel.upper())
    return found


def make_event(g,channels,now,old=None):
    dates=[f'DTSTART:{stamp(g.start)}',f'DTEND:{stamp(g.start+timedelta(hours=2))}'] if g.known else [
        f'DTSTART;VALUE=DATE:{g.start:%Y%m%d}',f'DTEND;VALUE=DATE:{g.start+timedelta(days=1):%Y%m%d}']
    body=[f'UID:pl-espn-{g.id}@sports-us-bein-calendar',*dates,
          'SUMMARY:'+escape(title(g)), 'DESCRIPTION:'+escape(' + '.join(sorted(channels)) if channels else 'CANAL+ (chaîne à confirmer)'),
          'LOCATION:'+escape(g.venue),f'URL:https://www.espn.com/soccer/match/_/gameId/{g.id}',
          'STATUS:CONFIRMED' if g.known else 'STATUS:TENTATIVE','TRANSP:OPAQUE',
          'X-PL-HOME:'+escape(g.home),'X-PL-AWAY:'+escape(g.away),'X-PL-RIGHTS:'+RIGHTS]
    ignored=('DTSTAMP:','LAST-MODIFIED:','SEQUENCE:')
    if old and [x for x in old if not x.startswith(ignored)]==body:
        return old
    sequence=int(prop(old or [],'SEQUENCE','0'))+(1 if old else 0)
    return body+[f'DTSTAMP:{stamp(now)}',f'LAST-MODIFIED:{stamp(now)}',f'SEQUENCE:{sequence}']


def begun(event,now):
    return ics_time(event,'DTEND' if any(x.startswith('DTSTART;VALUE=DATE:') for x in event) else 'DTSTART')<=now


def reconcile(old,games,channels,now):
    previous={}
    for e in old:
        uid=prop(e,'UID')
        if not uid or uid in previous:
            raise ValueError('Historique invalide : UID absent ou doublon')
        previous[uid]=e
    result={uid:e for uid,e in previous.items() if begun(e,now)}
    for g in games.values():
        uid=f'pl-espn-{g.id}@sports-us-bein-calendar'
        # Un report connu vers le futur remplace le même rendez-vous.
        if g.start>now and g.state=='pre':
            result.pop(uid,None)
        if uid in result:
            continue
        if g.status in CANCELLED or g.state=='post':
            continue
        if not {g.home,g.away}&BIG_SIX or not 2025<=g.season<=2027:
            continue
        if g.start+(timedelta(days=1) if not g.known else timedelta())<=now and g.state!='in':
            continue
        result[uid]=make_event(g,channels.get(g.id,set()),now,previous.get(uid))
    # Une disparition de la source n'est pas une annulation explicite.
    for uid,e in previous.items():
        game_id=uid.removeprefix('pl-espn-').split('@')[0]
        if uid not in result and game_id not in games:
            result[uid]=e
            LOG.warning('Match absent de la source, conservé : %s',uid)
    return list(result.values())


def serialize(events):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//sports-us-bein-calendar//Premier League//FR',
           'CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:Premier League — Big Six — CANAL+',
           'REFRESH-INTERVAL;VALUE=DURATION:PT6H','X-PUBLISHED-TTL:PT6H']
    for e in sorted(events,key=lambda x:(ics_time(x),prop(x,'UID'))):
        lines+=['BEGIN:VEVENT',*e,'END:VEVENT']
    return ('\r\n'.join(fold(x) for x in lines+['END:VCALENDAR'])+'\r\n').encode('utf-8')


def run(output,dry_run=False):
    now=datetime.now(UTC)
    season=now.year if now.month>=7 else now.year-1
    if not 2025<=season<=2027:
        raise ValueError('Droits Canal+ à revérifier pour cette saison : fichier conservé')
    cursor=now-timedelta(days=1)
    end=datetime(season+1,6,15,tzinfo=UTC)
    games={}
    while cursor<end:
        stop=min(cursor+timedelta(days=30),end)
        data=fetch(ESPN+'?limit=1000&dates='+cursor.strftime('%Y%m%d')+'-'+stop.strftime('%Y%m%d'))
        games.update(parse_schedule(data))
        cursor=stop
    if not games:
        raise ValueError('Calendrier ESPN vide : fichier conservé')
    channels={}
    try:
        channels=tv_channels(fetch(TV),games)
        LOG.info('%d matchs avec chaîne Canal précisée par TV-Sports',len(channels))
    except Exception as exc:
        LOG.warning('Grille TV indisponible : CANAL+ générique (%s)',exc)
    path=Path(output)
    old=read_ics(path.read_text()) if path.exists() else []
    events=reconcile(old,games,channels,now)
    content=serialize(events)
    content=team_context.enrich_file(content.decode("utf-8"), path, "PL").encode("utf-8")
    read_ics(content.decode())
    if not dry_run:
        atomic_write(path,content)
    LOG.info('%d événements, %d historiques, %d horaires à confirmer',len(events),sum(begun(e,now) for e in events),
             sum(any(x.startswith('DTSTART;VALUE=DATE:') for x in e) for e in events))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='premier_league_canal_calendar.ics')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    try:
        run(args.output,args.dry_run)
    except Exception as exc:
        LOG.error('%s',exc)
        return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
