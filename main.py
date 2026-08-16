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


STADES_MLB = {
    "arizona diamondbacks": "Chase Field, Phoenix",
    "athletics": "Sutter Health Park, West Sacramento",
    "oakland athletics": "Sutter Health Park, West Sacramento",
    "atlanta braves": "Truist Park, Atlanta",
    "baltimore orioles": "Oriole Park at Camden Yards, Baltimore",
    "boston red sox": "Fenway Park, Boston",
    "chicago cubs": "Wrigley Field, Chicago",
    "chicago white sox": "Rate Field, Chicago",
    "cincinnati reds": "Great American Ball Park, Cincinnati",
    "cleveland guardians": "Progressive Field, Cleveland",
    "colorado rockies": "Coors Field, Denver",
    "detroit tigers": "Comerica Park, Detroit",
    "houston astros": "Daikin Park, Houston",
    "kansas city royals": "Kauffman Stadium, Kansas City",
    "los angeles angels": "Angel Stadium, Anaheim",
    "los angeles dodgers": "Dodger Stadium, Los Angeles",
    "miami marlins": "loanDepot park, Miami",
    "milwaukee brewers": "American Family Field, Milwaukee",
    "minnesota twins": "Target Field, Minneapolis",
    "new york mets": "Citi Field, New York",
    "new york yankees": "Yankee Stadium, New York",
    "philadelphia phillies": "Citizens Bank Park, Philadelphia",
    "pittsburgh pirates": "PNC Park, Pittsburgh",
    "san diego padres": "Petco Park, San Diego",
    "san francisco giants": "Oracle Park, San Francisco",
    "seattle mariners": "T-Mobile Park, Seattle",
    "st louis cardinals": "Busch Stadium, St. Louis",
    "st. louis cardinals": "Busch Stadium, St. Louis",
    "tampa bay rays": "Tropicana Field, St. Petersburg",
    "texas rangers": "Globe Life Field, Arlington",
    "toronto blue jays": "Rogers Centre, Toronto",
    "washington nationals": "Nationals Park, Washington",
}


STADES_NFL = {
    "arizona cardinals": "State Farm Stadium, Glendale",
    "atlanta falcons": "Mercedes-Benz Stadium, Atlanta",
    "baltimore ravens": "M&T Bank Stadium, Baltimore",
    "buffalo bills": "Highmark Stadium, Orchard Park",
    "carolina panthers": "Bank of America Stadium, Charlotte",
    "chicago bears": "Soldier Field, Chicago",
    "cincinnati bengals": "Paycor Stadium, Cincinnati",
    "cleveland browns": "Huntington Bank Field, Cleveland",
    "dallas cowboys": "AT&T Stadium, Arlington",
    "denver broncos": "Empower Field at Mile High, Denver",
    "detroit lions": "Ford Field, Detroit",
    "green bay packers": "Lambeau Field, Green Bay",
    "houston texans": "NRG Stadium, Houston",
    "indianapolis colts": "Lucas Oil Stadium, Indianapolis",
    "jacksonville jaguars": "EverBank Stadium, Jacksonville",
    "kansas city chiefs": "GEHA Field at Arrowhead Stadium, Kansas City",
    "las vegas raiders": "Allegiant Stadium, Las Vegas",
    "los angeles chargers": "SoFi Stadium, Inglewood",
    "los angeles rams": "SoFi Stadium, Inglewood",
    "miami dolphins": "Hard Rock Stadium, Miami Gardens",
    "minnesota vikings": "U.S. Bank Stadium, Minneapolis",
    "new england patriots": "Gillette Stadium, Foxborough",
    "new orleans saints": "Caesars Superdome, New Orleans",
    "new york giants": "MetLife Stadium, East Rutherford",
    "new york jets": "MetLife Stadium, East Rutherford",
    "philadelphia eagles": "Lincoln Financial Field, Philadelphia",
    "pittsburgh steelers": "Acrisure Stadium, Pittsburgh",
    "san francisco 49ers": "Levi's Stadium, Santa Clara",
    "seattle seahawks": "Lumen Field, Seattle",
    "tampa bay buccaneers": "Raymond James Stadium, Tampa",
    "tennessee titans": "Nissan Stadium, Nashville",
    "washington commanders": "Northwest Stadium, Landover",
}


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


class AnalyseurLieu(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.textes = []
        self.ignorer = 0

    def handle_starttag(self, balise, attributs):
        if balise in ("script", "style", "noscript"):
            self.ignorer += 1

    def handle_endtag(self, balise):
        if (
            balise in ("script", "style", "noscript")
            and self.ignorer > 0
        ):
            self.ignorer -= 1

    def handle_data(self, donnees):
        if self.ignorer:
            return

        texte = " ".join(donnees.split())

        if texte:
            self.textes.append(texte)


def normaliser_nom(texte):
    return (
        texte
        .strip()
        .casefold()
        .replace("’", "'")
    )


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
                "lieu": None,
                "statut_lieu": None,
            }
        )

    return sorted(
        diffusions,
        key=lambda diffusion: diffusion["debut"],
    )


