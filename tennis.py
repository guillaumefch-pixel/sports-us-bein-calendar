"""Grand Chelem : Top 5 ATP/WTA en simples, puis toutes les demies/finales.

Sources ESPN publiques : rankings (classement mondial, jamais curatedRank,
qui est le seed du tableau) et scoreboard/groupings/competitions.
Pas de compte, clé API ou dépendance supplémentaire. Utilitaires ICS partagés
avec premier_league.py. Les matchs déjà commencés sont conservés tels quels.
"""
import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import premier_league as cal

UTC = timezone.utc
BASE = 'https://site.api.espn.com/apis/site/v2/sports/tennis/'
TOURNAMENTS = {
    'australian open': ("Open d'Australie", 'Melbourne Park', 'Melbourne', 'Australia/Melbourne', 'Eurosport', 2031),
    'french open': ('Roland-Garros', 'Stade Roland-Garros', 'Paris', 'Europe/Paris', '', 2027),
    'roland garros': ('Roland-Garros', 'Stade Roland-Garros', 'Paris', 'Europe/Paris', '', 2027),
    'roland-garros': ('Roland-Garros', 'Stade Roland-Garros', 'Paris', 'Europe/Paris', '', 2027),
    'wimbledon': ('Wimbledon', 'All England Lawn Tennis Club', 'Londres', 'Europe/London', 'beIN SPORTS', 2028),
    'us open': ('US Open', 'USTA Billie Jean King National Tennis Center', 'New York', 'America/New_York', 'Eurosport', 2027),
}
ROUNDS = {'Round 1': '1er tour', 'Round 2': '2e tour', 'Round 3': '3e tour',
          'Round 4': '1/8 de finale', 'Quarterfinal': '1/4 de finale',
          'Semifinal': '1/2 finale', 'Final': 'Finale'}
LATE = {'Semifinal', 'Final'}
CANCELLED = {'STATUS_CANCELED', 'STATUS_CANCELLED', 'STATUS_WALKOVER'}


@dataclass
class Match:
    id: str
    tournament_id: str
    tournament: str
    tour: str
    round: str
    start: datetime
    known: bool
    players: tuple
    court: str
    state: str
    status: str
    channels: tuple = ()

    @property
    def uid(self):
        return f'tennis-{self.tour}-{self.tournament_id}-{self.id}@sports-us-bein-calendar'


def rankings(data, tour, now):
    polls = [p for p in data.get('rankings', []) if p.get('type') == tour]
    if len(polls) != 1:
        raise ValueError('Classement mondial '+tour+' absent ou ambigu')
    poll = polls[0]
    updated = cal.instant(poll['update'])
    if updated > now + timedelta(days=1) or now - updated > timedelta(days=21):
        raise ValueError('Classement '+tour+' périmé : '+poll['update'])
    result = {}
    for row in poll['ranks']:
        aid = str(row['athlete']['id'])
        rank = int(row['current'])
        if aid in result or rank <= 0:
            raise ValueError('Classement invalide')
        result[aid] = rank
    if len(result) < 100 or sorted(result.values())[:5] != [1, 2, 3, 4, 5]:
        raise ValueError('Classement tronqué ou Top 5 incomplet')
    return result


