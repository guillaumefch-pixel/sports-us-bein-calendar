#!/usr/bin/env python3
"""Liga Disney+, Bayern beIN, Ligue des champions hors PSG. Python 3.11+."""
from __future__ import annotations
import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import premier_league as cal
import team_context as context
from calendar_locations import location,norm,decode

UTC=timezone.utc
PARIS=ZoneInfo('Europe/Paris')
LOG=logging.getLogger('football-europe')
LIGA_RIGHTS='https://www.laliga.com/noticias/disney-y-dazn-nuevos-hogares-de-laliga-ea-sports-en-francia'
BUNDES_RIGHTS='https://beinregie.beinsports.com/bein-sports-bundesliga-renouvellent-accord-exclusif/'
LEAGUES={'esp.1':'La Liga','ger.1':'Bundesliga','uefa.champions':'Ligue des champions'}
CLUBS={'esp.1':{'83','86','1068'},'ger.1':{'132'}}  # Barça, Real, Atlético ; Bayern.
PSG='160'
NAMES={'83':'FC Barcelone','86':'Real Madrid','1068':'Atlético de Madrid','132':'Bayern Munich'}
RIVALRIES={frozenset(('83','86')):(3,'El Clásico'),frozenset(('86','1068')):(3,'Derby de Madrid'),
           frozenset(('83','1068')):(2,''),frozenset(('132','124')):(3,'Der Klassiker'),
           frozenset(('132','11420')):(2,''),frozenset(('132','131')):(2,'')}
CANCELLED={'STATUS_CANCELED','STATUS_CANCELLED','STATUS_POSTPONED','STATUS_SUSPENDED'}

@dataclass
class Game:
    id:str
    league:str
    start:datetime
    known:bool
    home_id:str
    away_id:str
    home:str
    away:str
    raw_home:str
    raw_away:str
    stadium:str
    city:str
    stage:str
    status:str
    state:str
    season:int
    channel:str=''


def parse_schedule(data,league,season):
    if not isinstance(data.get('events'),list) or not any(x.get('slug')==league for x in data.get('leagues',[])):
        raise ValueError('Calendrier de compétition invalide')
    result={}
    for e in data['events']:
        if int(e.get('season',{}).get('year',0))!=season:continue
        comp=e['competitions'][0]
        teams={x['homeAway']:x['team'] for x in comp.get('competitors',[])}
        if set(teams)!={'home','away'}:continue
        h,a=teams['home'],teams['away']
        if not h.get('id') or not a.get('id'):continue
        if any(norm(t.get('displayName','')) in ('','tbd','to be determined') for t in (h,a)):continue
        status=comp.get('status',e.get('status',{})).get('type',{})
        if comp.get('dateValid') is False and status.get('name') not in CANCELLED:continue
        start=cal.instant(comp['date'])
        known=comp.get('timeValid') is True
        if not known:
            day=start.astimezone(PARIS).date()
            start=datetime(day.year,day.month,day.day,tzinfo=UTC)
        venue=comp.get('venue') or {}
        channel=''
        for b in comp.get('geoBroadcasts',[]):
            name=b.get('media',{}).get('shortName','')
            if b.get('region','').lower()=='fr' and name.lower().startswith('bein sports'):
                channel=name
        def display(t):return NAMES.get(str(t['id']), 'Côme' if t.get('displayName')=='Como' else t['displayName'])
        game=Game(str(e['id']),league,start,known,str(h['id']),str(a['id']),display(h),display(a),
                  h['displayName'],a['displayName'],venue.get('fullName',''),venue.get('address',{}).get('city',''),
                  e.get('season',{}).get('slug',''),status.get('name',''),status.get('state',''),season,channel)
        if game.id in result and result[game.id]!=game:raise ValueError('Match contradictoire')
        result[game.id]=game
    if not result:raise ValueError('Calendrier vide : événements antérieurs conservés')
    return result


def selected(g):
    if g.league in CLUBS:return bool({g.home_id,g.away_id}&CLUBS[g.league])
    return PSG not in (g.home_id,g.away_id) and stage_name(g.stage) is not None


