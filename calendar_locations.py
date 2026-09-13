"""Localisations communes : stade, ville, équipe domicile si utile."""
import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone
import team_context as ics

HERE=Path(__file__).resolve().parent
PATHS={'NFL':['football/nfl'],'NCAA':['football/college-football'],
       'PL':['soccer/eng.1'],'PSG':['soccer/fra.1','soccer/uefa.champions'],
       'France':['soccer/uefa.nations']}
CITY_NAMES={'munchen':'Munich','muenchen':'Munich','london':'Londres','barcelona':'Barcelone',
            'como':'Côme','brussels':'Bruxelles','roma':'Rome','milan':'Milan','milano':'Milan'}
STADIUM_ALIASES={'geha field at arrowhead stadium':'arrowhead stadium',
 'stade orange velodrome':'stade velodrome','stadium municipal':'stadium municipal de toulouse',
 'stadio giuseppe sinigaglia':'giuseppe sinigaglia','stade du moustoir':'stade du moustoir yves allainmat','reliant stadium':'nrg stadium','parc olympique lyonnais':'groupama stadium',
                 'm marena':'mma rena','mmarena':'stade marie marvingt','stade atlantique':'matmut atlantique',
                 'bernabeu stadium':'santiago bernabeu','fc bayern munich stadium':'allianz arena'}


def norm(s):
    s=''.join(c for c in unicodedata.normalize('NFKD',str(s)).casefold() if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())


def decode(s):
    return re.sub(r'\\([nN,;\\])',lambda m:'\n' if m[1].lower()=='n' else m[1],s)


def escape(s):
    return s.replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')


def city_name(s):
    return CITY_NAMES.get(norm(s),s)


def location(stadium,city,home=''):
    if not stadium or not city:
        return stadium or ''
    city=city_name(city)
    # Les variantes linguistiques d’une ville désignent le même lieu.
    home_key=norm(home)
    for source,target in CITY_NAMES.items():
        home_key=re.sub(r'\b'+re.escape(source)+r'\b',norm(target),home_key)
    suffix=' — '+home if home and norm(city) not in home_key else ''
    return f'{stadium}, {city}{suffix}'


def extract_venues(data):
    result={}
    for event in data.get('events',[]):
        for comp in event.get('competitions',[]):
            venue=comp.get('venue') or {}
            stadium=venue.get('fullName','')
            city=(venue.get('address') or {}).get('city','')
            if stadium and city:
                key=norm(stadium)
                if key in result and result[key]!=city:
                    result[key]=''  # Pas d’homonyme résolu au hasard.
                else:result[key]=city
    return {k:v for k,v in result.items() if v}


@lru_cache(maxsize=12)
def registry(kind,year):
    seed=json.loads((HERE/'venues.json').read_text(encoding='utf-8'))
    result=dict(seed.get(kind,{}))
    try:
        if kind=='F1':
            # Le fichier contient les noms de circuits et leurs villes.
            return result
        if kind=='MLB':
            data=ics.fetch('https://statsapi.mlb.com/api/v1/venues?sportId=1&hydrate=location')
            result.update({norm(v['name']):v['location']['city'] for v in data.get('venues',[])
                           if v.get('location',{}).get('city')})
        else:
            for path in PATHS.get(kind,[]):
                url='https://site.api.espn.com/apis/site/v2/sports/'+path+'/scoreboard?limit=1000&dates='+str(year)+'0801-'+str(year+1)+'0701'
                if kind=='NCAA':url+='&groups=80'
                result.update(extract_venues(ics.fetch(url)))
    except Exception as exc:
        logging.warning('Villes %s : référentiel conservé en secours (%s)',kind,exc)
    return result


def normalize_calendar(text,path,kind,lookup=None,now=None):
    now=now or datetime.now(timezone.utc)
    year=now.year if now.month>=7 or kind in ('NFL','MLB','F1') else now.year-1
    lookup=registry(kind,year) if lookup is None else lookup
    previous=Path(path).read_text(encoding='utf-8') if Path(path).exists() else ''
    old={ics.prop(e,'UID'):e for e in ics.blocks(previous)}
    result=[];event=None
    for line in ics.unfold(text):
        if line=='BEGIN:VEVENT':event=[]
        if event is None:result.append(line);continue
        event.append(line)
        if line!='END:VEVENT':continue
        raw=decode(ics.prop(event,'LOCATION'))
        summary=ics.strip_labels(decode(ics.prop(event,'SUMMARY')))
        home=summary.split(' : ',1)[-1].split(' - ',1)[0] if ' : ' in summary and ' - ' in summary else ''
        if kind=='NCAA' and ics.prop(event,'X-CFB-HOME-DISPLAY'):
            home=decode(ics.prop(event,'X-CFB-HOME-DISPLAY'))
        home=re.sub(r'\s+(?:#\d+|\(NC\)|NC)$','',home)
        if kind=='NCAA' and not home:
            home=ics.prop(event,'X-CFB-HOME').title()
        # Une localisation déjà normalisée peut fournir la ville de secours.
        raw=raw.split(' — ',1)[0]
        stadium=raw;city=''
        if kind=='F1':
            pair=lookup.get(norm(raw))
            if pair:stadium,city=pair
            home=''
        else:
            key=norm(raw)
            city=lookup.get(key,'') or lookup.get(STADIUM_ALIASES.get(key,''),'')
            if not city and ', ' in raw:
                stadium,city=raw.rsplit(', ',1)
                city=lookup.get(norm(stadium),city)
            if not city and raw:
                logging.warning('Ville non résolue (%s) : %s',kind,raw)
        new=location(stadium,city,home) if city else raw
        if new:
            event=['LOCATION:'+escape(new) if x.startswith('LOCATION:') else x for x in event]
        before=old.get(ics.prop(event,'UID'))
        ignored=('DTSTAMP:','LAST-MODIFIED:','SEQUENCE:')
        body=lambda e:sorted(x for x in e if not x.startswith(ignored))
        if before and body(event)==body(before):
            event=before
        elif before:
            stamp=now.strftime('%Y%m%dT%H%M%SZ')
            seq=int(ics.prop(before,'SEQUENCE') or 0)+1
            event=[x for x in event if not x.startswith(ignored)]
            event[-1:-1]=['DTSTAMP:'+stamp,'LAST-MODIFIED:'+stamp,'SEQUENCE:'+str(seq)]
        result.extend(event);event=None
    return '\r\n'.join(part for line in result for part in ics.fold(line))+'\r\n'
