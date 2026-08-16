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
        "url": (
            "https://tv-sports.fr/"
            "calendrier/competition/199/mlb?direct=1"
        ),
        "fichier": "mlb_bein_calendar.ics",
        "duree_minutes": 210,
    },
    {
        "nom": "NFL sur beIN",
        "prefixe": "NFL",
        "emoji": "🏈",
        "url": (
            "https://tv-sports.fr/"
            "calendrier/competition/172/nfl?direct=1"
        ),
        "fichier": "nfl_bein_calendar.ics",
        "duree_minutes": 240,
    },
)


STADES_MLB = {
    "arizona diamondbacks": (
        "Chase Field, Phoenix"
    ),
    "athletics": (
        "Sutter Health Park, West Sacramento"
    ),
    "oakland athletics": (
        "Sutter Health Park, West Sacramento"
    ),
    "atlanta braves": (
        "Truist Park, Atlanta"
    ),
    "baltimore orioles": (
        "Oriole Park at Camden Yards, Baltimore"
    ),
    "boston red sox": (
        "Fenway Park, Boston"
    ),
    "chicago cubs": (
        "Wrigley Field, Chicago"
    ),
    "chicago white sox": (
        "Rate Field, Chicago"
    ),
    "cincinnati reds": (
        "Great American Ball Park, Cincinnati"
    ),
    "cleveland guardians": (
        "Progressive Field, Cleveland"
    ),
    "colorado rockies": (
        "Coors Field, Denver"
    ),
    "detroit tigers": (
        "Comerica Park, Detroit"
    ),
    "houston astros": (
        "Daikin Park, Houston"
    ),
    "kansas city royals": (
        "Kauffman Stadium, Kansas City"
    ),
    "los angeles angels": (
        "Angel Stadium, Anaheim"
    ),
    "los angeles dodgers": (
        "Dodger Stadium, Los Angeles"
    ),
    "miami marlins": (
        "loanDepot park, Miami"
    ),
    "milwaukee brewers": (
        "American Family Field, Milwaukee"
    ),
    "minnesota twins": (
        "Target Field, Minneapolis"
    ),
    "new york mets": (
        "Citi Field, New York"
    ),
    "new york yankees": (
        "Yankee Stadium, New York"
    ),
    "philadelphia phillies": (
        "Citizens Bank Park, Philadelphia"
    ),
    "pittsburgh pirates": (
        "PNC Park, Pittsburgh"
    ),
    "san diego padres": (
        "Petco Park, San Diego"
    ),
    "san francisco giants": (
        "Oracle Park, San Francisco"
    ),
    "seattle mariners": (
        "T-Mobile Park, Seattle"
    ),
    "st louis cardinals": (
        "Busch Stadium, St. Louis"
    ),
    "st. louis cardinals": (
        "Busch Stadium, St. Louis"
    ),
    "tampa bay rays": (
        "Tropicana Field, St. Petersburg"
    ),
    "texas rangers": (
        "Globe Life Field, Arlington"
    ),
    "toronto blue jays": (
        "Rogers Centre, Toronto"
    ),
    "washington nationals": (
        "Nationals Park, Washington"
    ),
}


