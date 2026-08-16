import re
from datetime import datetime, timedelta, timezone
from html import unescape

import requests


F1_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"
TV_SPORTS_URL = "https://tv-sports.fr/formule-1"

NOMS_SESSIONS = {
    "fp1": "Essais libres 1",
    "fp2": "Essais libres 2",
    "fp3": "Essais libres 3",
    "sprintQualifying": "Qualifications Sprint",
    "sprint": "Sprint",
    "qualifying": "Qualifications",
    "gp": "Grand Prix",
}

DUREES_MINUTES = {
    "fp1": 60,
    "fp2": 60,
    "fp3": 60,
    "sprintQualifying": 60,
    "sprint": 60,
    "qualifying": 60,
    "gp": 120,
}

FENETRE_SECONDES = 3 * 60 * 60
EN_TETES = {
    "User-Agent": "Mozilla/5.0 (compatible; F1CalendarBot/1.0)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def recuperer_calendrier_f1():
    reponse = requests.get(F1_URL, headers=EN_TETES, timeout=20)
    reponse.raise_for_status()
    return reponse.json()["races"]


def extraire_sessions(courses):
    sessions = []
    for course in courses:
        for cle, valeur_iso in course["sessions"].items():
            horaire = datetime.fromisoformat(valeur_iso.replace("Z", "+00:00"))
            sessions.append(
                {
                    "course": course,
                    "cle": cle,
                    "nom": NOMS_SESSIONS.get(cle, cle),
                    "horaire": horaire.astimezone(timezone.utc),
                    "duree_minutes": DUREES_MINUTES.get(cle, 60),
                }
            )
    return sorted(sessions, key=lambda session: session["horaire"])


def nettoyer_texte(texte):
    texte = re.sub(r"<[^>]+>", " ", unescape(texte))
    return re.sub(r"\s+", " ", texte).strip()


def recuperer_diffusions_tv():
    reponse = requests.get(TV_SPORTS_URL, headers=EN_TETES, timeout=20)
    reponse.raise_for_status()
    page = reponse.text

    # TV-Sports place les horaires de diffusion dans des balises <time>.
    blocs = re.findall(
        r"(?is)<(?:article|li|div)\b[^>]*>.*?</(?:article|li|div)>", page
    )
    diffusions = []
    deja_vues = set()

    for bloc in blocs:
        if "canal+" not in bloc.lower() or "direct" not in bloc.lower():
            continue

        correspondance = re.search(
            r'<time\b[^>]*datetime=["\']([^"\']+)["\'][^>]*>', bloc, re.I
        )
        if not correspondance:
            continue

        try:
            horaire = datetime.fromisoformat(
                correspondance.group(1).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError:
            continue

        titre = nettoyer_texte(bloc)
        lien_match = re.search(r'href=["\']([^"\']+)["\']', bloc, re.I)
        lien = lien_match.group(1) if lien_match else TV_SPORTS_URL
        if lien.startswith("/"):
            lien = "https://tv-sports.fr" + lien

        cle = (horaire, titre)
        if cle not in deja_vues:
            deja_vues.add(cle)
            diffusions.append({"horaire": horaire, "titre": titre, "lien": lien})

    return sorted(diffusions, key=lambda diffusion: diffusion["horaire"])


def associer_diffusions(sessions, diffusions):
    disponibles = set(range(len(diffusions)))
    associations = {}

    for session in sessions:
        candidats = []
        for index in disponibles:
            ecart = abs(
                (diffusions[index]["horaire"] - session["horaire"]).total_seconds()
            )
            if ecart <= FENETRE_SECONDES:
                candidats.append((ecart, index))

        if candidats:
            _, index = min(candidats)
            associations[id(session)] = diffusions[index]
            disponibles.remove(index)

    return associations


def echapper_ics(texte):
    return (
        str(texte)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def construire_vevent(session, diffusion, dtstamp):
    course = session["course"]
    debut = session["horaire"]
    fin = debut + timedelta(minutes=session["duree_minutes"])
    resume = f"F1 - {course['location']} - {session['nom']}"
    description = [f"Grand Prix : {course['name']} ({course['location']})"]

    if diffusion:
        description.extend((f"Diffusion : {diffusion['titre']}", diffusion["lien"]))
    else:
        description.append("Diffusion TV : non trouvée")

    return [
        "BEGIN:VEVENT",
        f"UID:f1-{course['round']}-{session['cle']}@sports-us-bein-calendar",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{debut.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{fin.strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{echapper_ics(resume)}",
        f"DESCRIPTION:{echapper_ics(chr(10).join(description))}",
        f"LOCATION:{echapper_ics(course['location'])}",
        "END:VEVENT",
    ]


def main():
    print("Téléchargement du calendrier F1…")
    sessions = extraire_sessions(recuperer_calendrier_f1())

    print("Téléchargement des diffusions TV-Sports…")
    try:
        diffusions = recuperer_diffusions_tv()
    except requests.RequestException as erreur:
        print(f"Avertissement : TV-Sports est inaccessible ({erreur}).")
        diffusions = []

    associations = associer_diffusions(sessions, diffusions)
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//sports-us-bein-calendar//F1 2026//FR",
        "CALSCALE:GREGORIAN",
    ]

    print("\nDIFFUSIONS ASSOCIÉES")
    for session in sessions:
        diffusion = associations.get(id(session))
        lignes.extend(construire_vevent(session, diffusion, dtstamp))
        if diffusion:
            print(
                f"{session['horaire']:%Y-%m-%d %H:%M} — "
                f"{session['course']['location']} — {session['nom']} → "
                f"{diffusion['titre']}"
            )

    lignes.append("END:VCALENDAR")
    with open("f1_calendar.ics", "w", encoding="utf-8", newline="") as fichier:
        fichier.write("\r\n".join(lignes) + "\r\n")

    print(f"\n{len(sessions)} sessions écrites dans f1_calendar.ics.")
    print(f"{len(associations)} diffusions TV associées.")


if __name__ == "__main__":
    main()
