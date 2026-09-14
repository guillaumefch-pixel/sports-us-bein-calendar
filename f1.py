import calendar_locations
import re
import unicodedata
from pathlib import Path
import premier_league as cal
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

FENETRE_SECONDES = 20 * 60
F1_RIGHTS_URL = "https://boutique.canalplus.com/sport/f1"

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
        self.dans_h3 = False

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
                self.element = {"chaines": [], "texte": []}
                self.profondeur_li = 1

            return

        if self.element is None:
            return

        if balise == "h3":
            self.dans_h3 = True

        if balise == "time" and attributs.get("datetime"):
            self.element["datetime"] = attributs["datetime"]

        elif balise == "img" and "logoChaine" in classes:
            self.element["chaines"].append(attributs.get("alt", "").strip())

        elif balise == "a" and "schedule-entity-visual" in classes:
            self.element["competition"] = (
                attributs.get("title", "").strip()
            )

            self.element["lien"] = (
                attributs.get("href", "").strip()
            )

    def handle_startendtag(self, balise, attributs):
        self.handle_starttag(
            balise,
            attributs,
        )

    def handle_data(self, texte):
        if self.element is not None and self.dans_h3:
            self.element["texte"].append(texte)

    def handle_endtag(self, balise):
        if balise == "h3":
            self.dans_h3 = False
        if balise != "li" or self.element is None:
            return

        self.profondeur_li -= 1

        if self.profondeur_li == 0:
            self.elements.append(
                self.element
            )

            self.element = None


def identifier_seance(texte):
    texte = "".join(c for c in unicodedata.normalize("NFKD", texte.casefold()) if not unicodedata.combining(c))
    if "sprint" in texte and ("qualif" in texte or "shootout" in texte):return "sprintQualifying"
    if "sprint" in texte:return "sprint"
    if "qualif" in texte:return "qualifying"
    m = re.search(r"(?:essais? libres?|practice)\s*([123])", texte)
    if m:return "fp"+m[1]
    if "la course" in texte or texte.strip() == "course":return "gp"
    return None


def conserver_diffusions(texte, path):
    """Conserver une annonce précise si la grille glissante ne l'expose plus."""
    old = {cal.prop(e, "UID"): e for e in cal.read_ics(path.read_text())} if path.exists() else {}
    events = cal.read_ics(texte)
    for e in events:
        previous = old.get(cal.prop(e, "UID"))
        if not previous or cal.prop(previous, "DTSTART") != cal.prop(e, "DTSTART"):
            continue
        desc = cal.prop(previous, "DESCRIPTION")
        # Migration des anciennes notes "Diffusion : ... (Canal+ Sport)".
        match = re.search(r"\((Canal\+[^()]*)\)", desc)
        channel = match[1] if match else desc if desc.startswith("Canal+") and "confirmer" not in desc else ""
        if channel and cal.prop(e, "DESCRIPTION") == "Canal+ (chaîne à confirmer)":
            e[:] = ["DESCRIPTION:"+channel if x.startswith("DESCRIPTION:") else x for x in e]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//sports-us-bein-calendar//F1//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:F1 — Canal+",
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for e in events:lines += ["BEGIN:VEVENT", *e, "END:VEVENT"]
    return "\r\n".join(cal.fold(x) for x in lines+["END:VCALENDAR"])+"\r\n"


def recuperer_calendrier_f1():
    reponse = requests.get(
        F1_URL,
        headers=EN_TETES,
        timeout=20,
    )

    reponse.raise_for_status()

    return reponse.json()["races"]


def extraire_sessions(courses):
    sessions = []

    for course in courses:
        for cle, valeur_iso in course["sessions"].items():
            horaire = datetime.fromisoformat(
                valeur_iso.replace(
                    "Z",
                    "+00:00",
                )
            )

            sessions.append(
                {
                    "course": course,
                    "cle": cle,
                    "nom": NOMS_SESSIONS.get(
                        cle,
                        cle,
                    ),
                    "horaire": horaire.astimezone(
                        timezone.utc
                    ),
                    "duree_minutes": DUREES_MINUTES.get(
                        cle,
                        60,
                    ),
                }
            )

    return sorted(
        sessions,
        key=lambda session: session["horaire"],
    )


def extraire_diffusions_tv(page):
    analyseur = AnalyseurDiffusionsTV()
    analyseur.feed(page)

    diffusions = []
    deja_vues = set()

    for element in analyseur.elements:
        chaines = sorted(set(c for c in element.get("chaines", []) if c.casefold().startswith("canal+")))
        if not chaines:
            continue
        chaine = " + ".join(chaines)
        try:
            horaire = datetime.fromisoformat(
                element["datetime"].replace(
                    "Z",
                    "+00:00",
                )
            ).astimezone(
                timezone.utc
            )

        except (KeyError, ValueError):
            continue

        competition = (
            element.get("competition")
            or "Formule 1"
        )

        lien = (
            element.get("lien")
            or TV_SPORTS_URL
        )

        if lien.startswith("/"):
            lien = (
                "https://tv-sports.fr"
                + lien
            )

        titre = (
            f"{competition} ({chaine})"
        )

        cle = (
            horaire,
            competition,
            chaine,
        )

        if cle not in deja_vues:
            deja_vues.add(cle)

            diffusions.append(
                {
                    "horaire": horaire,
                    "titre": titre,
                    "chaine": chaine,
                    "seance": identifier_seance(" ".join(element.get("texte", []))),
                    "lien": lien,
                }
            )

    return sorted(
        diffusions,
        key=lambda diffusion: diffusion["horaire"],
    )