def parse_schedule(data, tour):
    if not any(x.get('slug') == tour for x in data.get('leagues', [])) or not isinstance(data.get('events'), list):
        raise ValueError('Calendrier '+tour+' invalide')
    result = {}
    for event in data['events']:
        name = event.get('name', '').lower().strip()
        if name not in TOURNAMENTS or event.get('major') is not True:
            continue
        groups = event.get('groupings')
        if not isinstance(groups, list):
            raise ValueError('Tableaux de Grand Chelem absents')
        slug = 'mens-singles' if tour == 'atp' else 'womens-singles'
        for group in groups:
            if group.get('grouping', {}).get('slug') != slug:
                continue
            if not isinstance(group.get('competitions'), list):
                raise ValueError('Rencontres absentes du tableau')
            for c in group['competitions']:
                if c.get('type', {}).get('slug') != slug:
                    continue
                rnd = c.get('round', {}).get('displayName')
                if rnd not in ROUNDS:  # Exclut aussi "Qualifying Final".
                    continue
                players = tuple((str(p['id']), p.get('athlete', {}).get('displayName', ''))
                                for p in sorted(c.get('competitors', []), key=lambda p: p.get('order', 0)))
                if len(players) != 2 or any(not p[0].isdigit() or int(p[0]) <= 0 or not p[1] or p[1] == 'TBD' for p in players):
                    continue
                start = cal.instant(c['date'])
                known = c.get('timeValid') is True
                if not known:
                    # ESPN utilise le fuseau déclaré par son calendrier pour
                    # les dates fictives à minuit. Ne pas les interpréter en UTC.
                    tz = event.get('calendar', {}).get('timeZone')
                    if not tz:
                        continue
                    day = start.astimezone(ZoneInfo(tz)).date()
                    start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                venue = c.get('venue', {})
                st = c.get('status', {}).get('type', {})
                channels = tuple(sorted(set(b.get('media', {}).get('shortName', '') for b in c.get('geoBroadcasts', [])
                                            if b.get('region', '').lower() == 'fr' and b.get('media', {}).get('shortName'))))
                m = Match(str(c['id']), str(event['id']), name, tour, rnd, start, known, players,
                          venue.get('court', ''), st.get('state', ''), st.get('name', ''), channels)
                if m.uid in result and result[m.uid] != m:
                    raise ValueError('Versions contradictoires du même match')
                result[m.uid] = m
    return result


def selected(m, ranks):
    return m.round in LATE or any(0 < ranks.get(pid, 99999) <= 5 for pid, _ in m.players)


def broadcaster(m):
    if m.channels:
        return ' + '.join(m.channels)
    title, _, _, tz, channel, last_year = TOURNAMENTS[m.tournament]
    if not 2026 <= m.start.year <= last_year:
        return 'Diffusion à confirmer'
    if title != 'Roland-Garros':
        return channel
    # Droits français 2024–2027 : toutes les demies/finales codiffusées,
    # sessions de soirée sur le Chatrier exclusives à Prime Video.
    if m.round in LATE:
        return 'France Télévisions / france.tv + Prime Video'
    if not m.known:
        return 'France Télévisions / france.tv ou Prime Video (selon séance)'
    court = m.court.casefold()
    if 'chatrier' in court and m.start.astimezone(ZoneInfo(tz)).hour >= 20:
        return 'Prime Video'
    if m.start.astimezone(ZoneInfo(tz)).hour < 20 or (court and 'chatrier' not in court):
        return 'France Télévisions / france.tv'
    return 'France Télévisions / france.tv ou Prime Video (selon séance)'


def make_event(m, ranks, now, previous=None):
    tournament, site, city, _, _, _ = TOURNAMENTS[m.tournament]
    # Convention demandée : NC lorsque le rang est absent du flux disponible.
    names = [f'{name} [#{ranks[pid]}]' if pid in ranks else f'{name} [NC]' for pid, name in m.players]
    title = f'🎾 {tournament} — {m.tour.upper()} — {ROUNDS[m.round]} : '+ ' - '.join(names)
    if m.known:
        dates = ['DTSTART:'+cal.stamp(m.start), 'DTEND:'+cal.stamp(m.start+timedelta(hours=3 if m.tour == 'atp' else 2))]
    else:
        dates = [f'DTSTART;VALUE=DATE:{m.start:%Y%m%d}', f'DTEND;VALUE=DATE:{m.start+timedelta(days=1):%Y%m%d}']
        title += ' — horaire à confirmer'
    body = ['UID:'+m.uid, *dates, 'SUMMARY:'+cal.escape(title),
            'DESCRIPTION:'+cal.escape(broadcaster(m)), 'LOCATION:'+cal.escape((m.court or site)+', '+city),
            'URL:https://www.espn.com/tennis/scoreboard/_/date/'+m.start.strftime('%Y%m%d'),
            'STATUS:'+('CONFIRMED' if m.known else 'TENTATIVE'), 'TRANSP:OPAQUE',
            'X-TENNIS-TOUR:'+m.tour, 'X-TENNIS-PLAYERS:'+','.join(pid for pid, _ in m.players),
            'X-TENNIS-ROUND:'+m.round]
    ignore = ('DTSTAMP:', 'LAST-MODIFIED:', 'SEQUENCE:')
    if previous and [x for x in previous if not x.startswith(ignore)] == body:
        return previous
    seq = int(cal.prop(previous or [], 'SEQUENCE', '0')) + bool(previous)
    return body+['DTSTAMP:'+cal.stamp(now), 'LAST-MODIFIED:'+cal.stamp(now), 'SEQUENCE:'+str(seq)]


