import re
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
        "url_ics": (
            "https://tv-sports.fr/"
            "calendrier/competition/199/mlb?direct=1"
        ),
        "fichier": "mlb_bein_calendar.ics",
        "duree_minutes": 210,
    },
    {
        "nom": "NFL — beIN + Netflix",
        "prefixe": "NFL",
        "emoji": "🏈",
        "url_ics": (
            "https://tv-sports.fr/"
            "calendrier/competition/172/nfl?direct=1"
        ),
        "fichier": "nfl_bein_calendar.ics",
        "duree_minutes": 240,
    },
)


NETFLIX_TUDUM_URL = (
    "https://www.netflix.com/tudum/"
    "articles/nfl-games-on-netflix"
)


# Matchs NFL Netflix 2026 déjà officiellement annoncés.
#
# Les horaires ci-dessous sont stockés en UTC.
#
# Le cinquième match Netflix, en Week 18 le 9 janvier 2027,
# n'est volontairement PAS ajouté tant que l'affiche n'est
# pas officiellement déterminée.
MATCHS_NETFLIX_NFL = (
    {
        "uid": (
            "nfl-netflix-2026-rams-49ers-melbourne"
            "@sports-us-bein-calendar"
        ),
        "match": (
            "Los Angeles Rams - San Francisco 49ers"
        ),
        "debut_utc": "20260911T003500Z",
        "lieu": (
            "Melbourne Cricket Ground, Melbourne"
        ),
    },
    {
        "uid": (
            "nfl-netflix-2026-rams-packers"
            "@sports-us-bein-calendar"
        ),
        "match": (
            "Los Angeles Rams - Green Bay Packers"
        ),
        "debut_utc": "20261126T010000Z",
        "lieu": (
            "SoFi Stadium, Inglewood"
        ),
    },
    {
        "uid": (
            "nfl-netflix-2026-bears-packers"
            "@sports-us-bein-calendar"
        ),
        "match": (
            "Chicago Bears - Green Bay Packers"
        ),
        "debut_utc": "20261225T180000Z",
        "lieu": (
            "Soldier Field, Chicago"
        ),
    },
    {
        "uid": (
            "nfl-netflix-2026-broncos-bills"
            "@sports-us-bein-calendar"
        ),
        "match": (
            "Denver Broncos - Buffalo Bills"
        ),
        "debut_utc": "20261225T213000Z",
        "lieu": (
            "Empower Field at Mile High, Denver"
        ),
    },
)


STADES_MLB = {
    "arizona diamondbacks":
        "Chase Field, Phoenix",

    "athletics":
        "Sutter Health Park, West Sacramento",

    "oakland athletics":
        "Sutter Health Park, West Sacramento",

    "atlanta braves":
        "Truist Park, Atlanta",

    "baltimore orioles":
        "Oriole Park at Camden Yards, Baltimore",

    "boston red sox":
        "Fenway Park, Boston",

    "chicago cubs":
        "Wrigley Field, Chicago",

    "chicago white sox":
        "Rate Field, Chicago",

    "cincinnati reds":
        "Great American Ball Park, Cincinnati",

    "cleveland guardians":
        "Progressive Field, Cleveland",

    "colorado rockies":
        "Coors Field, Denver",

    "detroit tigers":
        "Comerica Park, Detroit",

    "houston astros":
        "Daikin Park, Houston",

    "kansas city royals":
        "Kauffman Stadium, Kansas City",

    "los angeles angels":
        "Angel Stadium, Anaheim",

    "los angeles dodgers":
        "Dodger Stadium, Los Angeles",

    "miami marlins":
        "loanDepot park, Miami",

    "milwaukee brewers":
        "American Family Field, Milwaukee",

    "minnesota twins":
        "Target Field, Minneapolis",

    "new york mets":
        "Citi Field, New York",

    "new york yankees":
        "Yankee Stadium, New York",

    "philadelphia phillies":
        "Citizens Bank Park, Philadelphia",

    "pittsburgh pirates":
        "PNC Park, Pittsburgh",

    "san diego padres":
        "Petco Park, San Diego",

    "san francisco giants":
        "Oracle Park, San Francisco",

    "seattle mariners":
        "T-Mobile Park, Seattle",

    "st louis cardinals":
        "Busch Stadium, St. Louis",

    "st. louis cardinals":
        "Busch Stadium, St. Louis",

    "tampa bay rays":
        "Tropicana Field, St. Petersburg",

    "texas rangers":
        "Globe Life Field, Arlington",

    "toronto blue jays":
        "Rogers Centre, Toronto",

    "washington nationals":
        "Nationals Park, Washington",
}


