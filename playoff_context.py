"""Seeds figés des tableaux de playoffs ; aucun ajout de diffusion ou de match."""
import json
import logging
import re
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from functools import lru_cache
from pathlib import Path
import team_context as core

UTC=timezone.utc
PATHS={'NFL':'football/nfl','MLB':'baseball/mlb','NCAA':'football/college-football'}


def decode(s):
    return re.sub(r'\\([nN,;\\])',lambda m:'\n' if m[1].lower()=='n' else m[1],s)


def escape(s):return s.replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')


def stage(kind,notes):
    text=' '.join(n.get('headline','') for n in notes)
    low=text.lower()
    if kind=='NCAA':return 'CFP' if 'college football playoff' in low else ''
    if kind=='NFL':
        if 'wild card' in low:return 'Wild Card'
        if 'divisional' in low:return 'Divisional Round'
        if 'championship' in low and ('afc' in low or 'nfc' in low):return 'Conference Championship'
        if 'super bowl' in low:return 'Super Bowl'
    if kind=='MLB':
        for token,label in [('ALWC','Wild Card Series'),('NLWC','Wild Card Series'),('ALDS','Division Series'),
                            ('NLDS','Division Series'),('ALCS','Championship Series'),('NLCS','Championship Series')]:
            if token in text:return label
        if 'world series' in low:return 'World Series'
    return ''


def games(data,kind,season):
    if not isinstance(data.get('events'),list):raise ValueError('Calendrier de playoffs invalide')
    result=[]
    for event in data['events']:
        if event.get('season',{}).get('year')!=season or event.get('season',{}).get('type')!=3:continue
        comp=event['competitions'][0];round_name=stage(kind,comp.get('notes',[]))
        if not round_name:continue  # Exclut notamment les bowls hors CFP et le Pro Bowl.
        teams={x['homeAway']:x for x in comp.get('competitors',[]) if x.get('homeAway') in ('home','away')}
        if set(teams)!={'home','away'}:continue
        if comp.get('status',event.get('status',{})).get('type',{}).get('name') in ('STATUS_CANCELED','STATUS_CANCELLED','STATUS_POSTPONED'):continue
        start=datetime.fromisoformat(comp['date'].replace('Z','+00:00'))
        if start.tzinfo is None:raise ValueError('Date sans fuseau')
        result.append({'id':str(event['id']),'start':start,'round':round_name,'teams':teams,
                       'completed':comp.get('status',event.get('status',{})).get('type',{}).get('completed') is True})
    unique={}
    for row in result:
        if row['id'] in unique and unique[row['id']]!=row:
            raise ValueError('Match de playoffs contradictoire')
        unique[row['id']]=row
    return list(unique.values())


def cfp_seeds(rows):
    # curatedRank n’est utilisé que dans les matchs identifiés explicitement CFP,
    # et uniquement si l’ensemble du tableau fournit les 12 seeds distincts.
    labels={}
    for game in rows:
        for competitor in game['teams'].values():
            team=competitor['team'];rank=competitor.get('curatedRank',{}).get('current')
            if not isinstance(rank,int) or not 1<=rank<=12:continue
            key=core.norm(team.get('location',''))
            if key in labels and labels[key]!=rank:raise ValueError('Seeds CFP contradictoires')
            labels[key]=rank
    if len(labels)!=12 or set(labels.values())!=set(range(1,13)):
        raise ValueError('Tableau CFP complet non confirmé')
    return {k:f'CFP #{v}' for k,v in labels.items()}


def nfl_seeds(data,season,started=False):
    if int(data.get('season',{}).get('year',0))!=season:raise ValueError('Mauvaise saison NFL')
    result={};count=0
    for group in data.get('children',[]):
        name=group.get('abbreviation') or {'American Football Conference':'AFC','National Football Conference':'NFC'}.get(group.get('name'))
        if name not in ('AFC','NFC'):continue
        seeds=[]
        for table in core.tables(group):
            for entry in table['entries']:
                count+=1;stats=entry['stats']
                overall=next((x.get('displayValue','') for x in stats if x['name']=='overall'),'')
                values=re.fullmatch(r'(\d+)-(\d+)(?:-(\d+))?',overall)
                if not started and (not values or sum(int(x or 0) for x in values.groups())<17):
                    raise ValueError('Saison régulière NFL encore en cours')
                rank=next((x.get('value') for x in stats if x['name']=='playoffSeed'),None)
                if rank is None or int(rank)!=rank or not 1<=rank<=7:continue
                rank=int(rank);seeds.append(rank)
                result[core.norm(entry['team']['displayName'])]=f'{name} #{rank}'
        if sorted(seeds)!=list(range(1,8)):raise ValueError('Tableau NFL incomplet')
    if count!=32 or len(result)!=14:raise ValueError('Tableau NFL incomplet')
    return result