def reconcile(old, games, ranks, now):
    previous = {cal.prop(e, 'UID'): e for e in old}
    if len(previous) != len(old):
        raise ValueError('UID dupliqué dans le calendrier existant')
    result = {}
    for uid, e in previous.items():
        tour = cal.prop(e, 'X-TENNIS-TOUR')
        if cal.begun(e, now) or tour not in ranks:
            result[uid] = e
        elif uid not in games:
            # Une grille glissante ne prouve pas l'annulation d'un match.
            # Le nouveau Top 5 permet toutefois de retirer les sortants.
            if cal.prop(e, 'X-TENNIS-ROUND') in LATE or any(ranks[tour].get(p, 99999) <= 5 for p in cal.prop(e, 'X-TENNIS-PLAYERS').split(',')):
                result[uid] = e
    for uid, m in games.items():
        if uid in result and cal.begun(result[uid], now):
            continue
        if m.tour not in ranks:
            continue
        if m.status in CANCELLED or m.state == 'post' or (m.known and m.start <= now) or (not m.known and m.start.date() < now.date()):
            continue
        if selected(m, ranks[m.tour]):
            result[uid] = make_event(m, ranks[m.tour], now, previous.get(uid))
    return sorted(result.values(), key=lambda e: (cal.ics_time(e), cal.prop(e, 'UID')))


def serialize(events):
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//sports-us-bein-calendar//Tennis//FR',
             'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:Tennis — Grand Chelem — Top 5 ATP + WTA',
             'REFRESH-INTERVAL;VALUE=DURATION:PT2H', 'X-PUBLISHED-TTL:PT2H']
    for event in events:
        lines += ['BEGIN:VEVENT', *event, 'END:VEVENT']
    return ('\r\n'.join(cal.fold(x) for x in lines+['END:VCALENDAR'])+'\r\n').encode('utf-8')


def run(output):
    now = datetime.now(UTC)
    path = Path(output)
    old = cal.read_ics(path.read_text()) if path.exists() else []
    games, ranks = {}, {}
    successful = 0
    for tour in ('atp', 'wta'):
        try:
            table = rankings(json.loads(cal.fetch(BASE+tour+'/rankings')), tour, now)
            # Chaque réponse expose tout le tableau des tournois rencontrés.
            # Les dates successives couvrent aussi un tournoi débutant bientôt.
            snapshots = {}
            for days in (0, 7, 14):
                date = (now+timedelta(days=days)).strftime('%Y%m%d')
                snapshots.update(parse_schedule(json.loads(cal.fetch(BASE+tour+'/scoreboard?dates='+date)), tour))
            games.update(snapshots)
            ranks[tour] = table
            successful += 1
            logging.info('%s : Top 5 %s ; %s matchs de Grand Chelem lus', tour.upper(),
                         {p:r for p,r in table.items() if r <= 5}, len(snapshots))
        except Exception as exc:
            logging.warning('%s indisponible : %s ; événements existants conservés', tour.upper(), exc)
    if not successful:
        raise RuntimeError('Sources tennis indisponibles : calendrier inchangé')
    events = reconcile(old, games, ranks, now)
    cal.atomic_write(path, serialize(events))
    logging.info('%s : %s événements. Un calendrier vide hors Grand Chelem est normal.', path, len(events))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='tennis_calendar.ics')
    args = parser.parse_args()
    run(args.output)
