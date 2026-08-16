from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import requests


F1_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"
TV_SPORTS_URL = "https://tv-sports.fr/formule-1/"

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


class AnalyseurDiffusionsTV(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.element = None
        self.profondeur_li = 0

    def handle_starttag(self, balise, attributs):
        attributs = dict(attributs)
        classes = set(attributs.get("class", "").split())

        if balise == "li":
            if self.element is not None:
                self.profondeur_li += 1
            elif (
                "schedule-item" in classes
                and attributs.get("data-is-live") == "1"
            ):
                self.element = {}
                self.profondeur_li = 1
            return

        if self.element is None:
            return

        if balise == "time" and attributs.get("datetime"):
            self.element["datetime"] = attributs["datetime"]
        elif balise == "img" and "logoChaine" in classes:
            self.element["chaine"] = attributs.get("alt", "").strip()
        elif balise == "a" and "schedule-entity-visual" in classes:
            self.element["competition"] = attributs.get("title", "").strip()
            self.element["lien"] = attributs.get("href", "").strip()

    def handle_startendtag(self, balise, attributs):
        self.handle_starttag(balise, attributs)

    def handle_endtag(self, balise):
        if balise != "li" or self.element is None:
            return

        self.profondeur_li -= 1
        if self.profondeur_li == 0:
            self.elements.append(self.element)
            self.element = None


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


def extraire_diffusions_tv(page):
    analyseur = AnalyseurDiffusionsTV()
    analyseur.feed(page)
    diffusions = []
    deja_vues = set()

    for element in analyseur.elements:
        chaine = element.get("chaine", "")
        if not chaine.casefold().startswith("canal+"):
            continue

        try:
            horaire = datetime.fromisoformat(
                element["datetime"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue

        competition = element.get("competition") or "Formule 1"
        lien = element.get("lien") or TV_SPORTS_URL
        if lien.startswith("/"):
            lien = "https://tv-sports.fr" + lien

        titre = f"{competition} ({chaine})"
        cle = (horaire, competition, chaine)
        if cle not in deja_vues:
            deja_vues.add(cle)
            diffusions.append({"horaire": horaire, "titre": titre, "lien": lien})

    return sorted(diffusions, key=lambda diffusion: diffusion["horaire"])


def recuperer_diffusions_tv():
    reponse = requests.get(TV_SPORTS_URL, headers=EN_TETES, timeout=20)
    reponse.raise_for_status()
    return extraire_diffusions_tv(reponse.text)


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


def recuperer_dtstamp_existant():
    try:
        with open("f1_calendar.ics", encoding="utf-8") as calendrier:
            for ligne in calendrier:
                if ligne.startswith("DTSTAMP:"):
                    valeur = ligne.removeprefix("DTSTAMP:").strip()
                    datetime.strptime(valeur, "%Y%m%dT%H%M%SZ")
                    return valeur
    except (OSError, ValueError):
        pass

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
        print(f"{len(diffusions)} directs Canal+ trouvés sur TV-Sports.")
    except requests.RequestException as erreur:
        print(f"Avertissement : TV-Sports est inaccessible ({erreur}).")
        diffusions = []

    associations = associer_diffusions(sessions, diffusions)
    dtstamp = recuperer_dtstamp_existant()
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
