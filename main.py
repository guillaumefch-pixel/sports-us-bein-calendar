import re
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

import requests


BASE_TV_SPORTS = "https://tv-sports.fr"

EN_TETES = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "text/calendar;q=0.9,*/*;q=0.8"
    ),
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
        "url_page": (
            "https://tv-sports.fr/"
            "base-ball/mlb/match-direct"
        ),
        "fichier": "mlb_bein_calendar.ics",
        "duree_minutes": 210,
    },
    {
        "nom": "NFL sur beIN",
        "prefixe": "NFL",
        "emoji": "🏈",
        "url_ics": (
            "https://tv-sports.fr/"
            "calendrier/competition/172/nfl?direct=1"
        ),
        "url_page": (
            "https://tv-sports.fr/"
            "football-americain/nfl"
        ),
        "fichier": "nfl_bein_calendar.ics",
        "duree_minutes": 240,
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


class AnalyseurLiensEvenements(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.liens = []

    def handle_starttag(
        self,
        balise,
        attributs,
    ):
        if balise != "a":
            return

        attributs = dict(
            attributs
        )

        href = (
            attributs
            .get(
                "href",
                "",
            )
            .strip()
        )

        if not href:
            return

        if re.search(
            r"-tv-x\d+",
            href,
        ):
            self.liens.append(
                href
            )


class AnalyseurPageDetail(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.capture_h3 = False
        self.texte_h3 = []

        self.dans_direct = False

        self.liens_ics_direct = []

        self.textes = []
        self.ignorer = 0

    def handle_starttag(
        self,
        balise,
        attributs,
    ):
        attributs = dict(
            attributs
        )

        if balise in (
            "script",
            "style",
            "noscript",
        ):
            self.ignorer += 1

        if balise == "h3":
            self.capture_h3 = True
            self.texte_h3 = []

        if (
            balise == "a"
            and self.dans_direct
        ):
            href = (
                attributs
                .get(
                    "href",
                    "",
                )
                .strip()
            )

            if (
                href
                and "/calendrier/diffusion/"
                in href
                and ".ics" in href
            ):
                self.liens_ics_direct.append(
                    href
                )

    def handle_endtag(
        self,
        balise,
    ):
        if (
            balise
            in (
                "script",
                "style",
                "noscript",
            )
            and self.ignorer > 0
        ):
            self.ignorer -= 1

        if (
            balise == "h3"
            and self.capture_h3
        ):
            texte = " ".join(
                "".join(
                    self.texte_h3
                ).split()
            )

            self.dans_direct = (
                texte
                .casefold()
                == "direct"
            )

            self.capture_h3 = False
            self.texte_h3 = []

    def handle_data(
        self,
        donnees,
    ):
        if self.ignorer:
            return

        if self.capture_h3:
            self.texte_h3.append(
                donnees
            )

        texte = " ".join(
            donnees.split()
        )

        if not texte:
            return

        self.textes.append(
            texte
        )

        if (
            self.dans_direct
            and texte
            .casefold()
            .startswith(
                "rediffusion"
            )
        ):
            self.dans_direct = False


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

            elif suivant == ",":
                resultat.append(
                    ","
                )

            elif suivant == ";":
                resultat.append(
                    ";"
                )

            elif suivant == "\\":
                resultat.append(
                    "\\"
                )

            else:
                resultat.append(
                    suivant
                )

            index += 2
            continue

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

    return morceaux or [
        ""
    ]


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
    lignes = deplier_ics(
        texte
    )

    evenements = []
    evenement = None

    for ligne in lignes:
        if ligne == "BEGIN:VEVENT":
            evenement = [
                ligne
            ]
            continue

        if evenement is None:
            continue

        evenement.append(
            ligne
        )

        if ligne == "END:VEVENT":
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
            resultat[uid] = (
                dtstamp
            )

    return resultat


def normaliser_nom(
    texte,
):
    return (
        texte
        .strip()
        .casefold()
        .replace(
            "’",
            "'",
        )
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
            "competition": None,
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

    competition = (
        parties[1]
        if len(parties) >= 2
        else None
    )

    if competition:
        competition = re.sub(
            r"^(?:Base-ball|"
            r"Football américain)"
            r"\s*-\s*",
            "",
            competition,
            flags=re.IGNORECASE,
        ).strip()

    chaines = []

    if len(parties) >= 3:
        for partie in parties[
            2:
        ]:
            chaine = (
                partie.strip()
            )

            if (
                chaine
                and chaine
                not in chaines
            ):
                chaines.append(
                    chaine
                )

    return {
        "match": match,
        "competition": competition,
        "chaines": chaines,
    }


def extraire_match_ics(
    evenement,
):
    description = (
        valeur_propriete(
            evenement,
            "DESCRIPTION",
        )
    )

    infos = (
        extraire_infos_description(
            description
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
    description = (
        valeur_propriete(
            evenement,
            "DESCRIPTION",
        )
    )

    infos = (
        extraire_infos_description(
            description
        )
    )

    chaines = []

    for chaine in infos[
        "chaines"
    ]:
        if (
            chaine
            .casefold()
            .startswith(
                "bein sports"
            )
        ):
            if (
                chaine
                not in chaines
            ):
                chaines.append(
                    chaine
                )

    return chaines


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


def extraire_equipe_domicile(
    match,
):
    if not match:
        return None

    morceaux = re.split(
        r"\s+[–—-]\s+",
        match,
        maxsplit=1,
    )

    if len(morceaux) != 2:
        return None

    return (
        morceaux[0]
        .strip()
    )


def stade_estime(
    match,
    sport,
):
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


def extraire_lieu_page_detail(
    page,
):
    analyseur = (
        AnalyseurPageDetail()
    )

    analyseur.feed(
        page
    )

    textes = analyseur.textes

    fins = {
        "diffusion",
        "avant-match",
        "tendances",
        "compétition",
        "tour",
        "saison",
        "date et heure",
        "calendrier",
        "horaire",
        "chaîne",
    }

    for index, texte in enumerate(
        textes
    ):
        if (
            texte
            .strip()
            .casefold()
            not in {
                "lieu",
                "stade",
            }
        ):
            continue

        for suivant in textes[
            index + 1:
        ]:
            suivant = (
                suivant.strip()
            )

            if not suivant:
                continue

            if (
                suivant
                .casefold()
                in fins
            ):
                return None

            if (
                suivant
                .casefold()
                .startswith(
                    "bein sports"
                )
            ):
                return None

            return suivant

    return None


def recuperer_page(
    url,
    timeout=30,
):
    reponse = requests.get(
        url,
        headers=EN_TETES,
        timeout=timeout,
    )

    reponse.raise_for_status()

    return reponse.text


def recuperer_lieu_page(
    url,
    cache_lieux,
):
    if not url:
        return None

    if url in cache_lieux:
        return (
            cache_lieux[
                url
            ]
        )

    try:
        page = recuperer_page(
            url,
            timeout=15,
        )

        lieu = (
            extraire_lieu_page_detail(
                page
            )
        )

    except requests.RequestException:
        lieu = None

    cache_lieux[
        url
    ] = lieu

    return lieu


def determiner_lieu(
    match,
    sport,
    url=None,
    cache_lieux=None,
    lieu_source=None,
    page_detail=None,
):
    if est_redzone(
        match
    ):
        return (
            None,
            "multiple",
        )

    if lieu_source:
        return (
            lieu_source,
            "source",
        )

    if page_detail:
        lieu_page = (
            extraire_lieu_page_detail(
                page_detail
            )
        )

        if lieu_page:
            return (
                lieu_page,
                "source",
            )

    if (
        url
        and cache_lieux
        is not None
    ):
        lieu_page = (
            recuperer_lieu_page(
                url,
                cache_lieux,
            )
        )

        if lieu_page:
            return (
                lieu_page,
                "source",
            )

    lieu_estime = stade_estime(
        match,
        sport,
    )

    if lieu_estime:
        return (
            lieu_estime,
            "estimation",
        )

    return (
        None,
        None,
    )


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

            return (
                resultat.replace(
                    tzinfo=timezone.utc
                )
            )

        except ValueError:
            continue

    return None


def parse_iso_utc(
    valeur,
):
    if not valeur:
        return None

    try:
        resultat = (
            datetime.fromisoformat(
                valeur.replace(
                    "Z",
                    "+00:00",
                )
            )
        )

    except ValueError:
        return None

    if resultat.tzinfo is None:
        resultat = (
            resultat.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        resultat.astimezone(
            timezone.utc
        )
    )


def duree_defaut(
    match,
    sport,
):
    if (
        sport["prefixe"] == "NFL"
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
    cache_lieux,
    dtstamps_existants,
):
    match = (
        extraire_match_ics(
            evenement
        )
    )

    if not match:
        return None

    chaines = (
        extraire_chaines_ics(
            evenement
        )
    )

    if not chaines:
        return None

    uid = valeur_propriete(
        evenement,
        "UID",
    )

    dtstart = valeur_propriete(
        evenement,
        "DTSTART",
    )

    if (
        not uid
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

    url = extraire_url_ics(
        evenement
    )

    lieu_source = (
        extraire_lieu_source_ics(
            evenement
        )
    )

    lieu, statut_lieu = (
        determiner_lieu(
            match=match,
            sport=sport,
            url=url,
            cache_lieux=cache_lieux,
            lieu_source=lieu_source,
        )
    )

    if not dtend:
        debut = (
            parse_datetime_ics(
                dtstart
            )
        )

        if debut:
            fin = debut + timedelta(
                minutes=duree_defaut(
                    match,
                    sport,
                )
            )

            dtend = fin.strftime(
                "%Y%m%dT%H%M%SZ"
            )

    return {
        "uid": uid,
        "dtstamp": dtstamp,
        "dtstart": dtstart,
        "dtend": dtend,
        "match": match,
        "chaines": chaines,
        "url": url,
        "lieu": lieu,
        "statut_lieu": statut_lieu,
    }


def recuperer_evenements_ics(
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

    source = (
        extraire_evenements_ics(
            texte
        )
    )

    cache_lieux = {}
    evenements = []

    for evenement_source in source:
        evenement = (
            preparer_evenement_ics(
                evenement_source,
                sport,
                cache_lieux,
                dtstamps_existants,
            )
        )

        if evenement:
            evenements.append(
                evenement
            )

    return evenements


def extraire_liens_evenements(
    page,
):
    analyseur = (
        AnalyseurLiensEvenements()
    )

    analyseur.feed(
        page
    )

    resultat = []
    deja_vus = set()

    for href in analyseur.liens:
        url = urljoin(
            BASE_TV_SPORTS,
            unescape(
                href
            ),
        )

        if url in deja_vus:
            continue

        deja_vus.add(
            url
        )

        resultat.append(
            url
        )

    return resultat


def extraire_liens_ics_direct(
    page,
):
    analyseur = (
        AnalyseurPageDetail()
    )

    analyseur.feed(
        page
    )

    resultat = []
    deja_vus = set()

    for href in (
        analyseur
        .liens_ics_direct
    ):
        url = urljoin(
            BASE_TV_SPORTS,
            unescape(
                href
            ),
        )

        if url in deja_vus:
            continue

        deja_vus.add(
            url
        )

        resultat.append(
            url
        )

    return resultat


def uid_depuis_lien_direct(
    lien_ics,
    source,
    sport,
):
    correspondance = re.search(
        r"-tv-x(\d+)",
        source or "",
    )

    if correspondance:
        return (
            f"{sport['prefixe'].lower()}-"
            f"x{correspondance.group(1)}"
            f"@sports-us-bein-calendar"
        )

    chemin = urlparse(
        lien_ics
    ).path

    correspondance = re.search(
        r"/calendrier/diffusion/"
        r"(d\d+)\.ics",
        chemin,
    )

    if correspondance:
        return (
            f"{sport['prefixe'].lower()}-"
            f"{correspondance.group(1)}"
            f"@sports-us-bein-calendar"
        )

    identifiant = re.sub(
        r"[^a-z0-9]+",
        "-",
        lien_ics.casefold(),
    ).strip("-")

    return (
        f"{sport['prefixe'].lower()}-"
        f"{identifiant[-80:]}"
        f"@sports-us-bein-calendar"
    )


def preparer_depuis_lien_direct(
    lien_ics,
    page_detail,
    url_detail,
    sport,
    dtstamps_existants,
):
    analyse = urlparse(
        lien_ics
    )

    parametres = parse_qs(
        analyse.query
    )

    titre = (
        parametres
        .get(
            "title",
            [None],
        )[0]
    )

    chaine = (
        parametres
        .get(
            "channel",
            [None],
        )[0]
    )

    debut_brut = (
        parametres
        .get(
            "start",
            [None],
        )[0]
    )

    fin_brut = (
        parametres
        .get(
            "end",
            [None],
        )[0]
    )

    source = (
        parametres
        .get(
            "source",
            [None],
        )[0]
    )

    if titre:
        titre = unescape(
            titre
        ).strip()

    if chaine:
        chaine = unescape(
            chaine
        ).strip()

    if (
        not titre
        or not chaine
        or not chaine
        .casefold()
        .startswith(
            "bein sports"
        )
    ):
        return None

    debut = parse_iso_utc(
        debut_brut
    )

    fin = parse_iso_utc(
        fin_brut
    )

    if not debut:
        return None

    if not fin:
        fin = debut + timedelta(
            minutes=duree_defaut(
                titre,
                sport,
            )
        )

    maintenant = datetime.now(
        timezone.utc
    )

    if fin <= maintenant:
        return None

    if source:
        url_evenement = urljoin(
            BASE_TV_SPORTS,
            source,
        )

    else:
        url_evenement = (
            url_detail
        )

    uid = uid_depuis_lien_direct(
        lien_ics,
        source or url_detail,
        sport,
    )

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

    lieu, statut_lieu = (
        determiner_lieu(
            match=titre,
            sport=sport,
            url=url_evenement,
            cache_lieux=None,
            lieu_source=None,
            page_detail=page_detail,
        )
    )

    return {
        "uid": uid,
        "dtstamp": dtstamp,
        "dtstart": debut.strftime(
            "%Y%m%dT%H%M%SZ"
        ),
        "dtend": fin.strftime(
            "%Y%m%dT%H%M%SZ"
        ),
        "match": titre,
        "chaines": [
            chaine
        ],
        "url": url_evenement,
        "lieu": lieu,
        "statut_lieu": statut_lieu,
    }


def fusionner_evenements(
    evenements,
):
    resultat = {}

    for evenement in evenements:
        cle = (
            evenement["uid"],
            evenement["dtstart"],
            evenement["match"],
        )

        if cle not in resultat:
            resultat[cle] = (
                evenement
            )

            continue

        existant = resultat[
            cle
        ]

        for chaine in evenement[
            "chaines"
        ]:
            if (
                chaine
                not in existant[
                    "chaines"
                ]
            ):
                existant[
                    "chaines"
                ].append(
                    chaine
                )

        if (
            not existant["lieu"]
            and evenement["lieu"]
        ):
            existant["lieu"] = (
                evenement[
                    "lieu"
                ]
            )

            existant[
                "statut_lieu"
            ] = (
                evenement[
                    "statut_lieu"
                ]
            )

    return list(
        resultat.values()
    )


def recuperer_evenements_page(
    sport,
    dtstamps_existants,
):
    page_principale = (
        recuperer_page(
            sport["url_page"],
            timeout=30,
        )
    )

    liens_evenements = (
        extraire_liens_evenements(
            page_principale
        )
    )

    if not liens_evenements:
        raise RuntimeError(
            f"Aucun lien de match "
            f"{sport['prefixe']} "
            f"trouvé sur la page publique."
        )

    evenements = []

    for url_detail in (
        liens_evenements
    ):
        try:
            page_detail = (
                recuperer_page(
                    url_detail,
                    timeout=20,
                )
            )

        except requests.RequestException as erreur:
            print(
                "    Avertissement : "
                "page match inaccessible : "
                f"{erreur}"
            )

            continue

        liens_direct = (
            extraire_liens_ics_direct(
                page_detail
            )
        )

        for lien_direct in (
            liens_direct
        ):
            evenement = (
                preparer_depuis_lien_direct(
                    lien_direct,
                    page_detail,
                    url_detail,
                    sport,
                    dtstamps_existants,
                )
            )

            if evenement:
                evenements.append(
                    evenement
                )

    evenements = (
        fusionner_evenements(
            evenements
        )
    )

    evenements.sort(
        key=lambda evenement:
        evenement["dtstart"]
    )

    return evenements


def construire_evenement(
    evenement,
    sport,
):
    chaines = " / ".join(
        evenement[
            "chaines"
        ]
    )

    resume = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} — "
        f"{evenement['match']}"
    )

    description = (
        "Diffusion en direct : "
        f"{chaines}"
    )

    lieu = evenement[
        "lieu"
    ]

    statut_lieu = evenement[
        "statut_lieu"
    ]

    if lieu:
        if (
            statut_lieu
            == "estimation"
        ):
            description += (
                "\nLieu estimé : "
                f"{lieu}"
            )

        else:
            description += (
                f"\nLieu : {lieu}"
            )

    elif (
        statut_lieu
        == "multiple"
    ):
        description += (
            "\nLieu : plusieurs "
            "matchs simultanés"
        )

    else:
        description += (
            "\nLieu : à confirmer"
        )

    if evenement[
        "url"
    ]:
        description += (
            "\nSource : "
            f"{evenement['url']}"
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

    if evenement[
        "dtend"
    ]:
        lignes.append(
            "DTEND:"
            f"{evenement['dtend']}"
        )

    lignes.extend(
        [
            (
                "SUMMARY:"
                f"{echapper_ics(resume)}"
            ),
            (
                "DESCRIPTION:"
                f"{echapper_ics(description)}"
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

    if evenement[
        "url"
    ]:
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
            f"{sport['prefixe']} beIN//FR"
        ),
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        (
            "X-WR-CALNAME:"
            f"{echapper_ics(sport['nom'])}"
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
            f"{evenement['match']} — "
            f"{' / '.join(evenement['chaines'])}"
        )

        if evenement[
            "lieu"
        ]:
            ligne += (
                " — 📍 "
                f"{evenement['lieu']}"
            )

            if (
                evenement[
                    "statut_lieu"
                ]
                == "estimation"
            ):
                ligne += (
                    " (estimation)"
                )

        elif (
            evenement[
                "statut_lieu"
            ]
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

    evenements = []
    source_utilisee = None

    try:
        evenements = (
            recuperer_evenements_ics(
                sport,
                dtstamps_existants,
            )
        )

        if evenements:
            source_utilisee = (
                "ICS"
            )

    except requests.HTTPError as erreur:
        code = (
            erreur.response.status_code
            if erreur.response
            is not None
            else "?"
        )

        print(
            "  Flux ICS indisponible "
            f"(HTTP {code})."
        )

    except (
        requests.RequestException,
        RuntimeError,
    ) as erreur:
        print(
            "  Flux ICS indisponible : "
            f"{erreur}"
        )

    if not evenements:
        print(
            "  Bascule sur la page "
            "publique TV-Sports et "
            "les liens Apple des "
            "diffusions Direct…"
        )

        try:
            evenements = (
                recuperer_evenements_page(
                    sport,
                    dtstamps_existants,
                )
            )

            if evenements:
                source_utilisee = (
                    "Page TV-Sports "
                    "+ liens Apple"
                )

        except (
            requests.RequestException,
            RuntimeError,
        ) as erreur:
            print(
                "  AVERTISSEMENT : "
                "fallback impossible : "
                f"{erreur}"
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
