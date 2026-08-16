import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

F1_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"

TV_URL = "https://tv-sports.fr/rss/competition/1434/grand-prix-des-pays-bas?direct=1"

NOMS_SESSIONS = {
"fp1": "Essais libres 1",
"fp2": "Essais libres 2",
"fp3": "Essais libres 3",
"sprintQualifying": "Sprint Qualifying",
"sprint": "Sprint",
"qualifying": "Qualifications",
"gp": "Grand Prix",
}

print()
print("=" * 90)
print("🏎️ TEST DU RAPPROCHEMENT F1 / TV-SPORTS")
print("=" * 90)

# ============================================================================

# 1. CALENDRIER F1

# ============================================================================

print()
print("📡 Récupération du calendrier F1...")

response = requests.get(F1_URL, timeout=10)
response.raise_for_status()

data = response.json()

course = None

for race in data["races"]:
if race["name"].lower() == "dutch":
course = race
break

if course is None:
raise RuntimeError("GP des Pays-Bas introuvable.")

print()
print("=" * 90)
print("🏎️ GRAND PRIX DES PAYS-BAS — SPORTSTIMES")
print("=" * 90)

print(f"Nom    : {course['name']}")
print(f"Lieu   : {course['location']}")
print(f"Round  : {course['round']}")

sessions = []

for key, iso in course["sessions"].items():

```
dt = datetime.fromisoformat(
    iso.replace("Z", "+00:00")
)

sessions.append({
    "key": key,
    "name": NOMS_SESSIONS.get(key, key),
    "datetime": dt,
})

print(
    f"{NOMS_SESSIONS.get(key, key):<22}"
    f" {dt.strftime('%d/%m/%Y %H:%M')} UTC"
)
```

# ============================================================================

# 2. TV-SPORTS

# ============================================================================

print()
print("📡 Récupération des diffusions TV-Sports...")

response = requests.get(TV_URL, timeout=10)
response.raise_for_status()

root = ET.fromstring(response.content)

tv_events = []

for item in root.findall("./channel/item"):

```
title = item.findtext("title", "")
description = item.findtext("description", "")
link = item.findtext("link", "")
pub_date = item.findtext("pubDate", "")

if not pub_date:
    continue

dt = datetime.strptime(
    pub_date,
    "%a, %d %b %Y %H:%M:%S %z"
).astimezone(timezone.utc)

tv_events.append({
    "title": title,
    "description": description,
    "link": link,
    "datetime": dt,
})
```

print()
print("=" * 90)
print("📺 DIFFUSIONS TV-SPORTS")
print("=" * 90)

for event in tv_events:

```
print(
    f"{event['datetime'].strftime('%d/%m/%Y %H:%M')} UTC"
    f" | {event['title']}"
)

print(f"  {event['link']}")
```

# ============================================================================

# 3. RAPPROCHEMENT

# ============================================================================

print()
print("=" * 90)
print("🔎 RAPPROCHEMENT F1 / TV-SPORTS")
print("=" * 90)

print()
print("Fenêtre de recherche : ±6 heures")
print()

for session in sessions:

```
print("-" * 90)

f1_time = session["datetime"]

print(
    f"🏎️ {session['name']}"
    f" — {f1_time.strftime('%d/%m/%Y %H:%M')} UTC"
)

candidates = []

for event in tv_events:

    difference = abs(
        (event["datetime"] - f1_time).total_seconds()
    )

    if difference <= 6 * 60 * 60:
        candidates.append(
            (difference, event)
        )

candidates.sort(
    key=lambda item: item[0]
)

if not candidates:

    print("  ❌ Aucun candidat")

else:

    for difference, event in candidates:

        hours = difference / 3600

        print(
            f"  → {event['datetime'].strftime('%d/%m/%Y %H:%M')} UTC"
            f" | écart : {hours:.1f} h"
            f" | {event['title']}"
        )
```

# ============================================================================

# FIN

# ============================================================================

print()
print("=" * 90)
print("✅ FIN DU TEST")
print("=" * 90)