STADES_NFL = {
    "arizona cardinals":
        "State Farm Stadium, Glendale",

    "atlanta falcons":
        "Mercedes-Benz Stadium, Atlanta",

    "baltimore ravens":
        "M&T Bank Stadium, Baltimore",

    "buffalo bills":
        "Highmark Stadium, Orchard Park",

    "carolina panthers":
        "Bank of America Stadium, Charlotte",

    "chicago bears":
        "Soldier Field, Chicago",

    "cincinnati bengals":
        "Paycor Stadium, Cincinnati",

    "cleveland browns":
        "Huntington Bank Field, Cleveland",

    "dallas cowboys":
        "AT&T Stadium, Arlington",

    "denver broncos":
        "Empower Field at Mile High, Denver",

    "detroit lions":
        "Ford Field, Detroit",

    "green bay packers":
        "Lambeau Field, Green Bay",

    "houston texans":
        "NRG Stadium, Houston",

    "indianapolis colts":
        "Lucas Oil Stadium, Indianapolis",

    "jacksonville jaguars":
        "EverBank Stadium, Jacksonville",

    "kansas city chiefs":
        "GEHA Field at Arrowhead Stadium, Kansas City",

    "las vegas raiders":
        "Allegiant Stadium, Las Vegas",

    "los angeles chargers":
        "SoFi Stadium, Inglewood",

    "los angeles rams":
        "SoFi Stadium, Inglewood",

    "miami dolphins":
        "Hard Rock Stadium, Miami Gardens",

    "minnesota vikings":
        "U.S. Bank Stadium, Minneapolis",

    "new england patriots":
        "Gillette Stadium, Foxborough",

    "new orleans saints":
        "Caesars Superdome, New Orleans",

    "new york giants":
        "MetLife Stadium, East Rutherford",

    "new york jets":
        "MetLife Stadium, East Rutherford",

    "philadelphia eagles":
        "Lincoln Financial Field, Philadelphia",

    "pittsburgh steelers":
        "Acrisure Stadium, Pittsburgh",

    "san francisco 49ers":
        "Levi's Stadium, Santa Clara",

    "seattle seahawks":
        "Lumen Field, Seattle",

    "tampa bay buccaneers":
        "Raymond James Stadium, Tampa",

    "tennessee titans":
        "Nissan Stadium, Nashville",

    "washington commanders":
        "Northwest Stadium, Landover",
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


PARIS = ZoneInfo(
    "Europe/Paris"
)


class AnalyseurProgrammeTV(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

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

    def finaliser_evenement(
        self,
    ):
        if (
            self.evenement_courant
            is not None
        ):
            self.evenements.append(
                self.evenement_courant
            )

            self.evenement_courant = (
                None
            )

    def handle_starttag(
        self,
        balise,
        attributs,
    ):
        attributs = dict(
            attributs
        )

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

            self.pre_h3 = (
                self.textes_recents[
                    -12:
                ]
            )

            return

        if (
            balise == "a"
            and self.capture_h3
        ):
            self.dans_lien_h3 = (
                True
            )

            href = (
                attributs
                .get(
                    "href",
                    "",
                )
                .strip()
            )

            if href:
                self.lien_h3 = (
                    href
                )

    def handle_endtag(
        self,
        balise,
    ):
        if (
            balise == "a"
            and self.capture_h3
        ):
            self.dans_lien_h3 = (
                False
            )

            return

        if (
            balise == "h2"
            and self.capture_h2
        ):
            texte = " ".join(
                " ".join(
                    self.texte_h2
                ).split()
            )

            if (
                texte
                .casefold()
                .startswith(
                    "bein sports"
                )
            ):
                self.canal = texte

            else:
                self.canal = None

            self.capture_h2 = False
            self.texte_h2 = []

            return

        if (
            balise == "h3"
            and self.capture_h3
        ):
            titre_lien = " ".join(
                " ".join(
                    self.texte_lien_h3
                ).split()
            )

            titre_h3 = " ".join(
                " ".join(
                    self.texte_h3
                ).split()
            )

            self.evenement_courant = {
                "canal": self.canal,
                "titre": (
                    titre_lien
                    or titre_h3
                ),
                "href": self.lien_h3,
                "pre": list(
                    self.pre_h3
                ),
                "h3": list(
                    self.texte_h3
                ),
                "post": [],
            }

            self.capture_h3 = False
            self.dans_lien_h3 = False

    def handle_data(
        self,
        donnees,
    ):
        texte = " ".join(
            donnees.split()
        )

        if not texte:
            return

        self.textes_recents.append(
            texte
        )

        self.textes_recents = (
            self.textes_recents[
                -60:
            ]
        )

        if self.capture_h2:
            self.texte_h2.append(
                texte
            )

            return

        if self.capture_h3:
            self.texte_h3.append(
                texte
            )

            if self.dans_lien_h3:
                self.texte_lien_h3.append(
                    texte
                )

            return

        if (
            self.evenement_courant
            is not None
        ):
            self.evenement_courant[
                "post"
            ].append(
                texte
            )

    def close(
        self,
    ):
        super().close()

        self.finaliser_evenement()


def deplier_ics(
    texte,
):
    lignes = (
        texte
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .split("\n")
    )

    resultat = []

    for ligne in lignes:
        if (
            ligne.startswith(
                (" ", "\t")
            )
            and resultat
        ):
            resultat[-1] += (
                ligne[1:]
            )

        else:
            resultat.append(
                ligne
            )

    return resultat


def deschapper_ics(
    texte,
):
    resultat = []
    index = 0

    while index < len(texte):
        caractere = texte[index]

        if (
            caractere == "\\"
            and index + 1 < len(texte)
        ):
            suivant = texte[
                index + 1
            ]

            if suivant in (
                "n",
                "N",
            ):
                resultat.append(
                    "\n"
                )

            elif suivant in (
                ",",
                ";",
                "\\",
            ):
                resultat.append(
                    suivant
                )

            else:
                resultat.append(
                    suivant
                )

            index += 2

        else:
            resultat.append(
                caractere
            )

            index += 1

    return "".join(
        resultat
    )


def echapper_ics(
    texte,
):
    return (
        str(texte)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def couper_utf8(
    texte,
    limite,
):
    taille = 0
    position = 0

    for caractere in texte:
        nouvelle_taille = (
            taille
            + len(
                caractere.encode(
                    "utf-8"
                )
            )
        )

        if nouvelle_taille > limite:
            break

        taille = nouvelle_taille
        position += 1

    return (
        texte[:position],
        texte[position:],
    )


def plier_ligne_ics(
    ligne,
):
    morceaux = []
    reste = ligne
    premier = True

    while reste:
        limite = (
            75
            if premier
            else 74
        )

        morceau, reste = (
            couper_utf8(
                reste,
                limite,
            )
        )

        morceaux.append(
            (
                ""
                if premier
                else " "
            )
            + morceau
        )

        premier = False

    return morceaux or [""]


def valeur_propriete(
    lignes,
    propriete,
):
    motif = re.compile(
        rf"^{re.escape(propriete)}"
        rf"(?:;[^:]*)?:(.*)$"
    )

    for ligne in lignes:
        correspondance = (
            motif.match(
                ligne
            )
        )

        if correspondance:
            return (
                correspondance
                .group(1)
            )

    return None


def extraire_evenements_ics(
    texte,
):
    evenements = []
    evenement = None

    for ligne in deplier_ics(
        texte
    ):
        if (
            ligne
            == "BEGIN:VEVENT"
        ):
            evenement = [
                ligne
            ]

            continue

        if evenement is None:
            continue

        evenement.append(
            ligne
        )

        if (
            ligne
            == "END:VEVENT"
        ):
            evenements.append(
                evenement
            )

            evenement = None

    return evenements


def lire_dtstamps_existants(
    fichier,
):
    try:
        with open(
            fichier,
            encoding="utf-8",
        ) as calendrier:
            evenements = (
                extraire_evenements_ics(
                    calendrier.read()
                )
            )

    except OSError:
        return {}

    resultat = {}

    for evenement in evenements:
        uid = valeur_propriete(
            evenement,
            "UID",
        )

        dtstamp = valeur_propriete(
            evenement,
            "DTSTAMP",
        )

        if uid and dtstamp:
            resultat[
                uid
            ] = dtstamp

    return resultat


def normaliser_nom(
    texte,
):
    return (
        texte
        .strip()
        .casefold()
        .replace("’", "'")
    )


def formater_match(
    match,
):
    return re.sub(
        r"\s+[–—]\s+",
        " - ",
        match.strip(),
    )


def est_redzone(
    titre,
):
    compact = re.sub(
        r"[^a-z0-9]",
        "",
        (
            titre
            or ""
        ).casefold(),
    )

    return (
        "redzone"
        in compact
    )


def extraire_infos_description(
    description,
):
    if not description:
        return {
            "match": None,
            "chaines": [],
        }

    description = (
        deschapper_ics(
            description
        )
    )

    premiere_ligne = (
        description
        .splitlines()[0]
        .strip()
    )

    premiere_ligne = re.sub(
        r"^\[[^\]]+\]\s*",
        "",
        premiere_ligne,
    )

    parties = [
        partie.strip()
        for partie
        in premiere_ligne.split(
            " | "
        )
        if partie.strip()
    ]

    match = (
        parties[0]
        if parties
        else None
    )

    chaines = []

    if len(parties) >= 3:
        for partie in parties[
            2:
        ]:
            if (
                partie
                .casefold()
                .startswith(
                    "bein sports"
                )
                and partie
                not in chaines
            ):
                chaines.append(
                    partie
                )

    return {
        "match": match,
        "chaines": chaines,
    }


def extraire_match_ics(
    evenement,
):
    infos = (
        extraire_infos_description(
            valeur_propriete(
                evenement,
                "DESCRIPTION",
            )
        )
    )

    if infos["match"]:
        return infos[
            "match"
        ]

    summary = valeur_propriete(
        evenement,
        "SUMMARY",
    )

    if summary:
        return (
            deschapper_ics(
                summary
            )
            .strip()
        )

    return None


def extraire_chaines_ics(
    evenement,
):
    infos = (
        extraire_infos_description(
            valeur_propriete(
                evenement,
                "DESCRIPTION",
            )
        )
    )

    return infos[
        "chaines"
    ]


def extraire_url_ics(
    evenement,
):
    url = valeur_propriete(
        evenement,
        "URL",
    )

    if not url:
        return None

    return (
        deschapper_ics(
            url
        )
        .strip()
    )


def extraire_lieu_source_ics(
    evenement,
):
    lieu = valeur_propriete(
        evenement,
        "LOCATION",
    )

    if not lieu:
        return None

    lieu = (
        deschapper_ics(
            lieu
        )
        .strip()
    )

    if not lieu:
        return None

    if (
        lieu
        .casefold()
        .startswith(
            "bein sports"
        )
    ):
        return None

    return lieu


def extraire_equipes_match(
    match,
):
    if not match:
        return (
            None,
            None,
        )

    match = formater_match(
        match
    )

    morceaux = re.split(
        r"\s+-\s+",
        match,
        maxsplit=1,
    )

    if len(morceaux) != 2:
        return (
            None,
            None,
        )

    return (
        morceaux[0].strip(),
        morceaux[1].strip(),
    )


def extraire_equipe_domicile(
    match,
):
    domicile, _ = (
        extraire_equipes_match(
            match
        )
    )

    return domicile


def cle_equipes_match(
    match,
):
    equipe_1, equipe_2 = (
        extraire_equipes_match(
            match
        )
    )

    if (
        not equipe_1
        or not equipe_2
    ):
        return None

    equipes = sorted(
        (
            normaliser_nom(
                equipe_1
            ),
            normaliser_nom(
                equipe_2
            ),
        )
    )

    return tuple(
        equipes
    )


def stade_estime(
    match,
    sport,
):
    if est_redzone(
        match
    ):
        return None

    domicile = (
        extraire_equipe_domicile(
            match
        )
    )

    if not domicile:
        return None

    domicile = (
        normaliser_nom(
            domicile
        )
    )

    if (
        sport["prefixe"]
        == "MLB"
    ):
        return (
            STADES_MLB.get(
                domicile
            )
        )

    if (
        sport["prefixe"]
        == "NFL"
    ):
        return (
            STADES_NFL.get(
                domicile
            )
        )

    return None


def parse_datetime_ics(
    valeur,
):
    if not valeur:
        return None

    formats = (
        "%Y%m%dT%H%M%SZ",
        "%Y%m%dT%H%M%S",
        "%Y%m%dT%H%M",
    )

    for format_date in formats:
        try:
            resultat = (
                datetime.strptime(
                    valeur,
                    format_date,
                )
            )

            return resultat.replace(
                tzinfo=timezone.utc
            )

        except ValueError:
            continue

    return None


def duree_evenement(
    match,
    sport,
):
    if (
        sport["prefixe"]
        == "NFL"
        and est_redzone(
            match
        )
    ):
        return 420

    return sport[
        "duree_minutes"
    ]


def preparer_evenement_ics(
    evenement,
    sport,
    dtstamps_existants,
):
    match = (
        extraire_match_ics(
            evenement
        )
    )

    chaines = (
        extraire_chaines_ics(
            evenement
        )
    )

    uid = valeur_propriete(
        evenement,
        "UID",
    )

    dtstart = valeur_propriete(
        evenement,
        "DTSTART",
    )

    if (
        not match
        or not chaines
        or not uid
        or not dtstart
    ):
        return None

    dtend = valeur_propriete(
        evenement,
        "DTEND",
    )

    dtstamp_source = (
        valeur_propriete(
            evenement,
            "DTSTAMP",
        )
    )

    dtstamp = (
        dtstamps_existants.get(
            uid
        )
        or dtstamp_source
        or datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )

    if not dtend:
        debut = (
            parse_datetime_ics(
                dtstart
            )
        )

        if debut:
            fin = (
                debut
                + timedelta(
                    minutes=duree_evenement(
                        match,
                        sport,
                    )
                )
            )

            dtend = (
                fin.strftime(
                    "%Y%m%dT%H%M%SZ"
                )
            )

    lieu_source = (
        extraire_lieu_source_ics(
            evenement
        )
    )

    if est_redzone(
        match
    ):
        lieu = None
        statut_lieu = "multiple"

    elif lieu_source:
        lieu = lieu_source
        statut_lieu = "source"

    else:
        lieu = stade_estime(
            match,
            sport,
        )

        statut_lieu = (
            "estimation"
            if lieu
            else None
        )

    return {
        "uid": uid,
        "dtstamp": dtstamp,
        "dtstart": dtstart,
        "dtend": dtend,
        "match": formater_match(
            match
        ),
        "chaines": chaines,
        "url": (
            extraire_url_ics(
                evenement
            )
        ),
        "lieu": lieu,
        "statut_lieu": statut_lieu,
    }


def recuperer_evenements_tv_sports(
    sport,
    dtstamps_existants,
):
    reponse = requests.get(
        sport["url_ics"],
        headers=EN_TETES,
        timeout=30,
    )

    reponse.raise_for_status()

    texte = reponse.text

    if (
        "BEGIN:VCALENDAR"
        not in texte
        or "BEGIN:VEVENT"
        not in texte
    ):
        raise RuntimeError(
            f"Flux ICS "
            f"{sport['prefixe']} "
            f"invalide."
        )

    evenements = []

    for source in (
        extraire_evenements_ics(
            texte
        )
    ):
        evenement = (
            preparer_evenement_ics(
                source,
                sport,
                dtstamps_existants,
            )
        )

        if evenement:
            evenements.append(
                evenement
            )

    return evenements


def creer_evenements_netflix_nfl(
    sport,
    dtstamps_existants,
):
    if (
        sport["prefixe"]
        != "NFL"
    ):
        return []

    resultat = []

    maintenant = datetime.now(
        timezone.utc
    )

    for source in MATCHS_NETFLIX_NFL:
        debut = parse_datetime_ics(
            source["debut_utc"]
        )

        if not debut:
            continue

        fin = debut + timedelta(
            minutes=sport[
                "duree_minutes"
            ]
        )

        if fin <= maintenant:
            continue

        uid = source[
            "uid"
        ]

        dtstamp = (
            dtstamps_existants.get(
                uid
            )
            or datetime.now(
                timezone.utc
            ).strftime(
                "%Y%m%dT%H%M%SZ"
            )
        )

        resultat.append(
            {
                "uid": uid,
                "dtstamp": dtstamp,
                "dtstart": (
                    debut.strftime(
                        "%Y%m%dT%H%M%SZ"
                    )
                ),
                "dtend": (
                    fin.strftime(
                        "%Y%m%dT%H%M%SZ"
                    )
                ),
                "match": source[
                    "match"
                ],
                "chaines": [
                    "Netflix"
                ],
                "url": (
                    NETFLIX_TUDUM_URL
                ),
                "lieu": source[
                    "lieu"
                ],
                "statut_lieu": (
                    "source"
                ),
            }
        )

    return resultat


def memes_equipes(
    evenement_1,
    evenement_2,
):
    cle_1 = cle_equipes_match(
        evenement_1.get(
            "match"
        )
    )

    cle_2 = cle_equipes_match(
        evenement_2.get(
            "match"
        )
    )

    return (
        cle_1 is not None
        and cle_1 == cle_2
    )


def meme_match_nfl(
    evenement_1,
    evenement_2,
):
    if not memes_equipes(
        evenement_1,
        evenement_2,
    ):
        return False

    debut_1 = parse_datetime_ics(
        evenement_1.get(
            "dtstart"
        )
    )

    debut_2 = parse_datetime_ics(
        evenement_2.get(
            "dtstart"
        )
    )

    if (
        debut_1 is None
        or debut_2 is None
    ):
        return False

    ecart = abs(
        (
            debut_1
            - debut_2
        ).total_seconds()
    )

    # Une petite tolérance évite un doublon
    # si deux sources indiquent légèrement
    # différemment l'heure de début.
    return (
        ecart
        <= 6 * 60 * 60
    )


def fusionner_evenements_nfl(
    evenements_bein,
    evenements_netflix,
):
    resultat = [
        dict(
            evenement
        )
        for evenement
        in evenements_bein
    ]

    for netflix in (
        evenements_netflix
    ):
        correspondant = None

        for existant in resultat:
            if meme_match_nfl(
                existant,
                netflix,
            ):
                correspondant = (
                    existant
                )

                break

        if correspondant is None:
            resultat.append(
                dict(
                    netflix
                )
            )

            continue

        if (
            "Netflix"
            not in correspondant[
                "chaines"
            ]
        ):
            correspondant[
                "chaines"
            ].append(
                "Netflix"
            )

        # Les matchs Netflix ont un UID stable
        # indépendant du diffuseur.
        #
        # Ainsi, si un match est d'abord Netflix
        # uniquement puis apparaît plus tard sur beIN,
        # Apple conserve le même événement au lieu
        # d'en créer un second.
        correspondant[
            "uid"
        ] = netflix[
            "uid"
        ]

        correspondant[
            "dtstamp"
        ] = netflix[
            "dtstamp"
        ]

        # Pour les matchs Netflix, le lieu ici vient
        # d'une annonce officielle.
        #
        # C'est notamment indispensable pour le match
        # Rams - 49ers joué à Melbourne : il ne faut
        # surtout pas utiliser SoFi Stadium simplement
        # parce que les Rams sont l'équipe "à domicile".
        if (
            netflix.get(
                "lieu"
            )
            and (
                not correspondant.get(
                    "lieu"
                )
                or correspondant.get(
                    "statut_lieu"
                )
                == "estimation"
            )
        ):
            correspondant[
                "lieu"
            ] = netflix[
                "lieu"
            ]

            correspondant[
                "statut_lieu"
            ] = "source"

    resultat.sort(
        key=lambda evenement:
        evenement[
            "dtstart"
        ]
    )

    return resultat


def slug_date_tv_programme(
    date,
):
    return (
        f"{JOURS_URL[date.weekday()]}-"
        f"{date.day}-"
        f"{MOIS_URL[date.month]}-"
        f"{date.year}"
    )


def extraire_heure(
    pre,
):
    texte = " ".join(
        pre
    )

    correspondances = list(
        re.finditer(
            r"\b([01]?\d|2[0-3])"
            r"h([0-5]\d)\b",
            texte,
        )
    )

    if not correspondances:
        return None

    correspondance = (
        correspondances[-1]
    )

    return (
        int(
            correspondance.group(1)
        ),
        int(
            correspondance.group(2)
        ),
    )


def est_evenement_nfl_tv_programme(
    evenement,
):
    texte = " ".join(
        [
            evenement.get(
                "titre",
                "",
            )
        ]
        + evenement.get(
            "h3",
            [],
        )
        + evenement.get(
            "post",
            [],
        )[:8]
    ).casefold()

    return (
        "nfl" in texte
        and (
            "football américain"
            in texte
            or "football americain"
            in texte
            or "redzone"
            in texte
        )
    )


def est_direct_tv_programme(
    evenement,
):
    contexte = " ".join(
        evenement.get(
            "h3",
            [],
        )
        + evenement.get(
            "post",
            [],
        )[:8]
    )

    return bool(
        re.search(
            r"\bdirect\b",
            contexte,
            flags=re.IGNORECASE,
        )
    )


def nettoyer_titre_nfl_tv_programme(
    titre,
):
    titre = " ".join(
        unescape(
            titre
            or ""
        ).split()
    )

    if (
        "redzone"
        in titre.casefold()
    ):
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

    titre = re.sub(
        r"\s*/\s*",
        " - ",
        titre,
    )

    return formater_match(
        titre.strip()
    )


def uid_tv_programme(
    href,
    match,
    date,
):
    if href:
        correspondance = re.search(
            r"-e(\d+)",
            href,
        )

        if correspondance:
            return (
                "nfl-tvp-e"
                + correspondance.group(1)
                + "@sports-us-bein-calendar"
            )

    compact = re.sub(
        r"[^a-z0-9]+",
        "-",
        match.casefold(),
    ).strip("-")

    return (
        f"nfl-tvp-"
        f"{date:%Y%m%d}-"
        f"{compact}"
        f"@sports-us-bein-calendar"
    )


def recuperer_evenements_nfl_tv_programme(
    sport,
    dtstamps_existants,
):
    maintenant_paris = (
        datetime.now(
            PARIS
        )
    )

    aujourd_hui = (
        maintenant_paris.date()
    )

    resultat = []
    deja_vus = set()

    for decalage in range(
        11
    ):
        date = (
            aujourd_hui
            + timedelta(
                days=decalage
            )
        )

        slug = (
            slug_date_tv_programme(
                date
            )
        )

        url = (
            "https://tv-programme.com/"
            + slug
            + "/"
        )

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

        analyseur = (
            AnalyseurProgrammeTV()
        )

        analyseur.feed(
            reponse.text
        )

        analyseur.close()

        for source in (
            analyseur.evenements
        ):
            canal = (
                source
                .get(
                    "canal",
                    "",
                )
                or ""
            ).strip()

            if not canal.casefold().startswith(
                "bein sports"
            ):
                continue

            if not est_evenement_nfl_tv_programme(
                source
            ):
                continue

            if not est_direct_tv_programme(
                source
            ):
                continue

            heure = extraire_heure(
                source.get(
                    "pre",
                    [],
                )
            )

            if not heure:
                continue

            match = (
                nettoyer_titre_nfl_tv_programme(
                    source.get(
                        "titre",
                        "",
                    )
                )
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

            fin_local = (
                debut_local
                + timedelta(
                    minutes=duree_evenement(
                        match,
                        sport,
                    )
                )
            )

            if (
                fin_local
                <= maintenant_paris
            ):
                continue

            uid = uid_tv_programme(
                source.get(
                    "href"
                ),
                match,
                date,
            )

            cle = (
                uid,
                debut_local,
                canal,
            )

            if cle in deja_vus:
                continue

            deja_vus.add(
                cle
            )

            if est_redzone(
                match
            ):
                lieu = None
                statut_lieu = (
                    "multiple"
                )

            else:
                lieu = stade_estime(
                    match,
                    sport,
                )

                statut_lieu = (
                    "estimation"
                    if lieu
                    else None
                )

            href = source.get(
                "href"
            )

            if href:
                if href.startswith(
                    "http"
                ):
                    url_detail = (
                        href
                    )

                else:
                    url_detail = (
                        "https://tv-programme.com"
                        + href
                    )

            else:
                url_detail = url

            resultat.append(
                {
                    "uid": uid,

                    "dtstamp": (
                        dtstamps_existants
                        .get(
                            uid
                        )
                        or datetime.now(
                            timezone.utc
                        ).strftime(
                            "%Y%m%dT%H%M%SZ"
                        )
                    ),

                    "dtstart": (
                        debut_local
                        .astimezone(
                            timezone.utc
                        )
                        .strftime(
                            "%Y%m%dT%H%M%SZ"
                        )
                    ),

                    "dtend": (
                        fin_local
                        .astimezone(
                            timezone.utc
                        )
                        .strftime(
                            "%Y%m%dT%H%M%SZ"
                        )
                    ),

                    "match": match,
                    "chaines": [
                        canal
                    ],
                    "url": url_detail,
                    "lieu": lieu,
                    "statut_lieu": statut_lieu,
                }
            )

    resultat.sort(
        key=lambda evenement:
        evenement[
            "dtstart"
        ]
    )

    return resultat


def extraire_match_calendrier_existant(
    evenement,
    sport,
):
    summary = valeur_propriete(
        evenement,
        "SUMMARY",
    )

    if not summary:
        return None

    summary = deschapper_ics(
        summary
    ).strip()

    prefixe = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} : "
    )

    if summary.startswith(
        prefixe
    ):
        return summary[
            len(prefixe):
        ].strip()

    if ":" in summary:
        return (
            summary
            .split(
                ":",
                1,
            )[1]
            .strip()
        )

    return None


def extraire_chaines_calendrier_existant(
    evenement,
):
    description = valeur_propriete(
        evenement,
        "DESCRIPTION",
    )

    if not description:
        return []

    description = (
        deschapper_ics(
            description
        )
        .strip()
    )

    if not description:
        return []

    chaines = []

    for chaine in re.split(
        r"\s+(?:\+|/)\s+",
        description,
    ):
        chaine = chaine.strip()

        if (
            chaine
            and chaine
            not in chaines
        ):
            chaines.append(
                chaine
            )

    return chaines


def charger_evenements_existants(
    fichier,
    sport,
):
    try:
        with open(
            fichier,
            encoding="utf-8",
        ) as calendrier:
            sources = (
                extraire_evenements_ics(
                    calendrier.read()
                )
            )

    except OSError:
        return []

    resultat = []

    maintenant = datetime.now(
        timezone.utc
    )

    for source in sources:
        uid = valeur_propriete(
            source,
            "UID",
        )

        dtstamp = valeur_propriete(
            source,
            "DTSTAMP",
        )

        dtstart = valeur_propriete(
            source,
            "DTSTART",
        )

        dtend = valeur_propriete(
            source,
            "DTEND",
        )

        match = (
            extraire_match_calendrier_existant(
                source,
                sport,
            )
        )

        chaines = (
            extraire_chaines_calendrier_existant(
                source
            )
        )

        if (
            not uid
            or not dtstart
            or not match
            or not chaines
        ):
            continue

        fin = parse_datetime_ics(
            dtend
            or dtstart
        )

        if (
            fin
            and fin
            < maintenant
        ):
            continue

        lieu_brut = valeur_propriete(
            source,
            "LOCATION",
        )

        lieu = (
            deschapper_ics(
                lieu_brut
            ).strip()
            if lieu_brut
            else None
        )

        url_brute = valeur_propriete(
            source,
            "URL",
        )

        url = (
            deschapper_ics(
                url_brute
            ).strip()
            if url_brute
            else None
        )

        resultat.append(
            {
                "uid": uid,
                "dtstamp": (
                    dtstamp
                    or datetime.now(
                        timezone.utc
                    ).strftime(
                        "%Y%m%dT%H%M%SZ"
                    )
                ),
                "dtstart": dtstart,
                "dtend": dtend,
                "match": match,
                "chaines": chaines,
                "url": url,
                "lieu": lieu,
                "statut_lieu": (
                    "conserve"
                    if lieu
                    else None
                ),
            }
        )

    return resultat


def construire_evenement(
    evenement,
    sport,
):
    chaines = " + ".join(
        evenement[
            "chaines"
        ]
    )

    resume = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} : "
        f"{formater_match(evenement['match'])}"
    )

    lieu = evenement.get(
        "lieu"
    )

    lignes = [
        "BEGIN:VEVENT",

        (
            "UID:"
            f"{evenement['uid']}"
        ),

        (
            "DTSTAMP:"
            f"{evenement['dtstamp']}"
        ),

        (
            "DTSTART:"
            f"{evenement['dtstart']}"
        ),
    ]

    if evenement.get(
        "dtend"
    ):
        lignes.append(
            "DTEND:"
            f"{evenement['dtend']}"
        )

    lignes.extend(
        [
            (
                "SUMMARY:"
                + echapper_ics(
                    resume
                )
            ),

            (
                "DESCRIPTION:"
                + echapper_ics(
                    chaines
                )
            ),
        ]
    )

    if lieu:
        lignes.append(
            "LOCATION:"
            + echapper_ics(
                lieu
            )
        )

    if evenement.get(
        "url"
    ):
        lignes.append(
            "URL:"
            f"{evenement['url']}"
        )

    lignes.extend(
        [
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]
    )

    return lignes


