"""Classements des titres ICS. Aucune sélection de match ni de diffuseur ici."""
import json
import logging
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

UTC = timezone.utc
ESPN = 'https://site.api.espn.com/apis/v2/sports/'
PATHS = {'PL': 'soccer/eng.1', 'L1': 'soccer/fra.1',
         'UCL': 'soccer/uefa.champions', 'NFL': 'football/nfl'}
LABEL = re.compile(r' \[(?:#\d+|\d+W/\d+L(?:/\d+T)?|\d+(?:[.,]\d+)?%)\]')
ALIASES = {'psg': 'paris saint germain', 'paris sg': 'paris saint germain',
           'paris': 'paris saint germain', 'tottenham': 'tottenham hotspur',
           'man united': 'manchester united', 'man city': 'manchester city',
           'fc barcelone': 'barcelona', 'barcelone': 'barcelona',
           'le havre': 'le havre ac', 'om': 'marseille', 'ol': 'lyon', 'as monaco': 'monaco',
           'saint etienne': 'st etienne', 'bayern munich': 'bayern munich',
           'inter milan': 'internazionale', 'inter': 'internazionale',
           'sporting portugal': 'sporting cp', 'atletico madrid': 'atletico madrid',
           'athletics': 'oakland athletics', 'sacramento athletics': 'oakland athletics'}


def norm(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.lower())
                    if not unicodedata.combining(c))
    value = ' '.join(re.sub(r'[^a-z0-9]+', ' ', value).split())
    return ALIASES.get(value, value)


def strip_labels(value):
    return LABEL.sub('', value)