def stage_name(slug):
    key=norm(slug)
    if key=='league phase':return 'Phase de ligue'
    if 'qualif' in key or 'preliminary' in key:return None
    if 'knockout' in key and ('playoff' in key or 'play off' in key):return 'Barrages'
    if key in ('playoffs','playoff round','play offs'):return 'Barrages'
    if 'round of 16' in key or 'last 16' in key:return 'Huitième de finale'
    if 'quarter' in key:return 'Quart de finale'
    if 'semi' in key:return 'Demi-finale'
    if key in ('final','finals'):return 'Finale'
    return None


def labels(g,ranks):
    def label(name,raw):
        rank=ranks.get(context.norm(raw))
        return name+' '+rank if rank else name
    return label(g.home,g.raw_home),label(g.away,g.raw_away)


def finalize(body,previous,now):
    ignored=('DTSTAMP:','LAST-MODIFIED:','SEQUENCE:')
    if previous and [x for x in previous if not x.startswith(ignored)]==body:return previous
    seq=int(cal.prop(previous or [],'SEQUENCE','0'))+bool(previous)
    return body+['DTSTAMP:'+cal.stamp(now),'LAST-MODIFIED:'+cal.stamp(now),'SEQUENCE:'+str(seq)]


def individual(g,ranks,now,previous=None):
    home,away=labels(g,ranks)
    level,name=RIVALRIES.get(frozenset((g.home_id,g.away_id)),(0,''))
    prefix=LEAGUES[g.league]
    if g.league=='uefa.champions':prefix+=' — '+stage_name(g.stage)
    title=('🔥'*level+' ' if level else '')+f'⚽ {prefix} : {home} - {away}'+(' — '+name if name else '')
    if not g.known:title+=' — horaire à confirmer'
    channel='Disney+' if g.league=='esp.1' else (g.channel or 'beIN SPORTS (chaîne à confirmer)') if g.league=='ger.1' else ''
    dates=['DTSTART:'+cal.stamp(g.start),'DTEND:'+cal.stamp(g.start+timedelta(hours=2))] if g.known else [
        f'DTSTART;VALUE=DATE:{g.start:%Y%m%d}',f'DTEND;VALUE=DATE:{g.start+timedelta(days=1):%Y%m%d}']
    body=['UID:europe-'+g.league+'-'+g.id+'@sports-us-bein-calendar',*dates,
          'SUMMARY:'+cal.escape(title),'DESCRIPTION:'+cal.escape(channel),
          'LOCATION:'+cal.escape(location(g.stadium,g.city,g.home)),
          'URL:https://www.espn.com/soccer/match/_/gameId/'+g.id,
          'STATUS:'+('CONFIRMED' if g.known else 'TENTATIVE'),'TRANSP:OPAQUE','X-EU-LEAGUE:'+g.league,
          'X-EU-RANKS:'+cal.escape(json.dumps({k:ranks[k] for k in (context.norm(g.raw_home),context.norm(g.raw_away)) if k in ranks},ensure_ascii=False))]
    if g.league in ('esp.1','ger.1'):
        body.append('X-EU-RIGHTS:'+(LIGA_RIGHTS if g.league=='esp.1' else BUNDES_RIGHTS))
    return finalize(body,previous,now)


def grouped(games,ranks,now,previous=None):
    games=sorted(games,key=lambda g:(g.home,g.away,g.id))
    start=games[0].start
    notes=[]
    for g in games:
        home,away=labels(g,ranks)
        notes.append(f'{home} - {away}, '+location(g.stadium,g.city,g.home))
    uid='ucl-slot-'+cal.stamp(start)+'@sports-us-bein-calendar'
    body=['UID:'+uid,'DTSTART:'+cal.stamp(start),'DTEND:'+cal.stamp(start+timedelta(hours=2)),
          'SUMMARY:Ligue des champions','DESCRIPTION:'+cal.escape('\n'.join(notes)),
          'STATUS:CONFIRMED','TRANSP:OPAQUE','X-EU-LEAGUE:uefa.champions','X-EU-GROUPED:TRUE',
          'X-EU-MATCHES:'+','.join(g.id for g in games),
          'X-EU-RANKS:'+cal.escape(json.dumps({context.norm(raw):ranks[context.norm(raw)] for g in games for raw in (g.raw_home,g.raw_away) if context.norm(raw) in ranks},ensure_ascii=False))]
    return finalize(body,previous,now)


