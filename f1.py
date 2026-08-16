import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

F1_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"
TV_RSS_TEMPLATE = "https://tv-sports.fr/rss/competition/{tv_id}/{tv_slug}?direct=1"

NOMS_SESSIONS = {
    "fp1": "Essais libres 1",
    "fp2": "Essais libres 2",
    "fp3": "Essais libres 3",
    "sprintQualifying": "Sprint Qualifying",
    "sprint": "Sprint",
    "qualifying": "Qualifications",
    "gp": "Grand Prix",
}

# Durée par défaut de chaque type de session (pour DTEND)
DUREES_MINUTES = {
    "fp1": 60,
    "fp2": 60,
    "fp3": 60,
    "sprintQualifying": 60,
    "sprint": 60,
    "qualifying": 60,
    "gp": 120,
}

FENETRE_SECONDES = 6 * 60 * 60  # tolérance de rapprochement F1 / TV

# Correspondance nom sportstimes -> compétition TV-Sports (id + slug)
# Construits à partir de https://tv-sports.fr/competitions-sports-tv?sport=formule-1
# "Spanish" (Madrid, round 14) et "Bahrain Grand Prix (Malaysia)" (round 16)
# n'ont pas de correspondance fiable sur TV-Sports pour l'instant -> volontairement absents.
TV_SPORTS_MAPPING = {
    "Australian": (1135, "grand-prix-d-australie"),
    "Chinese": (369, "grand-prix-de-chine"),
    "Japanese": (718, "grand-prix-du-japon"),
    "Miami": (1523, "grand-prix-de-miami"),
    "Canadian": (489, "grand-prix-du-canada"),
    "Monaco": (451, "grand-prix-de-monaco"),
    "Barcelona-Catalunya": (427, "grand-prix-d-espagne"),
    "Austrian": (541, "grand-prix-d-autriche"),
    "British": (557, "grand-prix-de-grande-bretagne"),
    "Belgian": (631, "grand-prix-de-spa-francorchamps"),
    "Hungarian": (593, "grand-prix-de-hongrie"),
    "Dutch": (1434, "grand-prix-des-pays-bas"),
    "Italian": (640, "grand-prix-d-italie-monza"),
    "Azerbaijan": (400, "grand-prix-d-azerbaidjan"),
    "Singapore": (673, "grand-prix-de-singapour"),
    "United States": (872, "grand-prix-des-etats-unis"),
    "Mexican": (854, "grand-prix-du-mexique"),
    "Brazilian": (897, "grand-prix-du-bresil"),
    "Las Vegas": (1580, "grand-prix-de-las-vegas"),
    "Qatar": (1486, "grand-prix-du-qatar"),
    "Abu Dhabi": (914, "grand-prix-d-abu-dhabi"),
}


def titre(texte):
    print()
    print("=" * 90)
    print(texte)
    print("=" * 90)


def recuperer_calendrier_f1():
    reponse = requests.get(F1_URL, timeout=10)
    reponse.raise_for_status()
    return reponse.json()["races"]


def extraire_sessions(course):
    sessions = []
    for cle, valeur_iso in course["sessions"].items():
        horaire = datetime.fromisoformat(valeur_iso.replace("Z", "+00:00"))
        sessions.append({
            "cle": cle,
            "nom": NOMS_SESSIONS.get(cle, cle),
            "horaire": horaire,
            "duree_minutes": DUREES_MINUTES.get(cle, 60),
        })
    sessions.sort(key=lambda s: s["horaire"])
    return sessions