STADES_NFL = {
    "arizona cardinals": (
        "State Farm Stadium, Glendale"
    ),
    "atlanta falcons": (
        "Mercedes-Benz Stadium, Atlanta"
    ),
    "baltimore ravens": (
        "M&T Bank Stadium, Baltimore"
    ),
    "buffalo bills": (
        "Highmark Stadium, Orchard Park"
    ),
    "carolina panthers": (
        "Bank of America Stadium, Charlotte"
    ),
    "chicago bears": (
        "Soldier Field, Chicago"
    ),
    "cincinnati bengals": (
        "Paycor Stadium, Cincinnati"
    ),
    "cleveland browns": (
        "Huntington Bank Field, Cleveland"
    ),
    "dallas cowboys": (
        "AT&T Stadium, Arlington"
    ),
    "denver broncos": (
        "Empower Field at Mile High, Denver"
    ),
    "detroit lions": (
        "Ford Field, Detroit"
    ),
    "green bay packers": (
        "Lambeau Field, Green Bay"
    ),
    "houston texans": (
        "NRG Stadium, Houston"
    ),
    "indianapolis colts": (
        "Lucas Oil Stadium, Indianapolis"
    ),
    "jacksonville jaguars": (
        "EverBank Stadium, Jacksonville"
    ),
    "kansas city chiefs": (
        "GEHA Field at Arrowhead Stadium, Kansas City"
    ),
    "las vegas raiders": (
        "Allegiant Stadium, Las Vegas"
    ),
    "los angeles chargers": (
        "SoFi Stadium, Inglewood"
    ),
    "los angeles rams": (
        "SoFi Stadium, Inglewood"
    ),
    "miami dolphins": (
        "Hard Rock Stadium, Miami Gardens"
    ),
    "minnesota vikings": (
        "U.S. Bank Stadium, Minneapolis"
    ),
    "new england patriots": (
        "Gillette Stadium, Foxborough"
    ),
    "new orleans saints": (
        "Caesars Superdome, New Orleans"
    ),
    "new york giants": (
        "MetLife Stadium, East Rutherford"
    ),
    "new york jets": (
        "MetLife Stadium, East Rutherford"
    ),
    "philadelphia eagles": (
        "Lincoln Financial Field, Philadelphia"
    ),
    "pittsburgh steelers": (
        "Acrisure Stadium, Pittsburgh"
    ),
    "san francisco 49ers": (
        "Levi's Stadium, Santa Clara"
    ),
    "seattle seahawks": (
        "Lumen Field, Seattle"
    ),
    "tampa bay buccaneers": (
        "Raymond James Stadium, Tampa"
    ),
    "tennessee titans": (
        "Nissan Stadium, Nashville"
    ),
    "washington commanders": (
        "Northwest Stadium, Landover"
    ),
}


