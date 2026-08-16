import hashlib
import re
import time
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

            elif (
                "schedule-item" in classes
                or attributs.get("data-is-live") is not None
            ):
                self.element = {
                    "attributs": attributs,
                    "participants": [],
                    "liens": [],
                    "chaines": [],
                }
                self.profondeur_li = 1

            return

        if self.element is None:
            return

        if (
            balise == "time"
            and attributs.get("datetime")
        ):
            self.element["datetime"] = (
                attributs["datetime"]
            )

        elif balise == "img":
            alt = attributs.get("alt", "").strip()

            if (
                "logoChaine" in classes
                and alt
            ):
                if alt not in self.element["chaines"]:
                    self.element["chaines"].append(alt)

        elif balise == "a":
            self.ancre = {
                "classes": classes,
                "href": attributs.get("href", "").strip(),
                "title": attributs.get("title", "").strip(),
                "texte": [],
            }

            if "schedule-participant" in classes:
                participant = (
                    attributs.get("title", "").strip()
                )

                if (
                    participant
                    and participant
                    not in self.element["participants"]
                ):
                    self.element["participants"].append(
                        participant
                    )

    def handle_startendtag(
        self,
        balise,
        attributs,
    ):
        self.handle_starttag(
            balise,
            attributs,
        )

    def handle_data(self, donnees):
        if self.ancre is not None:
            self.ancre["texte"].append(
                donnees
            )

    def handle_endtag(self, balise):
        if (
            balise == "a"
            and self.ancre is not None
            and self.element is not None
        ):
            texte = " ".join(
                "".join(
                    self.ancre["texte"]
                ).split()
            )

            self.ancre["texte"] = texte

            if (
                "schedule-participant"
                in self.ancre["classes"]
                and not self.ancre["title"]
                and texte
                and texte
                not in self.element["participants"]
            ):
                self.element["participants"].append(
                    texte
                )

            self.element["liens"].append(
                self.ancre
            )

            self.ancre = None
            return

        if (
            balise != "li"
            or self.element is None
        ):
            return

        self.profondeur_li -= 1

        if self.profondeur_li == 0:
            self.elements.append(
                self.element
            )

            self.element = None
            self.ancre = None


class AnalyseurTexteHTML(HTMLParser):
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


def recuperer_page(
    url,
    tentatives=3,
):
    derniere_erreur = None

    for tentative in range(
        1,
        tentatives + 1,
    ):
        try:
            reponse = requests.get(
                url,
                headers=EN_TETES,
                timeout=30,
            )

            reponse.raise_for_status()

            if reponse.text.strip():
                return reponse.text

        except requests.RequestException as erreur:
            derniere_erreur = erreur

        if tentative < tentatives:
            print(
                f"  Nouvelle tentative "
                f"{tentative + 1}/{tentatives}…"
            )
            time.sleep(2)

    if derniere_erreur:
        raise derniere_erreur

    raise RuntimeError(
        f"Réponse vide pour {url}"
    )


def est_chaine_bein(chaine):
    return (
        chaine
        .casefold()
        .startswith("bein sports")
    )


def choisir_titre(
    element,
    prefixe,
):
    participants = []

    for participant in element.get(
        "participants",
        [],
    ):
        participant = participant.strip()

        if (
            participant
            and participant not in participants
        ):
            participants.append(
                participant
            )

    if len(participants) >= 2:
        return " – ".join(
            participants[:2]
        )

    for lien in element.get(
        "liens",
        [],
    ):
        texte = lien.get(
            "texte",
            "",
        ).strip()

        href = lien.get(
            "href",
            "",
        )

        if (
            texte
            and (
                "-tv-" in href
                or re.search(
                    r"-e\d+/?$",
                    href,
                )
            )
        ):
            return texte

    for lien in element.get(
        "liens",
        [],
    ):
        if (
            "schedule-entity-visual"
            in lien["classes"]
            and lien["title"]
        ):
            return lien["title"]

    return f"Programme {prefixe}"


def choisir_lien(
    element,
    url_page,
):
    for lien in reversed(
        element.get(
            "liens",
            [],
        )
    ):
        href = lien.get(
            "href",
            "",
        )

        if not href:
            continue

        if (
            "-tv-" in href
            or re.search(
                r"-e\d+/?$",
                href,
            )
        ):
            if href.startswith("/"):
                return (
                    "https://tv-sports.fr"
                    + href
                )

            return href

    return url_page


def extraire_diffusions(
    page,
    sport,
):
    analyseur = AnalyseurPlanning()
    analyseur.feed(page)

    diffusions = []
    deja_vues = set()

    for element in analyseur.elements:
        attributs = element.get(
            "attributs",
            {},
        )

        if (
            attributs.get("data-is-past")
            == "1"
        ):
            continue

        if (
            attributs.get("data-is-live")
            != "1"
        ):
            continue

        chaines = [
            chaine
            for chaine
            in element.get(
                "chaines",
                [],
            )
            if est_chaine_bein(
                chaine
            )
        ]

        if not chaines:
            continue

        try:
            debut = datetime.fromisoformat(
                element["datetime"].replace(
                    "Z",
                    "+00:00",
                )
            ).astimezone(
                timezone.utc
            )

        except (
            KeyError,
            ValueError,
        ):
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
                    for chaine in chaines:
                        if (
                            chaine
                            not in diffusion["chaines"]
                        ):
                            diffusion[
                                "chaines"
                            ].append(
                                chaine
                            )

                    break

            continue

        deja_vues.add(
            cle
        )

        diffusions.append(
            {
                "debut": debut,
                "titre": titre,
                "chaines": chaines,
                "lien": lien,
                "lieu": None,
            }
        )

    return sorted(
        diffusions,
        key=lambda diffusion: (
            diffusion["debut"]
        ),
    )