def recuperer_diffusions_tv(nom_course):
    mapping = TV_SPORTS_MAPPING.get(nom_course)
    if mapping is None:
        return None  # pas de correspondance connue

    tv_id, tv_slug = mapping
    url = TV_RSS_TEMPLATE.format(tv_id=tv_id, tv_slug=tv_slug)

    try:
        reponse = requests.get(url, timeout=10)
        reponse.raise_for_status()
        root = ET.fromstring(reponse.content)
    except (requests.RequestException, ET.ParseError) as erreur:
        print(f"  ⚠️ Flux TV-Sports inaccessible pour {nom_course} : {erreur}")
        return []

    evenements = []
    for item in root.findall("./channel/item"):
        pub_date = item.findtext("pubDate")
        if not pub_date:
            continue

        horaire = datetime.strptime(
            pub_date, "%a, %d %b %Y %H:%M:%S %z"
        ).astimezone(timezone.utc)

        evenements.append({
            "titre": item.findtext("title", ""),
            "lien": item.findtext("link", ""),
            "horaire": horaire,
        })

    return evenements


def meilleure_diffusion(session, evenements_tv):
    if not evenements_tv:
        return None

    candidats = []
    for evenement in evenements_tv:
        ecart = abs((evenement["horaire"] - session["horaire"]).total_seconds())
        if ecart <= FENETRE_SECONDES:
            candidats.append((ecart, evenement))

    if not candidats:
        return None

    candidats.sort(key=lambda c: c[0])
    return candidats[0][1]


def echapper_ics(texte):
    return (
        texte.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def construire_vevent(course, session, diffusion):
    debut = session["horaire"]
    fin = debut + timedelta(minutes=session["duree_minutes"])

    summary = f"F1 - {course['location']} - {session['nom']}"

    description_lignes = [f"Grand Prix : {course['name']} ({course['location']})"]
    if diffusion:
        description_lignes.append(f"Diffusion : {diffusion['titre']}")
        description_lignes.append(diffusion["lien"])
    else:
        description_lignes.append("Diffusion TV : non trouvée")

    uid = f"f1-{course['round']}-{session['cle']}@sports-us-bein-calendar"

    lignes = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{debut.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{fin.strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{echapper_ics(summary)}",
        f"DESCRIPTION:{echapper_ics(chr(10).join(description_lignes))}",
        f"LOCATION:{echapper_ics(course['location'])}",
        "END:VEVENT",
    ]
    return lignes


def main():
    titre("🏎️ GÉNÉRATION DU CALENDRIER F1 2026 (avec diffusions TV-Sports)")

    print()
    print("📡 Téléchargement du calendrier F1...")
    courses = recuperer_calendrier_f1()
    print(f"  {len(courses)} courses trouvées.")

    lignes_ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//sports-us-bein-calendar//F1 2026//FR",
        "CALSCALE:GREGORIAN",
    ]

    total_sessions = 0
    total_avec_tv = 0

    for course in courses:
        nom = course["name"]
        print()
        print(f"🏎️ {nom} — {course['location']}")

        sessions = extraire_sessions(course)
        evenements_tv = recuperer_diffusions_tv(nom)

        if evenements_tv is None:
            print("  ⚠️ Aucune correspondance TV-Sports connue pour ce GP.")
        elif not evenements_tv:
            print("  ⚠️ Flux TV-Sports vide ou inaccessible.")
        else:
            print(f"  {len(evenements_tv)} diffusions TV trouvées.")

        for session in sessions:
            diffusion = meilleure_diffusion(session, evenements_tv or [])
            lignes_ics.extend(construire_vevent(course, session, diffusion))

            total_sessions += 1
            if diffusion:
                total_avec_tv += 1
                print(f"    ✅ {session['nom']:<20} → {diffusion['titre']}")
            else:
                print(f"    ➖ {session['nom']:<20} (pas de diffusion associée)")

    lignes_ics.append("END:VCALENDAR")

    with open("f1_calendar.ics", "w", encoding="utf-8") as fichier:
        fichier.write("\r\n".join(lignes_ics) + "\r\n")

    titre("✅ TERMINÉ")
    print(f"Sessions générées      : {total_sessions}")
    print(f"Avec diffusion TV      : {total_avec_tv}")
    print(f"Fichier écrit          : f1_calendar.ics")


if __name__ == "__main__":
    main()