class AnalyseurLieuHTML(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.textes = []
        self.ignorer = 0

    def handle_starttag(
        self,
        balise,
        attributs,
    ):
        if balise in (
            "script",
            "style",
            "noscript",
        ):
            self.ignorer += 1

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

    def handle_data(
        self,
        donnees,
    ):
        if self.ignorer:
            return

        texte = " ".join(
            donnees.split()
        )

        if texte:
            self.textes.append(
                texte
            )


def deplier_ics(texte):
    lignes = (
        texte
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .split("\n")
    )

    resultat = []

    for ligne in lignes:
        if (
            ligne.startswith((" ", "\t"))
            and resultat
        ):
            resultat[-1] += ligne[1:]

        else:
            resultat.append(
                ligne
            )

    return resultat


def deschapper_ics(texte):
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


def echapper_ics(texte):
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

        if (
            nouvelle_taille
            > limite
        ):
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
        titre.casefold(),
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


def extraire_match(
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
        return infos["match"]

    summary = valeur_propriete(
        evenement,
        "SUMMARY",
    )

    if summary:
        return deschapper_ics(
            summary
        ).strip()

    return None


def extraire_chaines(
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


def extraire_url(
    evenement,
):
    url = valeur_propriete(
        evenement,
        "URL",
    )

    if not url:
        return None

    return deschapper_ics(
        url
    ).strip()


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


def extraire_lieu_page(
    page,
):
    analyseur = (
        AnalyseurLieuHTML()
    )

    analyseur.feed(
        page
    )

    textes = (
        analyseur.textes
    )

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


def recuperer_lieu_page(
    url,
    cache_lieux,
):
    if not url:
        return None

    if url in cache_lieux:
        return cache_lieux[
            url
        ]

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

    domicile = normaliser_nom(
        domicile
    )

    if (
        sport["prefixe"]
        == "MLB"
    ):
        return STADES_MLB.get(
            domicile
        )

    if (
        sport["prefixe"]
        == "NFL"
    ):
        return STADES_NFL.get(
            domicile
        )

    return None


def determiner_lieu(
    evenement,
    match,
    sport,
    url,
    cache_lieux,
):
    if est_redzone(
        match or ""
    ):
        return (
            None,
            "multiple",
        )

    lieu = (
        extraire_lieu_source_ics(
            evenement
        )
    )

    if lieu:
        return (
            lieu,
            "source",
        )

    lieu = recuperer_lieu_page(
        url,
        cache_lieux,
    )

    if lieu:
        return (
            lieu,
            "source",
        )

    lieu = stade_estime(
        match,
        sport,
    )

    if lieu:
        return (
            lieu,
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
            resultat = datetime.strptime(
                valeur,
                format_date,
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
        sport["prefixe"] == "NFL"
        and est_redzone(
            match or ""
        )
    ):
        return 420

    return sport[
        "duree_minutes"
    ]


def preparer_evenement(
    evenement,
    sport,
    cache_lieux,
):
    match = extraire_match(
        evenement
    )

    if not match:
        return None

    chaines = extraire_chaines(
        evenement
    )

    if not chaines:
        return None

    uid = valeur_propriete(
        evenement,
        "UID",
    )

    if not uid:
        return None

    dtstart = valeur_propriete(
        evenement,
        "DTSTART",
    )

    if not dtstart:
        return None

    dtend = valeur_propriete(
        evenement,
        "DTEND",
    )

    dtstamp = valeur_propriete(
        evenement,
        "DTSTAMP",
    )

    if not dtstamp:
        dtstamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%SZ"
        )

    url = extraire_url(
        evenement
    )

    lieu, statut_lieu = (
        determiner_lieu(
            evenement,
            match,
            sport,
            url,
            cache_lieux,
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
                minutes=duree_evenement(
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
        f"Diffusion en direct : "
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
                f"\nLieu estimé : "
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
            f"\nSource : "
            f"{evenement['url']}"
        )

    lignes = [
        "BEGIN:VEVENT",
        (
            f"UID:"
            f"{evenement['uid']}"
        ),
        (
            f"DTSTAMP:"
            f"{evenement['dtstamp']}"
        ),
        (
            f"DTSTART:"
            f"{evenement['dtstart']}"
        ),
    ]

    if evenement[
        "dtend"
    ]:
        lignes.append(
            f"DTEND:"
            f"{evenement['dtend']}"
        )

    lignes.extend(
        [
            (
                f"SUMMARY:"
                f"{echapper_ics(resume)}"
            ),
            (
                f"DESCRIPTION:"
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
            f"URL:"
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
            f"PRODID:"
            f"-//sports-us-bein-calendar//"
            f"{sport['prefixe']} beIN//FR"
        ),
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        (
            f"X-WR-CALNAME:"
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


def recuperer_flux(
    sport,
):
    reponse = requests.get(
        sport["url"],
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
            f"Le flux ICS "
            f"{sport['prefixe']} "
            f"n'est pas valide."
        )

    return texte


def traiter_sport(
    sport,
):
    print(
        f"Téléchargement de "
        f"{sport['nom']}…"
    )

    texte = recuperer_flux(
        sport
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
            preparer_evenement(
                evenement_source,
                sport,
                cache_lieux,
            )
        )

        if evenement:
            evenements.append(
                evenement
            )

    if not evenements:
        raise RuntimeError(
            f"Aucune diffusion "
            f"{sport['prefixe']} "
            f"sur beIN trouvée "
            f"dans le flux ICS "
            f"TV-Sports."
        )

    ecrire_calendrier(
        evenements,
        sport,
    )

    print(
        f"{len(evenements)} "
        f"diffusion(s) écrite(s) "
        f"dans "
        f"{sport['fichier']}."
    )

    for evenement in evenements:
        ligne = (
            f"  "
            f"{evenement['match']} — "
            f"{' / '.join(evenement['chaines'])}"
        )

        if evenement[
            "lieu"
        ]:
            ligne += (
                f" — 📍 "
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