def extraire_lieu_page_match(page):
    analyseur = AnalyseurTexteHTML()

    analyseur.feed(
        page
    )

    textes = analyseur.textes

    libelles_fin = {
        "diffusion",
        "avant-match",
        "tendances",
        "compétition",
        "tour",
        "saison",
        "date et heure",
        "calendrier des matchs",
        "chaîne",
        "horaire",
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
            suivant = suivant.strip()

            if not suivant:
                continue

            if (
                suivant.casefold()
                in libelles_fin
            ):
                return None

            return suivant

    return None


def recuperer_lieu_page_match(
    url,
    cache_lieux,
):
    if (
        not url
        or url
        in {
            sport["url"]
            for sport in SPORTS
        }
    ):
        return None

    if url in cache_lieux:
        return cache_lieux[url]

    try:
        page = recuperer_page(
            url,
            tentatives=2,
        )

        lieu = extraire_lieu_page_match(
            page
        )

    except (
        requests.RequestException,
        RuntimeError,
    ) as erreur:
        print(
            f"    Avertissement lieu : "
            f"{erreur}"
        )

        lieu = None

    cache_lieux[url] = lieu

    return lieu


def est_redzone(titre):
    titre_compact = re.sub(
        r"[^a-z0-9]",
        "",
        titre.casefold(),
    )

    return (
        "redzone"
        in titre_compact
    )


def enrichir_lieux(
    diffusions,
):
    cache_lieux = {}

    for diffusion in diffusions:
        if est_redzone(
            diffusion["titre"]
        ):
            diffusion["lieu"] = None
            continue

        diffusion["lieu"] = (
            recuperer_lieu_page_match(
                diffusion["lien"],
                cache_lieux,
            )
        )

    return diffusions


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


def plier_ligne_ics(ligne):
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


def recuperer_dtstamp_existant(
    fichier,
):
    try:
        with open(
            fichier,
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

    except (
        OSError,
        ValueError,
    ):
        pass

    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def duree_diffusion(
    diffusion,
    sport,
):
    if (
        sport["prefixe"]
        == "NFL"
        and est_redzone(
            diffusion["titre"]
        )
    ):
        return 420

    return sport[
        "duree_minutes"
    ]


def construire_evenement(
    diffusion,
    sport,
    dtstamp,
):
    debut = diffusion[
        "debut"
    ]

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

    resume = (
        f"{sport['emoji']} "
        f"{sport['prefixe']} — "
        f"{diffusion['titre']}"
    )

    description = (
        f"Diffusion en direct : "
        f"{chaines}"
    )

    if lieu:
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
        f"\nSource : "
        f"{diffusion['lien']}"
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
            f"UID:"
            f"{sport['prefixe'].lower()}-"
            f"{empreinte}"
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
            f"{echapper_ics(description)}"
        ),
    ]

    # IMPORTANT :
    # uniquement un vrai lieu physique ici.
    # Jamais la chaîne TV.
    if lieu:
        lignes.append(
            "LOCATION:"
            + echapper_ics(
                lieu
            )
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
    dtstamp = (
        recuperer_dtstamp_existant(
            sport["fichier"]
        )
    )

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

    for diffusion in diffusions:
        lignes.extend(
            construire_evenement(
                diffusion,
                sport,
                dtstamp,
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


def traiter_sport(sport):
    print(
        f"Téléchargement de "
        f"{sport['nom']}…"
    )

    try:
        page = recuperer_page(
            sport["url"],
            tentatives=3,
        )

        diffusions = (
            extraire_diffusions(
                page,
                sport,
            )
        )

    except (
        requests.RequestException,
        RuntimeError,
    ) as erreur:
        print(
            f"AVERTISSEMENT : "
            f"impossible de récupérer "
            f"{sport['prefixe']} : "
            f"{erreur}"
        )

        print(
            f"Le fichier "
            f"{sport['fichier']} "
            f"existant est conservé."
        )

        return False

    if not diffusions:
        print(
            f"AVERTISSEMENT : "
            f"aucune diffusion "
            f"{sport['prefixe']} "
            f"beIN reconnue."
        )

        print(
            f"Le fichier "
            f"{sport['fichier']} "
            f"existant est conservé "
            f"pour éviter de vider "
            f"le calendrier sur Apple."
        )

        return False

    diffusions = enrichir_lieux(
        diffusions
    )

    ecrire_calendrier(
        diffusions,
        sport,
    )

    print(
        f"{len(diffusions)} "
        f"diffusion(s) écrite(s) "
        f"dans "
        f"{sport['fichier']}."
    )

    for diffusion in diffusions:
        lieu = diffusion.get(
            "lieu"
        )

        if lieu:
            suffixe_lieu = (
                f" — 📍 {lieu}"
            )

        elif est_redzone(
            diffusion["titre"]
        ):
            suffixe_lieu = (
                " — 📍 plusieurs matchs"
            )

        else:
            suffixe_lieu = (
                " — 📍 lieu à confirmer"
            )

        print(
            f"  "
            f"{diffusion['debut']:%Y-%m-%d %H:%M} UTC — "
            f"{diffusion['titre']} — "
            f"{' / '.join(diffusion['chaines'])}"
            f"{suffixe_lieu}"
        )

    return True


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