def mlb_seeds(data,teams,season,started=False):
    names={t['id']:t['name'] for t in teams['teams']};leagues=defaultdict(list)
    for group in data['records']:
        if group.get('standingsType')!='regularSeason':continue
        for entry in group['teamRecords']:
            if int(entry['season'])!=season:raise ValueError('Mauvaise saison MLB')
            if not started and entry.get('gamesPlayed',0)<162:raise ValueError('Saison régulière MLB encore en cours')
            leagues[group['league']['id']].append(entry)
    result={}
    for league,entries in leagues.items():
        if league not in (103,104) or len(entries)!=15:raise ValueError('Classement MLB incomplet')
        champions=sorted([t for t in entries if t.get('divisionChamp') is True],key=lambda t:int(t['leagueRank']))
        wildcards=sorted([t for t in entries if not t.get('divisionChamp') and t.get('clinched') is True],key=lambda t:int(t['wildCardRank']))
        if len(champions)!=3 or len(wildcards)!=3:raise ValueError('Qualifications MLB incomplètes')
        if len({t['leagueRank'] for t in champions})!=3 or [int(t['wildCardRank']) for t in wildcards]!=[1,2,3]:
            raise ValueError('Départage MLB non confirmé')
        for seed,team in enumerate(champions+wildcards,1):
            result[core.norm(names[team['team']['id']])]=f'{"AL" if league==103 else "NL"} #{seed}'
    if len(result)!=12:raise ValueError('Tableau MLB incomplet')
    return result


@lru_cache(maxsize=8)
def load(kind,season):
    begin=f'{season+1}0101' if kind=='NFL' else f'{season}0901' if kind=='MLB' else f'{season}1201'
    end=f'{season}1130' if kind=='MLB' else f'{season+1}0228'
    try:
        data=core.fetch('https://site.api.espn.com/apis/site/v2/sports/'+PATHS[kind]+f'/scoreboard?limit=1000&dates={begin}-{end}'+('&groups=80' if kind=='NCAA' else ''))
        rows=games(data,kind,season)
    except Exception as exc:
        logging.warning('Calendrier playoffs %s indisponible : %s',kind,exc);return [],{}
    if not rows:return [],{}
    started=datetime.now(UTC)>=min(g['start'] for g in rows)
    try:
        if kind=='NCAA':labels=cfp_seeds(rows)
        elif kind=='NFL':labels=nfl_seeds(core.fetch('https://site.api.espn.com/apis/v2/sports/football/nfl/standings?season='+str(season)),season,started)
        else:
            root='https://statsapi.mlb.com/api/v1/'
            labels=mlb_seeds(core.fetch(root+f'standings?leagueId=103,104&standingsTypes=regularSeason&season={season}'),
                             core.fetch(root+f'teams?sportId=1&season={season}'),season,started)
        logging.info('Seeds %s : %d équipes confirmées',kind,len(labels))
    except Exception as exc:
        logging.warning('Seeds %s non confirmés : %s',kind,exc);labels={}
    return rows,labels


def team_key(competitor,kind):
    return core.norm(competitor['team'].get('location','') if kind=='NCAA' else competitor['team']['displayName'])


def series_note(game,rows):
    pair={team_key(t,'MLB') for t in game['teams'].values()};wins={k:0 for k in pair}
    for played in rows:
        if not played['completed'] or played['round']!=game['round']:continue
        if {team_key(t,'MLB') for t in played['teams'].values()}!=pair:continue
        winners=[t for t in played['teams'].values() if t.get('winner') is True]
        if len(winners)==1:wins[team_key(winners[0],'MLB')]+=1
    if not sum(wins.values()):return ''
    home,away=game['teams']['home'],game['teams']['away']
    return f"Série : {home['team']['displayName']} {wins[team_key(home,'MLB')]}–{wins[team_key(away,'MLB')]} {away['team']['displayName']}"