def recuperer_diffusions_tv():
    reponse = requests.get(
        TV_SPORTS_URL,
        headers=EN_TETES,
        timeout=20,
    )

    reponse.raise_for_status()

    return extraire_diffusions_tv(
        reponse.text
    )


def associer_diffusions(
    sessions,
    diffusions,
):
    disponibles = set(
        range(len(diffusions))
    )

    associations = {}

    for session in sessions:
        candidats = []

        for index in disponibles:
            phase = diffusions[index].get("seance")
            if phase and phase != session["cle"]:
                continue
            ecart = abs(
                (
                    diffusions[index]["horaire"]
                    - session["horaire"]
                ).total_seconds()
            )

            if ecart <= FENETRE_SECONDES:
                candidats.append(
                    (
                        ecart,
                        index,
                    )
                )

        if candidats:
            _, index = min(
                candidats
            )

            associations[id(session)] = (
                diffusions[index]
            )

            disponibles.remove(
                index
            )

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
        with open(
            "f1_calendar.ics",
            encoding="utf-8",
        ) as calendrier:
            for ligne in calendrier:
                if ligne.startswith(
                    "DTSTAMP:"
                ):
                    valeur = (
                        ligne
                        .removeprefix(
                            "DTSTAMP:"
                        )
                        .strip()
                    )

                    datetime.strptime(
                        valeur,
                        "%Y%m%dT%H%M%SZ",
                    )

                    return valeur

    except (OSError, ValueError):
        pass

    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def construire_vevent(
    session,
    diffusion,
    dtstamp,
):
    course = session["course"]

    debut = session["horaire"]

    fin = debut + timedelta(
        minutes=session["duree_minutes"]
    )

    resume = (
        f"🏎️ F1 — "
        f"{course['location']} — "
        f"{session['nom']}"
    )

    # Les droits du groupe sont confirmés jusqu'en 2029. Le canal exact
    # vient de la grille, jamais d'une règle supposant une chaîne par séance.
    description = [diffusion["chaine"] if diffusion else (
        "Canal+ (chaîne à confirmer)" if 2026 <= debut.year <= 2029
        else "Diffusion à confirmer")]

    lignes = [
        "BEGIN:VEVENT",
        (
            f"UID:f1-"
            f"{course['round']}-"
            f"{session['cle']}"
            f"@sports-us-bein-calendar"
        ),
        f"DTSTAMP:{dtstamp}",
        (
            f"DTSTART:"
            f"{debut.strftime('%Y%m%dT%H%M%SZ')}"
        ),
        (
            f"DTEND:"
            f"{fin.strftime('%Y%m%dT%H%M%SZ')}"
        ),
        (
            f"SUMMARY:"
            f"{echapper_ics(resume)}"
        ),
        (
            f"DESCRIPTION:"
            f"{echapper_ics(chr(10).join(description))}"
        ),
        (
            f"LOCATION:"
            f"{echapper_ics(course['location'])}"
        ),
    ]

    latitude = course.get(
        "latitude"
    )

    longitude = course.get(
        "longitude"
    )

    if (
        latitude is not None
        and longitude is not None
    ):
        lignes.append(
            f"GEO:{latitude};{longitude}"
        )

    lignes.append("URL:" + (diffusion["lien"] if diffusion else F1_RIGHTS_URL))
    lignes.append("STATUS:CONFIRMED")
    lignes.append("TRANSP:OPAQUE")
    lignes.append("END:VEVENT")

    return lignes


def main():
    print(
        "Téléchargement du calendrier F1…"
    )

    sessions = extraire_sessions(
        recuperer_calendrier_f1()
    )

    print(
        "Téléchargement des diffusions TV-Sports…"
    )

    try:
        diffusions = (
            recuperer_diffusions_tv()
        )

        print(
            f"{len(diffusions)} directs "
            f"Canal+ trouvés sur TV-Sports."
        )

    except requests.RequestException as erreur:
        print(
            f"Avertissement : TV-Sports "
            f"est inaccessible ({erreur})."
        )

        diffusions = []

    associations = associer_diffusions(
        sessions,
        diffusions,
    )

    dtstamp = (
        recuperer_dtstamp_existant()
    )

    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        (
            "PRODID:-//sports-us-bein-calendar//"
            "F1 2026//FR"
        ),
        "CALSCALE:GREGORIAN",
    ]

    print(
        "\nDIFFUSIONS ASSOCIÉES"
    )

    for session in sessions:
        diffusion = associations.get(
            id(session)
        )

        lignes.extend(
            construire_vevent(
                session,
                diffusion,
                dtstamp,
            )
        )

        if diffusion:
            print(
                f"{session['horaire']:%Y-%m-%d %H:%M} — "
                f"{session['course']['location']} — "
                f"{session['nom']} → "
                f"{diffusion['titre']}"
            )

    lignes.append(
        "END:VCALENDAR"
    )

    contenu = conserver_diffusions("\r\n".join(lignes)+"\r\n", Path("f1_calendar.ics"))
    contenu = calendar_locations.normalize_calendar(contenu, "f1_calendar.ics", "F1")
    with open(
        "f1_calendar.ics",
        "w",
        encoding="utf-8",
        newline="",
    ) as fichier:
        fichier.write(
            contenu
        )

    print(
        f"\n{len(sessions)} sessions "
        f"écrites dans f1_calendar.ics."
    )

    print(
        f"{len(associations)} "
        f"diffusions TV associées."
    )


if __name__ == "__main__":
    main()

