import hashlib
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import requests


EN_TETES = {
    "User-Agent": "Mozilla/5.0 (compatible; SportsCalendarBot/1.0)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

SPORTS = (
    {
        "nom": "MLB sur beIN",
        "prefixe": "MLB",
        "emoji": "⚾",
        "url": "https://tv-sports.fr/base-ball/mlb/match-direct",
        "fichier": "mlb_bein_calendar.ics",
        "duree_minutes": 210,
    },
    {
        "nom": "NFL sur beIN",
        "prefixe": "NFL",
        "emoji": "🏈",
        "url": "https://tv-sports.fr/football-americain/nfl",
        "fichier": "nfl_bein_calendar.ics",
        "duree_minutes": 240,
    },
)


class AnalyseurPlanning(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.element = None
        self.profondeur_li = 0
        self.ancre = None

    def handle_starttag(self, balise, attributs):
        attributs = dict(attributs)
        classes = set(attributs.get("class", "").split())

        if balise == "li":
            if self.element is not None:
                self.profondeur_li += 1
            elif "schedule-item" in classes:
                self.element = {
                    "attributs": attributs,
                    "participants": [],
                    "liens": [],
                }
                self.profondeur_li = 1
            return

        if self.element is None:
            return

        if balise == "time" and attributs.get("datetime"):
            self.element["datetime"] = attributs["datetime"]

        elif balise == "img" and "logoChaine" in classes:
            self.element["chaine"] = attributs.get("alt", "").strip()

        elif balise == "a":
            self.ancre = {
                "classes": classes,
                "href": attributs.get("href", "").strip(),
                "title": attributs.get("title", "").strip(),
                "texte": [],
            }

            if "schedule-participant" in classes and self.ancre["title"]:
                self.element["participants"].append(self.ancre["title"])

    def handle_startendtag(self, balise, attributs):
        self.handle_starttag(balise, attributs)

    def handle_data(self, donnees):
        if self.ancre is not None:
            self.ancre["texte"].append(donnees)

    def handle_endtag(self, balise):
        if (
            balise == "a"
            and self.ancre is not None
            and self.element is not None
        ):
            self.ancre["texte"] = " ".join(
                "".join(self.ancre["texte"]).split()
            )

            self.element["liens"].append(self.ancre)
            self.ancre = None
            return

        if balise != "li" or self.element is None:
            return

        self.profondeur_li -= 1

        if self.profondeur_li == 0:
            self.elements.append(self.element)
            self.element = None
            self.ancre = None


def est_chaine_bein(chaine):
    return chaine.casefold().startswith("bein sports")


def choisir_titre(element, prefixe):
    participants = element.get("participants", [])

    if len(participants) >= 2:
        return " – ".join(participants[:2])

    for lien in element.get("liens", []):
        href = lien["href"]

        if (
            lien["texte"]
            and (
                "-tv-" in href
                or re.search(r"-e\d+/?$", href)
            )
        ):
            return lien["texte"]

    for lien in element.get("liens", []):
        if (
            "schedule-entity-visual" in lien["classes"]
            and lien["title"]
        ):
            return lien["title"]

    return f"Programme {prefixe}"


def choisir_lien(element, url_page):
    for lien in reversed(element.get("liens", [])):
        if (
            lien["href"]
            and (
                "-tv-" in lien["href"]
                or re.search(r"-e\d+/?$", lien["href"])
            )
        ):
            href = lien["href"]

            return (
                "https://tv-sports.fr" + href
                if href.startswith("/")
                else href
            )

    return url_page


def extraire_diffusions(page, sport):
    analyseur = AnalyseurPlanning()
    analyseur.feed(page)

    if (
        not analyseur.elements
        and "aucune diffusion" not in page.casefold()
    ):
        raise RuntimeError(
            f"Le planning {sport['prefixe']} "
            f"n'a pas été reconnu sur TV-Sports."
        )

    diffusions = []
    deja_vues = set()

    for element in analyseur.elements:
        attributs = element["attributs"]
        chaine = element.get("chaine", "")

        if attributs.get("data-is-live") != "1":
            continue

        if attributs.get("data-is-past") == "1":
            continue

        if not est_chaine_bein(chaine):
            continue

        try:
            debut = datetime.fromisoformat(
                element["datetime"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)

        except (KeyError, ValueError):
            continue

        titre = choisir_titre(
            element,
            sport["prefixe"],
        )

        lien = choisir_lien(
            element,
            sport["url"],
        )

        cle = (
            debut,
            titre,
        )

        if cle in deja_vues:
            for diffusion in diffusions:
                if (
                    diffusion["debut"],
                    diffusion["titre"],
                ) == cle:
                    if chaine not in diffusion["chaines"]:
                        diffusion["chaines"].append(chaine)

                    break

            continue

        deja_vues.add(cle)

        diffusions.append(
            {
                "debut": debut,
                "titre": titre,
                "chaines": [chaine],
                "lien": lien,
            }
        )

    return sorted(
        diffusions,
        key=lambda diffusion: diffusion["debut"],
    )


def echapper_ics(texte):
    return (
        str(texte)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def couper_utf8(texte, limite):
    taille = 0
    position = 0

    for caractere in texte:
        nouvelle_taille = taille + len(
            caractere.encode("utf-8")
        )

        if nouvelle_taille > limite:
            break

        taille = nouvelle_taille
        position += 1

    return texte[:position], texte[position:]


def plier_ligne_ics(ligne):
    morceaux = []
    reste = ligne
    premier = True

    while reste:
        limite = 75 if premier else 74

        morceau, reste = couper_utf8(
            reste,
            limite,
        )

        morceaux.append(
            ("" if premier else " ") + morceau
        )

        premier = False

    return morceaux or [""]


def recuperer_dtstamp_existant(fichier):
    try:
        with open(
            fichier,
            encoding="utf-8",
        ) as calendrier:
            for ligne in calendrier:
                if ligne.startswith("DTSTAMP:"):
                    valeur = (
                        ligne
                        .removeprefix("DTSTAMP:")
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
    ).strftime("%Y%m%dT%H%M%SZ")


def duree_diffusion(diffusion, sport):
    titre_compact = re.sub(
        r"[^a-z]",
        "",
        diffusion["titre"].casefold(),
    )

    if (
        sport["prefixe"] == "NFL"
        and "redzone" in titre_compact
    ):
        return 420

    return sport["duree_minutes"]


def construire_evenement(
    diffusion,
    sport,
    dtstamp,
):
    debut = diffusion["debut"]

    fin = debut + timedelta(
        minutes=duree_diffusion(
            diffusion,
            sport,
        )
    )

    chaines = " / ".join(
        diffusion["chaines"]
    )

    resume = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} — "
        f"{diffusion['titre']}"
    )

    description = (
        f"Diffusion en direct : {chaines}\n"
        f"Source : {diffusion['lien']}"
    )

    empreinte = hashlib.sha256(
        (
            f"{sport['prefixe']}|"
            f"{debut.isoformat()}|"
            f"{diffusion['titre']}"
        ).encode()
    ).hexdigest()[:24]

    lignes = [
        "BEGIN:VEVENT",
        (
            f"UID:{sport['prefixe'].lower()}-"
            f"{empreinte}@sports-us-bein-calendar"
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
        f"SUMMARY:{echapper_ics(resume)}",
        (
            f"DESCRIPTION:"
            f"{echapper_ics(description)}"
        ),
        (
            f"LOCATION:"
            f"{echapper_ics(chaines)}"
        ),
        f"URL:{diffusion['lien']}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
    ]

    return lignes


def ecrire_calendrier(
    diffusions,
    sport,
):
    dtstamp = recuperer_dtstamp_existant(
        sport["fichier"]
    )

    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        (
            f"PRODID:-//sports-us-bein-calendar//"
            f"{sport['prefixe']} beIN//FR"
        ),
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        (
            f"X-WR-CALNAME:"
            f"{echapper_ics(sport['nom'])}"
        ),
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for diffusion in diffusions:
        lignes.extend(
            construire_evenement(
                diffusion,
                sport,
                dtstamp,
            )
        )

    lignes.append("END:VCALENDAR")

    lignes_pliees = []

    for ligne in lignes:
        lignes_pliees.extend(
            plier_ligne_ics(ligne)
        )

    with open(
        sport["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write(
            "\r\n".join(lignes_pliees)
            + "\r\n"
        )


def extraire_vevents(fichier):
    evenements = []
    evenement = None

    with open(
        fichier,
        encoding="utf-8",
    ) as calendrier:
        for ligne in calendrier:
            ligne = ligne.rstrip(
                "\r\n"
            )

            if ligne == "BEGIN:VEVENT":
                evenement = [ligne]

            elif evenement is not None:
                evenement.append(ligne)

                if ligne == "END:VEVENT":
                    evenements.extend(
                        evenement
                    )

                    evenement = None

    return evenements


def ecrire_calendrier_global():
    fichiers = (
        "f1_calendar.ics",
        "mlb_bein_calendar.ics",
        "nfl_bein_calendar.ics",
        "psg_calendar.ics",
        "france_calendar.ics",
    )

    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        (
            "PRODID:-//sports-us-bein-calendar//"
            "Tous les sports//FR"
        ),
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        (
            "X-WR-CALNAME:"
            "Sports — F1 + MLB + NFL + PSG + France"
        ),
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for fichier in fichiers:
        lignes.extend(
            extraire_vevents(
                fichier
            )
        )

    lignes.append(
        "END:VCALENDAR"
    )

    with open(
        "sports_calendar.ics",
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write(
            "\r\n".join(lignes)
            + "\r\n"
        )


def main():
    for sport in SPORTS:
        print(
            f"Téléchargement de "
            f"{sport['nom']}…"
        )

        reponse = requests.get(
            sport["url"],
            headers=EN_TETES,
            timeout=30,
        )

        reponse.raise_for_status()

        diffusions = extraire_diffusions(
            reponse.text,
            sport,
        )

        ecrire_calendrier(
            diffusions,
            sport,
        )

        print(
            f"{len(diffusions)} "
            f"diffusion(s) écrite(s) dans "
            f"{sport['fichier']}."
        )

        for diffusion in diffusions:
            print(
                f"  "
                f"{diffusion['debut']:%Y-%m-%d %H:%M} UTC — "
                f"{diffusion['titre']} — "
                f"{' / '.join(diffusion['chaines'])}"
            )

    ecrire_calendrier_global()

    print(
        "Calendrier global écrit dans "
        "sports_calendar.ics."
    )


if __name__ == "__main__":
    main()
