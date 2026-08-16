import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ============================================================================

# CONFIGURATION

# ============================================================================

F1_URL = (
"https://raw.githubusercontent.com/sportstimes/f1/main/"
"_db/f1/2026.json"
)

TV_URL = (
"https://tv-sports.fr/rss/competition/1434/"
"grand-prix-des-pays-bas?direct=1"
)

NOMS_SESSIONS = {
"fp1": "Essais libres 1",
"fp2": "Essais libres 2",
"fp3": "Essais libres 3",
"sprintQualifying": "Sprint Qualifying",
"sprint": "Sprint",
"qualifying": "Qualifications",
"gp": "Grand Prix",
}

# ============================================================================

# OUTILS

# ============================================================================

def afficher_titre(titre):
print()
print("=" * 90)
print(titre)
print("=" * 90)

def recuperer_f1():
reponse = requests.get(F1_URL, timeout=10)
reponse.raise_for_status()

```
data = reponse.json()

for course in data["races"]:
    if course["name"].lower() == "dutch":
        return course

raise RuntimeError(
    "GP des Pays-Bas introuvable dans le calendrier F1."
)
```

def recuperer_tv():
reponse = requests.get(TV_URL, timeout=10)
reponse.raise_for_status()

```
root = ET.fromstring(reponse.content)

evenements = []

for item in root.findall("./channel/item"):
    titre = item.findtext("title", "")
    description = item.findtext("description", "")
    lien = item.findtext("link", "")
    pub_date = item.findtext("pubDate", "")

    if not pub_date:
        continue

    # Exemple :
    # Fri, 21 Aug 2026 12:15:00 +0200
    horaire = datetime.strptime(
        pub_date,
        "%a, %d %b %Y %H:%M:%S %z"
    ).astimezone(timezone.utc)

    evenements.append({
        "titre": titre,
        "description": description,
        "lien": lien,
        "horaire_utc": horaire,
    })

return evenements
```

def afficher_session_f1(course):
afficher_titre(
"🏎️ CALENDRIER F1 — GRAND PRIX DES PAYS-BAS"
)

```
print(f"Nom       : {course['name']}")
print(f"Lieu      : {course['location']}")
print(f"Round     : {course['round']}")

print()
print("SESSIONS F1")
print("-" * 90)

sessions = []

for cle, horaire_iso in course["sessions"].items():
    horaire = datetime.fromisoformat(
        horaire_iso.replace("Z", "+00:00")
    )

    nom = NOMS_SESSIONS.get(cle, cle)

    sessions.append({
        "cle": cle,
        "nom": nom,
        "horaire_utc": horaire,
    })

    # Conversion dans le fuseau local du runner
    horaire_locale = horaire.astimezone()

    print(
        f"{nom:<22} "
        f"{horaire_locale.strftime('%d/%m/%Y %H:%M')} "
        f"(UTC {horaire.strftime('%H:%M')})"
    )

return sessions
```

def afficher_tv(evenements):
afficher_titre("📺 DIFFUSIONS TV-SPORTS")

```
if not evenements:
    print("Aucune diffusion trouvée.")
    return

for evenement in evenements:
    horaire = evenement["horaire_utc"]

    print(
        f"{horaire.astimezone().strftime('%d/%m/%Y %H:%M')}"
        f" | UTC {horaire.strftime('%H:%M')}"
    )

    print(f"  {evenement['titre']}")
    print(f"  {evenement['lien']}")
    print()
```

def afficher_candidats(sessions, evenements):
afficher_titre(
"🔎 CANDIDATS DE RAPPROCHEMENT"
)

```
print(
    "Pour chaque session F1, les diffusions TV-Sports "
    "situées dans une fenêtre de ±6 heures sont affichées."
)

print()

for session in sessions:
    print("-" * 90)

    horaire_f1 = session["horaire_utc"]

    print(
        f"🏎️ {session['nom']}"
        f" — {horaire_f1.astimezone().strftime('%d/%m %H:%M')}"
        f" (UTC {horaire_f1.strftime('%H:%M')})"
    )

    candidats = []

    for evenement in evenements:
        difference = abs(
            (
                evenement["horaire_utc"] - horaire_f1
            ).total_seconds()
        )

        if difference <= 6 * 60 * 60:
            candidats.append(
                (difference, evenement)
            )

    candidats.sort(
        key=lambda x: x[0]
    )

    if not candidats:
        print(
            "  ❌ Aucun candidat dans la fenêtre de ±6h"
        )
        continue

    for difference, evenement in candidats:
        heures = difference / 3600

        print(
            f"  → "
            f"{evenement['horaire_utc'].astimezone().strftime('%d/%m %H:%M')}"
            f" | écart {heures:.1f}h"
            f" | {evenement['titre']}"
        )
```

# ============================================================================

# PROGRAMME PRINCIPAL

# ============================================================================

if **name** == "**main**":

```
afficher_titre(
    "🏎️ TEST DU RAPPROCHEMENT F1 / TV-SPORTS"
)

print("📡 Récupération du calendrier F1...")
course = recuperer_f1()

print("📡 Récupération des diffusions TV-Sports...")
evenements_tv = recuperer_tv()

sessions = afficher_session_f1(course)

afficher_tv(evenements_tv)

afficher_candidats(
    sessions,
    evenements_tv
)

afficher_titre("✅ FIN DU TEST")
```