def enrich(text,path,kind,provider=load,now=None):
    now=now or datetime.now(UTC)
    previous=Path(path).read_text() if Path(path).exists() else ''
    old={core.prop(e,'UID'):e for e in core.blocks(previous)}
    cache=defaultdict(dict)
    for event in old.values():
        season=core.prop(event,'X-POST-SEASON')
        if season:cache[int(season)].update(json.loads(decode(core.prop(event,'X-POST-SEEDS') or '{}')))
    output=[];event=None
    for line in core.unfold(text):
        if line=='BEGIN:VEVENT':event=[]
        if event is None:output.append(line);continue
        event.append(line)
        if line!='END:VEVENT':continue
        uid=core.prop(event,'UID');before=old.get(uid);start=core.prop(event,'DTSTART')
        if not start or start<=now.strftime('%Y%m%dT%H%M%SZ'):
            output.extend(event);event=None;continue
        date=datetime.strptime(start,'%Y%m%dT%H%M%SZ').replace(tzinfo=UTC)
        if kind=='NCAA' and not core.prop(event,'X-CFB-STAGE').startswith('CFP'):
            output.extend(event);event=None;continue
        if kind=='NFL' and date.month not in (1,2) or kind=='MLB' and date.month not in (9,10,11):
            output.extend(event);event=None;continue
        season=date.year-(1 if kind in ('NFL','NCAA') and date.month<=2 else 0)
        rows,labels=provider(kind,season)
        summary=core.strip_labels(decode(core.prop(event,'SUMMARY')))
        if kind=='NCAA':
            summary=re.sub(r' (?:#\d+|\(NC\)|NC)(?= - | — |$)','',summary)
            event=['SUMMARY:'+escape(summary) if x.startswith('SUMMARY:') else x for x in event]
        pair={core.norm(x) for x in summary.split(' : ',1)[-1].split(' — ',1)[0].split(' - ')}
        matches=[g for g in rows if (kind=='NCAA' and uid==f"ncaa-espn-{g['id']}@sports-calendar") or
                 (kind!='NCAA' and abs(g['start']-date)<=timedelta(hours=12) and {team_key(t,kind) for t in g['teams'].values()}==pair)]
        game=matches[0] if len(matches)==1 else None
        if game is None:
            if kind=='MLB' and core.prop(event,'X-MLB-POSTSEASON')=='TRUE':
                summary=summary.replace('MLB :','MLB Playoffs :',1)
                event=['SUMMARY:'+escape(summary) if x.startswith('SUMMARY:') else x for x in event]
            if before and core.prop(before,'X-POST-SEASON')==str(season):
                # Panne : restaurer uniquement la présentation des playoffs déjà identifiés.
                for key in ('SUMMARY','DESCRIPTION','X-POST-SEASON','X-POST-SEEDS'):
                    value=core.prop(before,key)
                    if value:
                        event=[x for x in event if not x.startswith(key+':')];event.insert(-1,key+':'+value)
            output.extend(event);event=None;continue
        selected={team_key(t,kind):cache[season].get(team_key(t,kind),labels.get(team_key(t,kind))) for t in game['teams'].values()}
        selected={k:v for k,v in selected.items() if v}
        cache[season].update(selected)
        if kind=='NCAA':summary=re.sub(r' (?:#\d+|\(NC\)|NC)(?= - | — |$)','',summary)
        else:summary=re.sub(r'\b'+kind+r'(?: Playoffs| Wild Card(?: Series)?| Divisional Round| Conference Championship| Super Bowl| Division Series| Championship Series| World Series)? :',kind+' '+game['round']+' :',summary, count=1)
        for competitor in game['teams'].values():
            key=team_key(competitor,kind);seed=selected.get(key)
            if not seed:continue
            team=competitor['team']
            names={team.get('displayName',''),team.get('location','')}
            if kind=='NCAA' and key=='lsu':names.add('LSU')
            for name in sorted(names,key=len,reverse=True):
                if name:summary=re.sub(re.escape(name)+r'(?= - | — |$)',lambda m:m[0]+' ['+seed+']',summary)
        event=['SUMMARY:'+escape(summary) if x.startswith('SUMMARY:') else x for x in event]
        if kind=='MLB':
            desc=decode(core.prop(event,'DESCRIPTION')).split('\nSérie :',1)[0]
            note=series_note(game,rows)
            if note:desc+='\n'+note
            event=['DESCRIPTION:'+escape(desc) if x.startswith('DESCRIPTION:') else x for x in event]
        event=[x for x in event if not x.startswith(('X-POST-SEASON:','X-POST-SEEDS:'))]
        event[-1:-1]=['X-POST-SEASON:'+str(season),'X-POST-SEEDS:'+escape(json.dumps(selected,ensure_ascii=False,sort_keys=True))]
        output.extend(event);event=None
    # Les rédacteurs de localisations comparent ensuite le contenu final à l’ancien
    # fichier et mettent à jour SEQUENCE/DTSTAMP, sans modifier l’UID.
    return '\r\n'.join(part for line in output for part in core.fold(line))+'\r\n'
