import re
import unicodedata
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import requests


EN_TETES = {
    "User-Agent": "Mozilla/5.0 (compatible; SportsCalendarBot/1.0)",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

EN_TETES_TV_PROGRAMME = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

SPORTS = (
    {
        "nom": "MLB sur beIN",
        "prefixe": "MLB",
        "emoji": "⚾",
        "url_ics": "https://tv-sports.fr/calendrier/competition/199/mlb?direct=1",
        "fichier": "mlb_bein_calendar.ics",
        "duree_minutes": 210,
    },
    {
        "nom": "NFL — beIN + Netflix + L'Équipe",
        "prefixe": "NFL",
        "emoji": "🏈",
        "url_ics": "https://tv-sports.fr/calendrier/competition/172/nfl?direct=1",
        "fichier": "nfl_bein_calendar.ics",
        "duree_minutes": 240,
    },
)

NETFLIX_TUDUM_URL = (
    "https://www.netflix.com/tudum/articles/nfl-games-on-netflix"
)

NFL_NETFLIX_WEEK_18_URL = (
    "https://www.nfl.com/schedules/2026/by-week/week-18"
)

NFL_NETFLIX_WEEK_18_DEBUT_UTC = "20270109T180000Z"

NOMS_COURTS_NFL = {
    "Cardinals": "Arizona Cardinals",
    "Falcons": "Atlanta Falcons",
    "Ravens": "Baltimore Ravens",
    "Bills": "Buffalo Bills",
    "Panthers": "Carolina Panthers",
    "Bears": "Chicago Bears",
    "Bengals": "Cincinnati Bengals",
    "Browns": "Cleveland Browns",
    "Cowboys": "Dallas Cowboys",
    "Broncos": "Denver Broncos",
    "Lions": "Detroit Lions",
    "Packers": "Green Bay Packers",
    "Texans": "Houston Texans",
    "Colts": "Indianapolis Colts",
    "Jaguars": "Jacksonville Jaguars",
    "Chiefs": "Kansas City Chiefs",
    "Raiders": "Las Vegas Raiders",
    "Chargers": "Los Angeles Chargers",
    "Rams": "Los Angeles Rams",
    "Dolphins": "Miami Dolphins",
    "Vikings": "Minnesota Vikings",
    "Patriots": "New England Patriots",
    "Saints": "New Orleans Saints",
    "Giants": "New York Giants",
    "Jets": "New York Jets",
    "Eagles": "Philadelphia Eagles",
    "Steelers": "Pittsburgh Steelers",
    "49ers": "San Francisco 49ers",
    "Seahawks": "Seattle Seahawks",
    "Buccaneers": "Tampa Bay Buccaneers",
    "Titans": "Tennessee Titans",
    "Commanders": "Washington Commanders",
}

MATCHS_NETFLIX_NFL = (
    {
        "uid": (
            "nfl-netflix-2026-rams-49ers-melbourne"
            "@sports-us-bein-calendar"
        ),
        "match": "Los Angeles Rams - San Francisco 49ers",
        "debut_utc": "20260911T003500Z",
        "lieu": "Melbourne Cricket Ground, Melbourne",
    },
    {
        "uid": (
            "nfl-netflix-2026-rams-packers"
            "@sports-us-bein-calendar"
        ),
        "match": "Los Angeles Rams - Green Bay Packers",
        "debut_utc": "20261126T010000Z",
        "lieu": "SoFi Stadium, Inglewood",
    },
    {
        "uid": (
            "nfl-netflix-2026-bears-packers"
            "@sports-us-bein-calendar"
        ),
        "match": "Chicago Bears - Green Bay Packers",
        "debut_utc": "20261225T180000Z",
        "lieu": "Soldier Field, Chicago",
    },
    {
        "uid": (
            "nfl-netflix-2026-broncos-bills"
            "@sports-us-bein-calendar"
        ),
        "match": "Denver Broncos - Buffalo Bills",
        "debut_utc": "20261225T213000Z",
        "lieu": "Empower Field at Mile High, Denver",
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

MOIS_URL = {
    1: "janvier",
    2: "fevrier",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "aout",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "decembre",
}

JOURS_URL = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)

PARIS = ZoneInfo("Europe/Paris")


def normaliser_ascii(texte):
    texte = str(texte or "").replace("’", "'")
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )
    return " ".join(texte.casefold().split())


def normaliser_diffuseur(chaine):
    brut = " ".join(unescape(str(chaine or "")).split())
    if not brut:
        return None

    compact = normaliser_ascii(brut)

    if compact.startswith("bein sports"):
        suffixe = brut[len("beIN SPORTS"):].strip()
        if suffixe:
            return "beIN SPORTS " + suffixe
        return "beIN SPORTS"

    if "netflix" in compact:
        return "Netflix"

    if "equipe" in compact:
        if "live" in compact:
            if "foot" in compact:
                return "L'Équipe Live Foot"

            correspondance = re.search(
                r"\blive\s*(\d+)\b",
                compact,
                flags=re.IGNORECASE,
            )
            if correspondance:
                return f"L'Équipe Live {correspondance.group(1)}"

            return "L'Équipe Live"

        if "bouquet" in compact:
            return "Bouquet L'Équipe"

        return "L'Équipe"

    return None


def est_diffuseur_autorise(chaine, sport):
    chaine = normaliser_diffuseur(chaine)
    if not chaine:
        return False

    if sport["prefixe"] == "MLB":
        return chaine.startswith("beIN SPORTS")

    if sport["prefixe"] == "NFL":
        return (
            chaine.startswith("beIN SPORTS")
            or chaine == "Netflix"
            or "L'Équipe" in chaine
        )

    return False


def priorite_diffuseur(chaine):
    if chaine.startswith("beIN SPORTS"):
        return (0, chaine.casefold())
    if chaine == "Netflix":
        return (1, chaine.casefold())
    if chaine == "L'Équipe":
        return (2, chaine.casefold())
    if chaine.startswith("L'Équipe Live"):
        return (3, chaine.casefold())
    if chaine == "Bouquet L'Équipe":
        return (4, chaine.casefold())
    return (9, chaine.casefold())


def normaliser_liste_chaines(chaines, sport):
    resultat = []

    for chaine in chaines:
        canonique = normaliser_diffuseur(chaine)
        if not canonique:
            continue
        if not est_diffuseur_autorise(canonique, sport):
            continue
        if canonique not in resultat:
            resultat.append(canonique)

    if any(
        chaine == "L'Équipe" or chaine.startswith("L'Équipe Live")
        for chaine in resultat
    ):
        resultat = [
            chaine
            for chaine in resultat
            if chaine != "Bouquet L'Équipe"
        ]

    resultat.sort(key=priorite_diffuseur)
    return resultat


class AnalyseurProgrammeTV(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.evenements = []
        self.canal = None
        self.capture_h2 = False
        self.capture_h3 = False
        self.dans_lien_h3 = False
        self.texte_h2 = []
        self.texte_h3 = []
        self.texte_lien_h3 = []
        self.lien_h3 = None
        self.pre_h3 = []
        self.evenement_courant = None
        self.textes_recents = []

    def finaliser_evenement(self):
        if self.evenement_courant is not None:
            self.evenements.append(self.evenement_courant)
            self.evenement_courant = None

    def handle_starttag(self, balise, attributs):
        attributs = dict(attributs)

        if balise == "h2":
            self.finaliser_evenement()
            self.capture_h2 = True
            self.texte_h2 = []
            return

        if balise == "h3":
            self.finaliser_evenement()
            self.capture_h3 = True
            self.texte_h3 = []
            self.texte_lien_h3 = []
            self.lien_h3 = None
            self.pre_h3 = self.textes_recents[-12:]
            return

        if balise == "a" and self.capture_h3:
            self.dans_lien_h3 = True
            href = attributs.get("href", "").strip()
            if href:
                self.lien_h3 = href

    def handle_endtag(self, balise):
        if balise == "a" and self.capture_h3:
            self.dans_lien_h3 = False
            return

        if balise == "h2" and self.capture_h2:
            texte = " ".join(" ".join(self.texte_h2).split())
            canal = normaliser_diffuseur(texte)
            if canal and (
                canal.startswith("beIN SPORTS")
                or "L'Équipe" in canal
            ):
                self.canal = canal
            else:
                self.canal = None

            self.capture_h2 = False
            self.texte_h2 = []
            return

        if balise == "h3" and self.capture_h3:
            titre_lien = " ".join(" ".join(self.texte_lien_h3).split())
            titre_h3 = " ".join(" ".join(self.texte_h3).split())

            self.evenement_courant = {
                "canal": self.canal,
                "titre": titre_lien or titre_h3,
                "href": self.lien_h3,
                "pre": list(self.pre_h3),
                "h3": list(self.texte_h3),
                "post": [],
            }

            self.capture_h3 = False
            self.dans_lien_h3 = False

    def handle_data(self, donnees):
        texte = " ".join(donnees.split())
        if not texte:
            return

        self.textes_recents.append(texte)
        self.textes_recents = self.textes_recents[-60:]

        if self.capture_h2:
            self.texte_h2.append(texte)
            return

        if self.capture_h3:
            self.texte_h3.append(texte)
            if self.dans_lien_h3:
                self.texte_lien_h3.append(texte)
            return

        if self.evenement_courant is not None:
            self.evenement_courant["post"].append(texte)

    def close(self):
        super().close()
        self.finaliser_evenement()


def deplier_ics(texte):
    lignes = texte.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    resultat = []

    for ligne in lignes:
        if ligne.startswith((" ", "\t")) and resultat:
            resultat[-1] += ligne[1:]
        else:
            resultat.append(ligne)

    return resultat


def deschapper_ics(texte):
    resultat = []
    index = 0

    while index < len(texte):
        caractere = texte[index]
        if caractere == "\\" and index + 1 < len(texte):
            suivant = texte[index + 1]
            if suivant in ("n", "N"):
                resultat.append("\n")
            elif suivant in (",", ";", "\\"):
                resultat.append(suivant)
            else:
                resultat.append(suivant)
            index += 2
        else:
            resultat.append(caractere)
            index += 1

    return "".join(resultat)


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
        nouvelle_taille = taille + len(caractere.encode("utf-8"))
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
        morceau, reste = couper_utf8(reste, limite)
        morceaux.append(("" if premier else " ") + morceau)
        premier = False

    return morceaux or [""]


def valeur_propriete(lignes, propriete):
    motif = re.compile(rf"^{re.escape(propriete)}(?:;[^:]*)?:(.*)$")

    for ligne in lignes:
        correspondance = motif.match(ligne)
        if correspondance:
            return correspondance.group(1)

    return None


def extraire_evenements_ics(texte):
    evenements = []
    evenement = None

    for ligne in deplier_ics(texte):
        if ligne == "BEGIN:VEVENT":
            evenement = [ligne]
            continue

        if evenement is None:
            continue

        evenement.append(ligne)
        if ligne == "END:VEVENT":
            evenements.append(evenement)
            evenement = None

    return evenements


def lire_dtstamps_existants(fichier):
    try:
        with open(fichier, encoding="utf-8") as calendrier:
            evenements = extraire_evenements_ics(calendrier.read())
    except OSError:
        return {}

    resultat = {}

    for evenement in evenements:
        uid = valeur_propriete(evenement, "UID")
        dtstamp = valeur_propriete(evenement, "DTSTAMP")
        if uid and dtstamp:
            resultat[uid] = dtstamp

    return resultat


def normaliser_nom(texte):
    return texte.strip().casefold().replace("’", "'")


def formater_match(match):
    return re.sub(r"\s+[–—]\s+", " - ", match.strip())


def est_redzone(titre):
    compact = re.sub(r"[^a-z0-9]", "", (titre or "").casefold())
    return "redzone" in compact


def extraire_infos_description(description):
    if not description:
        return {"match": None, "chaines": []}

    description = deschapper_ics(description)
    premiere_ligne = description.splitlines()[0].strip()
    premiere_ligne = re.sub(r"^\[[^\]]+\]\s*", "", premiere_ligne)

    parties = [
        partie.strip()
        for partie in premiere_ligne.split(" | ")
        if partie.strip()
    ]

    match = parties[0] if parties else None
    chaines = []
    if len(parties) >= 3:
        for partie in parties[2:]:
            morceaux = re.split(r"\s*(?:/|\+|,)\s*", partie)
            chaines.extend(
                morceau.strip()
                for morceau in morceaux
                if morceau.strip()
            )

    return {"match": match, "chaines": chaines}


def extraire_match_ics(evenement):
    infos = extraire_infos_description(
        valeur_propriete(evenement, "DESCRIPTION")
    )

    if infos["match"]:
        return infos["match"]

    summary = valeur_propriete(evenement, "SUMMARY")
    if summary:
        return deschapper_ics(summary).strip()

    return None


def extraire_chaines_ics(evenement, sport):
    infos = extraire_infos_description(
        valeur_propriete(evenement, "DESCRIPTION")
    )
    return normaliser_liste_chaines(infos["chaines"], sport)


def extraire_url_ics(evenement):
    url = valeur_propriete(evenement, "URL")
    if not url:
        return None
    return deschapper_ics(url).strip()


def extraire_lieu_source_ics(evenement):
    lieu = valeur_propriete(evenement, "LOCATION")
    if not lieu:
        return None

    lieu = deschapper_ics(lieu).strip()
    if not lieu:
        return None

    if normaliser_diffuseur(lieu):
        return None

    return lieu


def extraire_equipes_match(match):
    if not match:
        return None, None

    match = formater_match(match)
    morceaux = re.split(r"\s+-\s+", match, maxsplit=1)
    if len(morceaux) != 2:
        return None, None

    return morceaux[0].strip(), morceaux[1].strip()


def extraire_equipe_domicile(match):
    domicile, _ = extraire_equipes_match(match)
    return domicile


def cle_equipes_match(match):
    equipe_1, equipe_2 = extraire_equipes_match(match)
    if not equipe_1 or not equipe_2:
        return None

    return tuple(
        sorted(
            (
                normaliser_nom(equipe_1),
                normaliser_nom(equipe_2),
            )
        )
    )


def stade_estime(match, sport):
    if est_redzone(match):
        return None

    domicile = extraire_equipe_domicile(match)
    if not domicile:
        return None

    domicile = normaliser_nom(domicile)

    if sport["prefixe"] == "MLB":
        return STADES_MLB.get(domicile)

    if sport["prefixe"] == "NFL":
        return STADES_NFL.get(domicile)

    return None


def parse_datetime_ics(valeur):
    if not valeur:
        return None

    formats = (
        "%Y%m%dT%H%M%SZ",
        "%Y%m%dT%H%M%S",
        "%Y%m%dT%H%M",
    )

    for format_date in formats:
        try:
            resultat = datetime.strptime(valeur, format_date)
            return resultat.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def duree_evenement(match, sport):
    if sport["prefixe"] == "NFL" and est_redzone(match):
        return 420
    return sport["duree_minutes"]


def preparer_evenement_ics(evenement, sport, dtstamps_existants):
    match = extraire_match_ics(evenement)
    chaines = extraire_chaines_ics(evenement, sport)
    uid = valeur_propriete(evenement, "UID")
    dtstart = valeur_propriete(evenement, "DTSTART")

    if not match or not chaines or not uid or not dtstart:
        return None

    dtend = valeur_propriete(evenement, "DTEND")
    dtstamp_source = valeur_propriete(evenement, "DTSTAMP")
    dtstamp = (
        dtstamps_existants.get(uid)
        or dtstamp_source
        or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )

    if not dtend:
        debut = parse_datetime_ics(dtstart)
        if debut:
            fin = debut + timedelta(minutes=duree_evenement(match, sport))
            dtend = fin.strftime("%Y%m%dT%H%M%SZ")

    lieu_source = extraire_lieu_source_ics(evenement)

    if est_redzone(match):
        lieu = None
        statut_lieu = "multiple"
    elif lieu_source:
        lieu = lieu_source
        statut_lieu = "source"
    else:
        lieu = stade_estime(match, sport)
        statut_lieu = "estimation" if lieu else None

    return {
        "uid": uid,
        "dtstamp": dtstamp,
        "dtstart": dtstart,
        "dtend": dtend,
        "match": formater_match(match),
        "chaines": chaines,
        "url": extraire_url_ics(evenement),
        "lieu": lieu,
        "statut_lieu": statut_lieu,
    }


def recuperer_evenements_tv_sports(sport, dtstamps_existants):
    reponse = requests.get(
        sport["url_ics"],
        headers=EN_TETES,
        timeout=30,
    )
    reponse.raise_for_status()

    texte = reponse.text
    if "BEGIN:VCALENDAR" not in texte or "BEGIN:VEVENT" not in texte:
        raise RuntimeError(f"Flux ICS {sport['prefixe']} invalide.")

    evenements = []
    for source in extraire_evenements_ics(texte):
        evenement = preparer_evenement_ics(
            source,
            sport,
            dtstamps_existants,
        )
        if evenement:
            evenements.append(evenement)

    return evenements


class AnalyseurTexteNFLNetflix(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.textes = []
        self.ignorer = 0

    def handle_starttag(self, balise, attributs):
        if balise in ("script", "style", "noscript"):
            self.ignorer += 1

    def handle_endtag(self, balise):
        if balise in ("script", "style", "noscript") and self.ignorer > 0:
            self.ignorer -= 1

    def handle_data(self, donnees):
        if self.ignorer:
            return

        texte = " ".join(donnees.split())
        if texte:
            self.textes.append(texte)


def extraire_affiche_netflix_page_nfl(page):
    analyseur = AnalyseurTexteNFLNetflix()
    analyseur.feed(page)
    analyseur.close()

    texte = " ".join(analyseur.textes)
    texte = re.split(
        r"\b20\d{2}\s+TBD Games\b",
        texte,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    alias = dict(NOMS_COURTS_NFL)
    for nom_complet in NOMS_COURTS_NFL.values():
        alias[nom_complet] = nom_complet

    motif_equipe = "|".join(
        re.escape(nom)
        for nom in sorted(alias, key=len, reverse=True)
    )

    motif_match = re.compile(
        rf"(?P<exterieur>{motif_equipe})"
        rf"\s+(?:at|@)\s+"
        rf"(?P<domicile>{motif_equipe})",
        flags=re.IGNORECASE,
    )

    correspondances = list(motif_match.finditer(texte))
    alias_normalises = {
        nom.casefold(): complet
        for nom, complet in alias.items()
    }

    for index, correspondance in enumerate(correspondances):
        fin_bloc = (
            correspondances[index + 1].start()
            if index + 1 < len(correspondances)
            else min(len(texte), correspondance.end() + 500)
        )

        bloc = texte[correspondance.start():fin_bloc]
        if not re.search(r"\bNetflix\b", bloc, flags=re.IGNORECASE):
            continue

        exterieur = alias_normalises[
            correspondance.group("exterieur").casefold()
        ]
        domicile = alias_normalises[
            correspondance.group("domicile").casefold()
        ]
        return f"{domicile} - {exterieur}"

    return None


def recuperer_annonce_netflix_week_18(sport, dtstamps_existants):
    reponse = requests.get(
        NFL_NETFLIX_WEEK_18_URL,
        headers=EN_TETES,
        timeout=30,
    )
    reponse.raise_for_status()

    match = extraire_affiche_netflix_page_nfl(reponse.text)
    if not match:
        return None

    debut = parse_datetime_ics(NFL_NETFLIX_WEEK_18_DEBUT_UTC)
    if not debut:
        return None

    fin = debut + timedelta(minutes=sport["duree_minutes"])
    if fin <= datetime.now(timezone.utc):
        return None

    uid = (
        "nfl-netflix-2026-week18-"
        + re.sub(
            r"[^a-z0-9]+",
            "-",
            normaliser_ascii(match),
        ).strip("-")
        + "@sports-us-bein-calendar"
    )

    return {
        "uid": uid,
        "dtstamp": (
            dtstamps_existants.get(uid)
            or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ),
        "dtstart": debut.strftime("%Y%m%dT%H%M%SZ"),
        "dtend": fin.strftime("%Y%m%dT%H%M%SZ"),
        "match": match,
        "chaines": ["Netflix"],
        "url": NFL_NETFLIX_WEEK_18_URL,
        "lieu": stade_estime(match, sport),
        "statut_lieu": "estimation",
    }


def creer_evenements_netflix_nfl(sport, dtstamps_existants):
    if sport["prefixe"] != "NFL":
        return []

    resultat = []
    maintenant = datetime.now(timezone.utc)

    for source in MATCHS_NETFLIX_NFL:
        debut = parse_datetime_ics(source["debut_utc"])
        if not debut:
            continue

        fin = debut + timedelta(minutes=sport["duree_minutes"])
        if fin <= maintenant:
            continue

        uid = source["uid"]
        dtstamp = (
            dtstamps_existants.get(uid)
            or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )

        resultat.append(
            {
                "uid": uid,
                "dtstamp": dtstamp,
                "dtstart": debut.strftime("%Y%m%dT%H%M%SZ"),
                "dtend": fin.strftime("%Y%m%dT%H%M%SZ"),
                "match": source["match"],
                "chaines": ["Netflix"],
                "url": NETFLIX_TUDUM_URL,
                "lieu": source["lieu"],
                "statut_lieu": "source",
            }
        )

    try:
        annonce_week_18 = recuperer_annonce_netflix_week_18(
            sport,
            dtstamps_existants,
        )
    except requests.RequestException:
        annonce_week_18 = None

    if annonce_week_18:
        resultat.append(annonce_week_18)

    evenements_existants = charger_evenements_existants(
        sport["fichier"],
        sport,
    )

    for existant in evenements_existants:
        if "Netflix" not in existant.get("chaines", []):
            continue

        if any(
            meme_match_nfl(deja_present, existant)
            for deja_present in resultat
        ):
            continue

        resultat.append(existant)

    resultat.sort(key=lambda evenement: evenement["dtstart"])
    return resultat


def memes_equipes(evenement_1, evenement_2):
    cle_1 = cle_equipes_match(evenement_1.get("match"))
    cle_2 = cle_equipes_match(evenement_2.get("match"))
    return cle_1 is not None and cle_1 == cle_2


def meme_match_nfl(evenement_1, evenement_2):
    if est_redzone(evenement_1.get("match")) or est_redzone(
        evenement_2.get("match")
    ):
        return False

    if not memes_equipes(evenement_1, evenement_2):
        return False

    debut_1 = parse_datetime_ics(evenement_1.get("dtstart"))
    debut_2 = parse_datetime_ics(evenement_2.get("dtstart"))
    if debut_1 is None or debut_2 is None:
        return False

    ecart = abs((debut_1 - debut_2).total_seconds())

    # 8 h permet aussi de fusionner une éventuelle diffusion différée
    # L'Équipe avec le direct du même match, sans créer un doublon.
    return ecart <= 8 * 60 * 60


def priorite_lieu(statut):
    return {
        "source": 3,
        "conserve": 2,
        "estimation": 1,
        "multiple": 0,
        None: 0,
    }.get(statut, 0)


def fusionner_deux_evenements_nfl(cible, source, sport):
    cible["chaines"] = normaliser_liste_chaines(
        cible.get("chaines", []) + source.get("chaines", []),
        sport,
    )

    debut_cible = parse_datetime_ics(cible.get("dtstart"))
    debut_source = parse_datetime_ics(source.get("dtstart"))

    # Si une chaîne programme le match en différé, on garde dans le
    # calendrier l'heure la plus tôt, qui correspond au coup d'envoi.
    if (
        debut_source is not None
        and (
            debut_cible is None
            or debut_source < debut_cible
        )
    ):
        cible["dtstart"] = source.get("dtstart")
        if source.get("dtend"):
            cible["dtend"] = source.get("dtend")

    if priorite_lieu(source.get("statut_lieu")) > priorite_lieu(
        cible.get("statut_lieu")
    ):
        cible["lieu"] = source.get("lieu")
        cible["statut_lieu"] = source.get("statut_lieu")

    if not cible.get("url") and source.get("url"):
        cible["url"] = source.get("url")

    return cible


def fusionner_evenements_nfl(groupes, sport):
    resultat = []

    for groupe in groupes:
        for source in groupe:
            correspondant = None

            for existant in resultat:
                if meme_match_nfl(existant, source):
                    correspondant = existant
                    break

            if correspondant is None:
                copie = dict(source)
                copie["chaines"] = normaliser_liste_chaines(
                    copie.get("chaines", []),
                    sport,
                )
                resultat.append(copie)
            else:
                fusionner_deux_evenements_nfl(
                    correspondant,
                    source,
                    sport,
                )

    resultat.sort(key=lambda evenement: evenement["dtstart"])
    return resultat


def slug_date_tv_programme(date):
    return (
        f"{JOURS_URL[date.weekday()]}-"
        f"{date.day}-"
        f"{MOIS_URL[date.month]}-"
        f"{date.year}"
    )


def extraire_heure(pre):
    texte = " ".join(pre)
    correspondances = list(
        re.finditer(r"\b([01]?\d|2[0-3])h([0-5]\d)\b", texte)
    )

    if not correspondances:
        return None

    correspondance = correspondances[-1]
    return int(correspondance.group(1)), int(correspondance.group(2))


def est_evenement_nfl_tv_programme(evenement):
    texte = " ".join(
        [evenement.get("titre", "")]
        + evenement.get("h3", [])
        + evenement.get("post", [])[:8]
    ).casefold()

    return (
        "nfl" in texte
        and (
            "football américain" in texte
            or "football americain" in texte
            or "redzone" in texte
        )
    )


def est_direct_tv_programme(evenement):
    contexte = " ".join(
        evenement.get("h3", [])
        + evenement.get("post", [])[:8]
    )

    return bool(
        re.search(
            r"\bdirect\b",
            contexte,
            flags=re.IGNORECASE,
        )
    )


def nettoyer_titre_nfl_tv_programme(titre):
    titre = " ".join(unescape(titre or "").split())

    if "redzone" in titre.casefold():
        return "NFL RedZone"

    titre = re.sub(
        r"\s+Football américain\b.*$",
        "",
        titre,
        flags=re.IGNORECASE,
    )
    titre = re.sub(
        r"\s+Football americain\b.*$",
        "",
        titre,
        flags=re.IGNORECASE,
    )
    titre = re.sub(
        r"\s+NFL\b.*$",
        "",
        titre,
        flags=re.IGNORECASE,
    )
    titre = re.sub(r"\s*/\s*", " - ", titre)

    return formater_match(titre.strip())


def uid_tv_programme(href, match, date):
    if href:
        correspondance = re.search(r"-e(\d+)", href)
        if correspondance:
            return (
                "nfl-tvp-e"
                + correspondance.group(1)
                + "@sports-us-bein-calendar"
            )

    compact = re.sub(
        r"[^a-z0-9]+",
        "-",
        normaliser_ascii(match),
    ).strip("-")

    return (
        f"nfl-tvp-{date:%Y%m%d}-{compact}"
        f"@sports-us-bein-calendar"
    )


def recuperer_evenements_nfl_tv_programme(
    sport,
    dtstamps_existants,
):
    maintenant_paris = datetime.now(PARIS)
    aujourd_hui = maintenant_paris.date()
    resultat = []
    deja_vus = set()

    # Source complémentaire : elle sert notamment à récupérer une
    # programmation L'Équipe proche du match si le flux TV-Sports
    # n'a pas encore intégré l'information.
    for decalage in range(11):
        date = aujourd_hui + timedelta(days=decalage)
        slug = slug_date_tv_programme(date)
        url = "https://tv-programme.com/" + slug + "/"

        try:
            reponse = requests.get(
                url,
                headers=EN_TETES_TV_PROGRAMME,
                timeout=25,
            )
            reponse.raise_for_status()
        except requests.RequestException as erreur:
            print(
                "    TV-Programme "
                f"{date:%Y-%m-%d} "
                "inaccessible : "
                f"{erreur}"
            )
            continue

        analyseur = AnalyseurProgrammeTV()
        analyseur.feed(reponse.text)
        analyseur.close()

        for source in analyseur.evenements:
            canal = normaliser_diffuseur(source.get("canal", ""))

            if not canal or not est_diffuseur_autorise(canal, sport):
                continue

            if not est_evenement_nfl_tv_programme(source):
                continue

            # On garde le direct quand l'information est disponible.
            # Une diffusion L'Équipe explicitement différée peut malgré
            # tout être récupérée via TV-Sports et fusionnée au direct.
            if not est_direct_tv_programme(source):
                continue

            heure = extraire_heure(source.get("pre", []))
            if not heure:
                continue

            match = nettoyer_titre_nfl_tv_programme(
                source.get("titre", "")
            )
            if not match:
                continue

            debut_local = datetime(
                date.year,
                date.month,
                date.day,
                heure[0],
                heure[1],
                tzinfo=PARIS,
            )
            fin_local = debut_local + timedelta(
                minutes=duree_evenement(match, sport)
            )

            if fin_local <= maintenant_paris:
                continue

            uid = uid_tv_programme(
                source.get("href"),
                match,
                date,
            )

            cle = (uid, debut_local, canal)
            if cle in deja_vus:
                continue
            deja_vus.add(cle)

            if est_redzone(match):
                lieu = None
                statut_lieu = "multiple"
            else:
                lieu = stade_estime(match, sport)
                statut_lieu = "estimation" if lieu else None

            href = source.get("href")
            if href:
                if href.startswith("http"):
                    url_detail = href
                else:
                    url_detail = "https://tv-programme.com" + href
            else:
                url_detail = url

            resultat.append(
                {
                    "uid": uid,
                    "dtstamp": (
                        dtstamps_existants.get(uid)
                        or datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ"
                        )
                    ),
                    "dtstart": debut_local.astimezone(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ"
                    ),
                    "dtend": fin_local.astimezone(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ"
                    ),
                    "match": match,
                    "chaines": [canal],
                    "url": url_detail,
                    "lieu": lieu,
                    "statut_lieu": statut_lieu,
                }
            )

    resultat.sort(key=lambda evenement: evenement["dtstart"])
    return resultat


def extraire_match_calendrier_existant(evenement, sport):
    summary = valeur_propriete(evenement, "SUMMARY")
    if not summary:
        return None

    summary = deschapper_ics(summary).strip()
    prefixe = f"{sport['emoji']} {sport['prefixe']} : "

    if summary.startswith(prefixe):
        return summary[len(prefixe):].strip()

    if ":" in summary:
        return summary.split(":", 1)[1].strip()

    return None


def extraire_chaines_calendrier_existant(evenement, sport):
    description = valeur_propriete(evenement, "DESCRIPTION")
    if not description:
        return []

    description = deschapper_ics(description).strip()
    if not description:
        return []

    chaines = [
        chaine.strip()
        for chaine in re.split(r"\s+(?:\+|/)\s+", description)
        if chaine.strip()
    ]

    return normaliser_liste_chaines(chaines, sport)


def charger_evenements_existants(fichier, sport):
    try:
        with open(fichier, encoding="utf-8") as calendrier:
            sources = extraire_evenements_ics(calendrier.read())
    except OSError:
        return []

    resultat = []
    maintenant = datetime.now(timezone.utc)

    for source in sources:
        uid = valeur_propriete(source, "UID")
        dtstamp = valeur_propriete(source, "DTSTAMP")
        dtstart = valeur_propriete(source, "DTSTART")
        dtend = valeur_propriete(source, "DTEND")
        match = extraire_match_calendrier_existant(source, sport)
        chaines = extraire_chaines_calendrier_existant(source, sport)

        if not uid or not dtstart or not match or not chaines:
            continue

        fin = parse_datetime_ics(dtend or dtstart)
        if fin and fin < maintenant:
            continue

        lieu_brut = valeur_propriete(source, "LOCATION")
        lieu = deschapper_ics(lieu_brut).strip() if lieu_brut else None

        url_brute = valeur_propriete(source, "URL")
        url = deschapper_ics(url_brute).strip() if url_brute else None

        resultat.append(
            {
                "uid": uid,
                "dtstamp": (
                    dtstamp
                    or datetime.now(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ"
                    )
                ),
                "dtstart": dtstart,
                "dtend": dtend,
                "match": match,
                "chaines": chaines,
                "url": url,
                "lieu": lieu,
                "statut_lieu": "conserve" if lieu else None,
            }
        )

    return resultat


def uid_canonique_nfl(evenement):
    cle_equipes = cle_equipes_match(evenement.get("match"))
    debut = parse_datetime_ics(evenement.get("dtstart"))

    if not cle_equipes or not debut:
        return evenement.get("uid")

    equipes = "-".join(
        re.sub(r"[^a-z0-9]+", "-", normaliser_ascii(equipe)).strip("-")
        for equipe in cle_equipes
    )

    return (
        f"nfl-{debut:%Y%m%d}-{equipes}"
        f"@sports-us-bein-calendar"
    )


def stabiliser_identifiants_nfl(evenements, existants):
    maintenant_dtstamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    for evenement in evenements:
        if est_redzone(evenement.get("match")):
            continue

        precedent = None
        for existant in existants:
            if meme_match_nfl(evenement, existant):
                precedent = existant
                break

        if precedent:
            evenement["uid"] = precedent["uid"]
            evenement["dtstamp"] = precedent.get("dtstamp") or maintenant_dtstamp
        else:
            evenement["uid"] = uid_canonique_nfl(evenement)
            evenement["dtstamp"] = evenement.get("dtstamp") or maintenant_dtstamp


def construire_evenement(evenement, sport):
    chaines = " + ".join(evenement["chaines"])
    resume = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} : "
        f"{formater_match(evenement['match'])}"
    )

    lignes = [
        "BEGIN:VEVENT",
        f"UID:{evenement['uid']}",
        f"DTSTAMP:{evenement['dtstamp']}",
        f"DTSTART:{evenement['dtstart']}",
    ]

    if evenement.get("dtend"):
        lignes.append(f"DTEND:{evenement['dtend']}")

    lignes.extend(
        [
            "SUMMARY:" + echapper_ics(resume),
            "DESCRIPTION:" + echapper_ics(chaines),
        ]
    )

    lieu = evenement.get("lieu")
    if lieu:
        lignes.append("LOCATION:" + echapper_ics(lieu))

    if evenement.get("url"):
        lignes.append(f"URL:{evenement['url']}")

    lignes.extend(
        [
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]
    )

    return lignes


def ecrire_calendrier(evenements, sport):
    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//sports-us-bein-calendar//"
        f"{sport['prefixe']}//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + echapper_ics(sport["nom"]),
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for evenement in evenements:
        lignes.extend(construire_evenement(evenement, sport))

    lignes.append("END:VCALENDAR")

    lignes_pliees = []
    for ligne in lignes:
        lignes_pliees.extend(plier_ligne_ics(ligne))

    with open(
        sport["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write("\r\n".join(lignes_pliees) + "\r\n")


def afficher_evenements(evenements):
    for evenement in evenements:
        ligne = (
            "  "
            + formater_match(evenement["match"])
            + " — "
            + " + ".join(evenement["chaines"])
        )

        if evenement.get("lieu"):
            ligne += " — 📍 " + evenement["lieu"]
            if evenement.get("statut_lieu") == "estimation":
                ligne += " (estimation)"
        elif evenement.get("statut_lieu") == "multiple":
            ligne += " — 📍 plusieurs matchs"
        else:
            ligne += " — 📍 lieu à confirmer"

        print(ligne)


def traiter_sport(sport):
    print(f"Téléchargement de {sport['nom']}…")

    dtstamps_existants = lire_dtstamps_existants(sport["fichier"])
    evenements_existants = charger_evenements_existants(
        sport["fichier"],
        sport,
    )

    evenements_tv_sports = []
    source_tv_sports_ok = False
    sources_utilisees = []

    try:
        evenements_tv_sports = recuperer_evenements_tv_sports(
            sport,
            dtstamps_existants,
        )
        source_tv_sports_ok = True
        if evenements_tv_sports:
            sources_utilisees.append("TV-Sports ICS")
    except requests.HTTPError as erreur:
        code = (
            erreur.response.status_code
            if erreur.response is not None
            else "?"
        )
        print(
            "  Flux TV-Sports ICS indisponible "
            f"(HTTP {code})."
        )
    except (requests.RequestException, RuntimeError) as erreur:
        print(
            "  Flux TV-Sports ICS indisponible : "
            f"{erreur}"
        )

    if sport["prefixe"] == "NFL":
        evenements_tv_programme = []
        source_tv_programme_ok = False

        print(
            "  Vérification complémentaire NFL "
            "sur TV-Programme.com (beIN + L'Équipe)…"
        )

        try:
            evenements_tv_programme = (
                recuperer_evenements_nfl_tv_programme(
                    sport,
                    dtstamps_existants,
                )
            )
            source_tv_programme_ok = True
            if evenements_tv_programme:
                sources_utilisees.append("TV-Programme.com")
        except (requests.RequestException, RuntimeError) as erreur:
            print(
                "  AVERTISSEMENT : "
                "source complémentaire NFL impossible : "
                f"{erreur}"
            )

        evenements_netflix = creer_evenements_netflix_nfl(
            sport,
            dtstamps_existants,
        )

        print(
            f"  {len(evenements_netflix)} "
            "match(s) NFL Netflix "
            "officiellement annoncé(s) "
            "encore à venir."
        )

        if evenements_netflix:
            sources_utilisees.append("Netflix")

        if not evenements_tv_sports and not evenements_tv_programme:
            if evenements_existants:
                print(
                    "  Sources de programmation NFL "
                    "indisponibles ou vides : "
                    "conservation des événements "
                    "existants en secours."
                )

                evenements_sources = [
                    evenements_existants,
                    evenements_netflix,
                ]
                sources_utilisees.append("Calendrier existant")
            else:
                evenements_sources = [evenements_netflix]
        else:
            evenements_sources = [
                evenements_tv_sports,
                evenements_tv_programme,
                evenements_netflix,
            ]

        evenements = fusionner_evenements_nfl(
            evenements_sources,
            sport,
        )

        stabiliser_identifiants_nfl(
            evenements,
            evenements_existants,
        )

        # Les variables sont gardées pour distinguer un vrai échec réseau
        # d'un flux valide qui n'a simplement aucune affiche à ce moment-là.
        _ = source_tv_sports_ok, source_tv_programme_ok

    else:
        evenements = evenements_tv_sports

    if not evenements:
        print(
            "  AVERTISSEMENT : "
            "aucune diffusion "
            f"{sport['prefixe']} récupérée."
        )
        print(
            "  Le fichier "
            f"{sport['fichier']} "
            "existant est conservé."
        )
        return False

    ecrire_calendrier(evenements, sport)

    print(
        f"{len(evenements)} "
        "diffusion(s) écrite(s) "
        "dans "
        f"{sport['fichier']}."
    )

    sources_uniques = []
    for source in sources_utilisees:
        if source not in sources_uniques:
            sources_uniques.append(source)

    print(
        "  Source(s) utilisée(s) : "
        + (
            " + ".join(sources_uniques)
            if sources_uniques
            else "aucune source nommée"
        )
    )

    afficher_evenements(evenements)

    if sport["prefixe"] == "NFL":
        week_18_trouvee = any(
            "nfl-netflix-2026-week18-" in evenement.get("uid", "")
            or (
                "Netflix" in evenement.get("chaines", [])
                and evenement.get("dtstart", "").startswith("20270109")
            )
            for evenement in evenements
        )

        if week_18_trouvee:
            print(
                "  Week 18 Netflix (09/01/2027) : "
                "affiche officielle ajoutée automatiquement."
            )
        else:
            print(
                "  Week 18 Netflix (09/01/2027) : "
                "affiche encore à confirmer, "
                "donc non ajoutée pour éviter "
                "d'inventer un match."
            )

        matchs_lequipe = [
            evenement
            for evenement in evenements
            if any(
                "L'Équipe" in chaine
                for chaine in evenement.get("chaines", [])
            )
        ]

        print(
            f"  {len(matchs_lequipe)} "
            "match(s) NFL L'Équipe détecté(s) "
            "dans les programmations disponibles."
        )

    return True


def extraire_vevents(fichier):
    evenements = []
    evenement = None

    with open(fichier, encoding="utf-8") as calendrier:
        for ligne in calendrier:
            ligne = ligne.rstrip("\r\n")

            if ligne == "BEGIN:VEVENT":
                evenement = [ligne]
            elif evenement is not None:
                evenement.append(ligne)
                if ligne == "END:VEVENT":
                    evenements.extend(evenement)
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
        "PRODID:-//sports-us-bein-calendar//Tous les sports//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Sports — F1 + MLB + NFL",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for fichier in fichiers:
        lignes.extend(extraire_vevents(fichier))

    lignes.append("END:VCALENDAR")

    with open(
        "sports_calendar.ics",
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write("\r\n".join(lignes) + "\r\n")


def main():
    for sport in SPORTS:
        traiter_sport(sport)

    ecrire_calendrier_global()
    print("Calendrier global écrit dans sports_calendar.ics.")


if __name__ == "__main__":
    main()