def reconcile(old,games,ranks,now,successful):
    previous={cal.prop(e,'UID'):e for e in old}
    if len(previous)!=len(old):raise ValueError('UID dupliqué dans le calendrier')
    output={uid:e for uid,e in previous.items() if cal.begun(e,now) or cal.prop(e,'X-EU-LEAGUE') not in successful}
    slots={}
    for g in games.values():
        if g.league not in successful or not selected(g) or g.status in CANCELLED or g.state=='post':continue
        if g.start+(timedelta(days=1) if not g.known else timedelta())<=now:continue
        if g.league=='uefa.champions' and norm(g.stage)=='league phase':
            if g.known:slots.setdefault(g.start,[]).append(g)
            continue
        uid='europe-'+g.league+'-'+g.id+'@sports-us-bein-calendar'
        output[uid]=individual(g,ranks.get(g.league,{}) or {},now,previous.get(uid))
    for start,group in slots.items():
        uid='ucl-slot-'+cal.stamp(start)+'@sports-us-bein-calendar'
        if uid not in output:output[uid]=grouped(group,ranks.get('uefa.champions',{}) or {},now,previous.get(uid))
    return sorted(output.values(),key=lambda e:(cal.ics_time(e),cal.prop(e,'UID')))


def serialize(events):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//sports-us-bein-calendar//Football Europe//FR',
           'CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:Football Europe — Liga + Bayern + LDC',
           'REFRESH-INTERVAL;VALUE=DURATION:PT6H','X-PUBLISHED-TTL:PT6H']
    for event in events:lines+=['BEGIN:VEVENT',*event,'END:VEVENT']
    return ('\r\n'.join(cal.fold(x) for x in lines+['END:VCALENDAR'])+'\r\n').encode('utf-8')


def run(output,dry_run=False):
    now=datetime.now(UTC);season=now.year if now.month>=7 else now.year-1
    if not 2026<=season<=2028:raise ValueError('Droits TV à revérifier : calendrier conservé')
    path=Path(output);old=cal.read_ics(path.read_text()) if path.exists() else []
    cached={}
    for event in old:
        league=cal.prop(event,'X-EU-LEAGUE')
        cached.setdefault(league,{}).update(json.loads(decode(cal.prop(event,'X-EU-RANKS','{}'))))
    games={};successful=set();ranks={}
    for league in LEAGUES:
        try:
            data=json.loads(cal.fetch('https://site.api.espn.com/apis/site/v2/sports/soccer/'+league+
                f'/scoreboard?limit=1000&dates={season}0801-{season+1}0701'))
            games.update(parse_schedule(data,league,season));successful.add(league)
            LOG.info('%s : calendrier récupéré',LEAGUES[league])
        except Exception as exc:LOG.warning('%s indisponible : %s',league,exc)
        ranks[league]=context.standings({'esp.1':'LIGA','ger.1':'BUNDES','uefa.champions':'UCL'}[league],season)
        if ranks[league] is None:ranks[league]=cached.get(league,{})
    if not successful:raise ValueError('Toutes les sources indisponibles : fichier conservé')
    events=reconcile(old,games,ranks,now,successful)
    data=serialize(events);cal.read_ics(data.decode())
    if not dry_run:cal.atomic_write(path,data)
    LOG.info('%d événements écrits dans %s',len(events),output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='europe_football_calendar.ics')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args();logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    try:run(args.output,args.dry_run)
    except Exception as exc:LOG.error('%s',exc);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