def est_redzone(titre):
    return "redzone" in re.sub(
        r"[^a-z0-9]",
        "",
        titre.casefold(),
    )


def extraire_equipe_domicile(titre):
    morceaux = re.split(
        r"\s+[–—-]\s+",
        titre,
        maxsplit=1,
    )

    if len(morceaux) != 2:
        return None

    return morceaux[0].strip()


def extraire_lieu_page(page):
    analyseur = AnalyseurLieu()
    analyseur.feed(page)

    textes = analyseur.textes

    for index, texte in enumerate(textes):
        if texte.strip().casefold() not in {
            "lieu",
            "stade",
        }:
            continue

        for suivant in textes[index + 1:]:
            suivant = suivant.strip()

            if not suivant:
                continue

            if suivant.casefold() in {
                "diffusion",
                "avant-match",
                "tendances",
                "compétition",
                "tour",
                "saison",
                "date et heure",
                "calendrier",
            }:
                return None

            return suivant

    return None


def recuperer_lieu_source(url, cache_lieux):
    if not url:
        return None

    if url in cache_lieux:
        return cache_lieux[url]

    try:
        reponse = requests.get(
            url,
            headers=EN_TETES,
            timeout=15,
        )

        reponse.raise_for_status()

        lieu = extraire_lieu_page(
            reponse.text
        )

    except requests.RequestException:
        lieu = None

    cache_lieux[url] = lieu

    return lieu


def determiner_lieu(diffusion, sport, cache_lieux):
    if est_redzone(
        diffusion["titre"]
    ):
        return None, None

    lieu_source = recuperer_lieu_source(
        diffusion["lien"],
        cache_lieux,
    )

    if lieu_source:
        return lieu_source, "source"

    domicile = extraire_equipe_domicile(
        diffusion["titre"]
    )

    if not domicile:
        return None, None

    domicile = normaliser_nom(
        domicile
    )

    if sport["prefixe"] == "MLB":
        lieu = STADES_MLB.get(
            domicile
        )

    else:
        lieu = STADES_NFL.get(
            domicile
        )

    if lieu:
        return lieu, "estimation"

    return None, None


def enrichir_lieux(diffusions, sport):
    cache_lieux = {}

    for diffusion in diffusions:
        lieu, statut_lieu = determiner_lieu(
            diffusion,
            sport,
            cache_lieux,
        )

        diffusion["lieu"] = lieu
        diffusion["statut_lieu"] = statut_lieu

    return diffusions


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
    if (
        sport["prefixe"] == "NFL"
        and est_redzone(
            diffusion["titre"]
        )
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

    lieu = diffusion.get(
        "lieu"
    )

    statut_lieu = diffusion.get(
        "statut_lieu"
    )

    resume = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} — "
        f"{diffusion['titre']}"
    )

    description = (
        f"Diffusion en direct : {chaines}"
    )

    if lieu:
        if statut_lieu == "estimation":
            description += (
                f"\nLieu estimé : {lieu}"
            )
        else:
            description += (
                f"\nLieu : {lieu}"
            )

    elif est_redzone(
        diffusion["titre"]
    ):
        description += (
            "\nLieu : plusieurs matchs simultanés"
        )

    else:
        description += (
            "\nLieu : à confirmer"
        )

    description += (
        f"\nSource : {diffusion['lien']}"
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
    ]

    if lieu:
        lignes.append(
            f"LOCATION:{echapper_ics(lieu)}"
        )

    lignes.extend(
        [
            f"URL:{diffusion['lien']}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]
    )

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
            "Sports — F1 + MLB + NFL"
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

        diffusions = enrichir_lieux(
            diffusions,
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
            ligne = (
                f"  "
                f"{diffusion['debut']:%Y-%m-%d %H:%M} UTC — "
                f"{diffusion['titre']} — "
                f"{' / '.join(diffusion['chaines'])}"
            )

            if diffusion["lieu"]:
                if diffusion["statut_lieu"] == "estimation":
                    ligne += (
                        f" — 📍 {diffusion['lieu']} "
                        f"(estimation)"
                    )
                else:
                    ligne += (
                        f" — 📍 {diffusion['lieu']}"
                    )

            elif est_redzone(
                diffusion["titre"]
            ):
                ligne += (
                    " — 📍 plusieurs matchs"
                )

            else:
                ligne += (
                    " — 📍 lieu à confirmer"
                )

            print(ligne)

    ecrire_calendrier_global()

    print(
        "Calendrier global écrit dans "
        "sports_calendar.ics."
    )


if __name__ == "__main__":
    main()