def ecrire_calendrier(
    evenements,
    sport,
):
    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",

        (
            "PRODID:"
            "-//sports-us-bein-calendar//"
            f"{sport['prefixe']}//FR"
        ),

        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",

        (
            "X-WR-CALNAME:"
            + echapper_ics(
                sport["nom"]
            )
        ),

        (
            "REFRESH-INTERVAL;"
            "VALUE=DURATION:PT6H"
        ),

        "X-PUBLISHED-TTL:PT6H",
    ]

    for evenement in evenements:
        lignes.extend(
            construire_evenement(
                evenement,
                sport,
            )
        )

    lignes.append(
        "END:VCALENDAR"
    )

    lignes_pliees = []

    for ligne in lignes:
        lignes_pliees.extend(
            plier_ligne_ics(
                ligne
            )
        )

    with open(
        sport["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write(
            "\r\n".join(
                lignes_pliees
            )
            + "\r\n"
        )


def afficher_evenements(
    evenements,
):
    for evenement in evenements:
        ligne = (
            "  "
            + formater_match(
                evenement[
                    "match"
                ]
            )
            + " — "
            + " + ".join(
                evenement[
                    "chaines"
                ]
            )
        )

        if evenement.get(
            "lieu"
        ):
            ligne += (
                " — 📍 "
                + evenement[
                    "lieu"
                ]
            )

            if (
                evenement.get(
                    "statut_lieu"
                )
                == "estimation"
            ):
                ligne += (
                    " (estimation)"
                )

        elif (
            evenement.get(
                "statut_lieu"
            )
            == "multiple"
        ):
            ligne += (
                " — 📍 "
                "plusieurs matchs"
            )

        else:
            ligne += (
                " — 📍 "
                "lieu à confirmer"
            )

        print(
            ligne
        )


def traiter_sport(
    sport,
):
    print(
        "Téléchargement de "
        f"{sport['nom']}…"
    )

    dtstamps_existants = (
        lire_dtstamps_existants(
            sport["fichier"]
        )
    )

    evenements_bein = []
    source_utilisee = None

    try:
        evenements_bein = (
            recuperer_evenements_tv_sports(
                sport,
                dtstamps_existants,
            )
        )

        if evenements_bein:
            source_utilisee = (
                "TV-Sports ICS"
            )

    except requests.HTTPError as erreur:
        code = (
            erreur.response.status_code
            if (
                erreur.response
                is not None
            )
            else "?"
        )

        print(
            "  Flux TV-Sports ICS "
            "indisponible "
            f"(HTTP {code})."
        )

    except (
        requests.RequestException,
        RuntimeError,
    ) as erreur:
        print(
            "  Flux TV-Sports ICS "
            "indisponible : "
            f"{erreur}"
        )

    if (
        not evenements_bein
        and sport["prefixe"]
        == "NFL"
    ):
        print(
            "  Bascule NFL sur "
            "TV-Programme.com…"
        )

        try:
            evenements_bein = (
                recuperer_evenements_nfl_tv_programme(
                    sport,
                    dtstamps_existants,
                )
            )

            if evenements_bein:
                source_utilisee = (
                    "TV-Programme.com"
                )

        except (
            requests.RequestException,
            RuntimeError,
        ) as erreur:
            print(
                "  AVERTISSEMENT : "
                "fallback NFL impossible : "
                f"{erreur}"
            )

    if (
        sport["prefixe"]
        == "NFL"
    ):
        evenements_netflix = (
            creer_evenements_netflix_nfl(
                sport,
                dtstamps_existants,
            )
        )

        print(
            f"  {len(evenements_netflix)} "
            "match(s) NFL Netflix "
            "officiellement annoncé(s) "
            "encore à venir."
        )

        if not evenements_bein:
            evenements_existants = (
                charger_evenements_existants(
                    sport["fichier"],
                    sport,
                )
            )

            if evenements_existants:
                print(
                    "  Sources beIN "
                    "indisponibles : "
                    "conservation des "
                    "événements NFL "
                    "existants."
                )

                evenements_bein = (
                    evenements_existants
                )

                source_utilisee = (
                    "Calendrier existant"
                )

        evenements = (
            fusionner_evenements_nfl(
                evenements_bein,
                evenements_netflix,
            )
        )

        if source_utilisee:
            source_utilisee += (
                " + Netflix"
            )

        elif evenements_netflix:
            source_utilisee = (
                "Netflix"
            )

    else:
        evenements = (
            evenements_bein
        )

    if not evenements:
        print(
            "  AVERTISSEMENT : "
            "aucune diffusion "
            f"{sport['prefixe']} "
            "récupérée."
        )

        print(
            "  Le fichier "
            f"{sport['fichier']} "
            "existant est conservé."
        )

        return False

    ecrire_calendrier(
        evenements,
        sport,
    )

    print(
        f"{len(evenements)} "
        "diffusion(s) écrite(s) "
        "dans "
        f"{sport['fichier']}."
    )

    print(
        "  Source utilisée : "
        f"{source_utilisee}"
    )

    afficher_evenements(
        evenements
    )

    if (
        sport["prefixe"]
        == "NFL"
    ):
        print(
            "  Week 18 Netflix "
            "(09/01/2027) : "
            "affiche encore à confirmer, "
            "donc non ajoutée pour "
            "éviter d'inventer un match."
        )

    return True


def extraire_vevents(
    fichier,
):
    evenements = []
    evenement = None

    with open(
        fichier,
        encoding="utf-8",
    ) as calendrier:
        for ligne in calendrier:
            ligne = (
                ligne.rstrip(
                    "\r\n"
                )
            )

            if (
                ligne
                == "BEGIN:VEVENT"
            ):
                evenement = [
                    ligne
                ]

            elif (
                evenement
                is not None
            ):
                evenement.append(
                    ligne
                )

                if (
                    ligne
                    == "END:VEVENT"
                ):
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
            "PRODID:"
            "-//sports-us-bein-calendar//"
            "Tous les sports//FR"
        ),

        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",

        (
            "X-WR-CALNAME:"
            "Sports — F1 + MLB + NFL"
        ),

        (
            "REFRESH-INTERVAL;"
            "VALUE=DURATION:PT6H"
        ),

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
            "\r\n".join(
                lignes
            )
            + "\r\n"
        )


def main():
    for sport in SPORTS:
        traiter_sport(
            sport
        )

    ecrire_calendrier_global()

    print(
        "Calendrier global écrit "
        "dans sports_calendar.ics."
    )


if __name__ == "__main__":
    main()