def fetch(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code != 403:
            raise
        # Même secours que le script Premier League, sans cookie ni compte.
        result = subprocess.run(['curl', '--fail', '--silent', '--show-error',
                                 '--location', '--max-time', '25', url],
                                check=True, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)


def tables(node):
    if isinstance(node, dict):
        if node.get('name') == 'overall' and isinstance(node.get('entries'), list):
            yield node
        for key in ('children', 'standings'):
            yield from tables(node.get(key))
    elif isinstance(node, list):
        for child in node:
            yield from tables(child)


def indexed(rows):
    result, owners, ambiguous = {}, {}, set()
    for identity, names, label in rows:
        for name in names:
            key = norm(name)
            if not key:
                continue
            if key in owners and owners[key] != identity:
                ambiguous.add(key)
            owners[key] = identity
            result[key] = label
    return {k: v for k, v in result.items() if k not in ambiguous}


def espn_labels(data, kind, season):
    if int(data.get('season', {}).get('year', 0)) != season:
        raise ValueError('Classement ESPN d’une autre saison')
    groups = list(tables(data))
    # La LDC demandée est le classement commun de la phase de ligue.
    expected = {'PL': 20, 'L1': 18, 'UCL': 36, 'NFL': 32}[kind]
    entries = [e for table in groups for e in table['entries']]
    if len({e['team']['id'] for e in entries}) != expected or len(entries) != expected:
        raise ValueError('Classement incomplet ou groupes ambigus')
    rows = []
    for entry in entries:
        team = entry['team']
        stats = {s['name']: s.get('value') for s in entry['stats']}
        if kind == 'NFL':
            w, l, t = (int(stats[k]) for k in ('wins', 'losses', 'ties'))
            label = f'{w}W/{l}L' + (f'/{t}T' if t else '')
        else:
            if not stats.get('gamesPlayed'):
                continue  # Aucun classement artificiel avant le premier match.
            rank = int(stats['rank'])
            if not 1 <= rank <= expected:
                raise ValueError('Rang invalide')
            label = f'#{rank}'
        names = [team[k] for k in ('displayName', 'shortDisplayName', 'name', 'abbreviation') if team.get(k)]
        rows.append((team['id'], names, label))
    return indexed(rows)


def mlb_labels(data, teams, season):
    names = {t['id']: [t.get(k, '') for k in ('name', 'teamName', 'clubName', 'abbreviation')]
             for t in teams['teams']}
    rows = []
    for group in data['records']:
        if group.get('standingsType') != 'regularSeason':
            continue
        for entry in group['teamRecords']:
            if int(entry['season']) != season:
                raise ValueError('Bilan MLB d’une autre saison')
            record = entry['leagueRecord']
            w, l = int(record['wins']), int(record['losses'])
            identity = entry['team']['id']
            if identity not in names:
                raise ValueError('Équipe MLB inconnue')
            if w+l:
                # Pourcentage de victoires de saison régulière, arrondi à l’unité.
                rows.append((identity, names[identity], f'{int(100*w/(w+l)+0.5)}%'))
    if not data['records']:
        raise ValueError('Classement MLB vide')
    return indexed(rows)


@lru_cache(maxsize=8)
def standings(kind, season):
    try:
        if kind == 'MLB':
            root = 'https://statsapi.mlb.com/api/v1/'
            data = fetch(root+f'standings?leagueId=103,104&standingsTypes=regularSeason&season={season}')
            teams = fetch(root+f'teams?sportId=1&season={season}')
            result = mlb_labels(data, teams, season)
        else:
            result = espn_labels(fetch(ESPN+PATHS[kind]+'/standings'), kind, season)
        logging.info('Classement %s : %d noms reconnus', kind, len(result))
        return result
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        logging.warning('Classement %s indisponible : %s. Dernières indications conservées.', kind, exc)
        return None


def unfold(text):
    return re.sub(r'\r?\n[ \t]', '', text).splitlines()


def prop(lines, key):
    return next((x.split(':', 1)[1] for x in lines if x.startswith(key+':')), '')


def blocks(text):
    lines = unfold(text)
    result, event = [], None
    for line in lines:
        if line == 'BEGIN:VEVENT':
            event = []
        if event is not None:
            event.append(line)
            if line == 'END:VEVENT':
                result.append(event)
                event = None
    return result


def fold(line):
    out, current = [], ''
    for char in line:
        if len((current+char).encode('utf-8')) > 75:
            out.append(current)
            current = ' '
        current += char
    return out+[current]


def decorate(summary, mapping):
    clean = strip_labels(summary)
    prefix, sep, body = clean.partition(' : ')
    if not sep:
        return clean
    match, suffix_sep, suffix = body.partition(' — ')
    teams = match.split(' - ')
    if len(teams) != 2:
        return clean
    decorated = [name + (f' [{mapping[norm(name)]}]' if norm(name) in mapping else '') for name in teams]
    return prefix+sep+' - '.join(decorated)+suffix_sep+suffix


def enrich_calendar(text, previous, kind, now=None, provider=standings):
    now = now or datetime.now(UTC)
    old = {prop(e, 'UID'): e for e in blocks(previous)}
    lines = unfold(text)
    result, event = [], None
    for line in lines:
        if line == 'BEGIN:VEVENT':
            event = []
        if event is None:
            result.append(line)
            continue
        event.append(line)
        if line != 'END:VEVENT':
            continue
        uid = prop(event, 'UID')
        before = old.get(uid)
        start = prop(event, 'DTSTART')
        date_start = next((x.split(':',1)[1] for x in event if x.startswith('DTSTART;VALUE=DATE:')), '')
        begun = bool(start and start <= now.strftime('%Y%m%dT%H%M%SZ')) or bool(date_start and date_start < now.strftime('%Y%m%d'))
        if begun:
            # Ne jamais réécrire les rangs/bilans des matchs déjà commencés.
            result.extend(before if before and prop(before, 'DTSTART') == start and next((x for x in before if x.startswith('DTSTART')), '') == next((x for x in event if x.startswith('DTSTART')), '') else event)
            event = None
            continue
        summary = prop(event, 'SUMMARY')
        selected = kind
        if kind == 'PSG':
            competition = norm(summary.split(' : ', 1)[0])
            selected = 'L1' if 'ligue 1' in competition else ('UCL' if ('champions' in competition or 'ldc' in competition) else None)
        if selected:
            season = now.year - int(now.month < (7 if selected in ('PL','L1','UCL') else 3 if selected == 'NFL' else 1))
            mapping = provider(selected, season)
            if mapping is not None:
                summary = decorate(summary, mapping)
            elif before and strip_labels(prop(before,'SUMMARY')) == strip_labels(summary):
                summary = prop(before, 'SUMMARY')
        event = ['SUMMARY:'+summary if x.startswith('SUMMARY:') else x for x in event]
        # Comparer le résultat final au fichier publié : pas de changement fictif
        # lorsque le générateur amont reconstruit un titre sans annotation.
        ignored = ('DTSTAMP:', 'LAST-MODIFIED:', 'SEQUENCE:')
        body = lambda e: [x for x in e if not x.startswith(ignored)]
        changed = before is not None and body(event) != body(before)
        stamp = now.strftime('%Y%m%dT%H%M%SZ')
        sequence = int(prop(before or [], 'SEQUENCE') or 0) + int(changed)
        dtstamp = stamp if changed else prop(before or event, 'DTSTAMP') or stamp
        event = [x for x in event if not x.startswith(ignored)]
        event[-1:-1] = ['DTSTAMP:'+dtstamp, 'LAST-MODIFIED:'+dtstamp, f'SEQUENCE:{sequence}']
        result.extend(event)
        event = None
    return '\r\n'.join(part for line in result for part in fold(line))+'\r\n'


def enrich_file(text, path, kind):
    path = Path(path)
    previous = path.read_text(encoding='utf-8') if path.exists() else ''
    return enrich_calendar(text, previous, kind)
