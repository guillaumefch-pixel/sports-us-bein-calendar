import hashlib
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import requests


EN_TETES = {
    "User-Agent": "Mozilla/5.0 (compatible; SportsCalendarBot/1.0)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

EQUIPES = (
    {
        "nom": "PSG",
        "emoji": "⚽",
        "prefixe": "PSG",
        "url_calendrier": "https://tv-sports.fr/foot/psg/calendrier",
        "url_tv": "https://tv-sports.fr/foot/psg/match-direct",
        "fichier": "psg_calendar.ics",
        "nom_calendrier": "PSG — Tous les matchs",
    },
    {
        "nom": "France",
        "emoji": "🇫🇷",
        "prefixe": "FRANCE",
        "url_calendrier": "https://tv-sports.fr/foot/france/calendrier",
        "url_tv": "https://tv-sports.fr/foot/france/match-direct",
        "fichier": "france_calendar.ics",
        "nom_calendrier": "Équipe de France — Tous les matchs",
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
                    "chaines": [],
                    "liens": [],
                }
                self.profondeur_li = 1
            return

        if self.element is None:
            return

        if balise == "time" and attributs.get("datetime"):
            self.element["datetime"] = attributs["datetime"]

        elif balise == "img":
            alt = attributs.get("alt", "").strip()

            if "logoChaine" in classes and alt:
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
                participant = attributs.get("title", "").strip()
                if participant:
                    self.element["participants"].append(participant)

    def handle_startendtag(self, balise, attributs):
        self.handle_starttag(balise, attributs)

    def handle_data(self, donnees):
        if self.ancre is not None:
            self.ancre["texte"].append(donnees)

    def handle_endtag(self, balise):
        if balise == "a" and self.ancre is not None and self.element is not None:
            self.ancre["texte"] = " ".join(
                "".join(self.ancre["texte"]).split()
            )

            if (
                "schedule-participant" in self.ancre["classes"]
                and not self.ancre["title"]
                and self.ancre["texte"]
            ):
                self.element["participants"].append(self.ancre["texte"])

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


def normaliser(texte):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        texte.casefold()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("ç", "c"),
    )


def extraire_equipes_depuis_titre(element):
    for lien in element.get("liens", []):
        texte = lien["texte"].strip()

        if " – " in texte:
            morceaux = texte.split(" – ", 1)
            if len(morceaux) == 2:
                return [morceaux[0].strip(), morceaux[1].strip()]

        if " - " in texte:
            morceaux = texte.split(" - ", 1)
            if len(morceaux) == 2:
                return [morceaux[0].strip(), morceaux[1].strip()]

    return []


def choisir_participants(element):
    participants = []

    for participant in element.get("participants", []):
        participant = participant.strip()
        if participant and participant not in participants:
            participants.append(participant)

    if len(participants) >= 2:
        return participants[:2]

    secours = extraire_equipes_depuis_titre(element)
    if len(secours) >= 2:
        return secours[:2]

    return participants


def choisir_competition(element, participants):
    participants_normalises = {
        normaliser(participant)
        for participant in participants
    }

    ignores = {
        "football",
        "foot",
        "infos",
        "matchcenter",
        "direct",
        "avenir",
        "psg",
        "france",
    }

    for lien in element.get("liens", []):
        texte = lien["texte"].strip()

        if not texte:
            continue

        texte_normalise = normaliser(texte)

        if texte_normalise in ignores:
            continue

        if texte_normalise in participants_normalises:
            continue

        if " – " in texte or " - " in texte:
            continue

        if len(texte) > 80:
            continue

        # La compétition est généralement le premier lien pertinent
        # à l'intérieur du schedule-item.
        return texte

    return "Compétition à confirmer"


def choisir_lien(element, url_defaut):
    for lien in reversed(element.get("liens", [])):
        href = lien["href"]

        if not href:
            continue

        if (
            "-tv-" in href
            or re.search(r"-e\d+/?$", href)
            or "match" in href.casefold()
        ):
            if href.startswith("/"):
                return "https://tv-sports.fr" + href
            return href

    return url_defaut


def extraire_matchs(page, url_defaut):
    analyseur = AnalyseurPlanning()
    analyseur.feed(page)

    matchs = []

    for element in analyseur.elements:
        attributs = element.get("attributs", {})

        if attributs.get("data-is-past") == "1":
            continue

        try:
            debut = datetime.fromisoformat(
                element["datetime"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue

        participants = choisir_participants(element)

        if len(participants) < 2:
            continue

        competition = choisir_competition(
            element,
            participants,
        )

        matchs.append(
            {
                "debut": debut,
                "equipe1": participants[0],
                "equipe2": participants[1],
                "competition": competition,
                "chaines": list(element.get("chaines", [])),
                "lien": choisir_lien(element, url_defaut),
            }
        )

    return matchs


def cle_match(match):
    return (
        normaliser(match["equipe1"]),
        normaliser(match["equipe2"]),
        normaliser(match["competition"]),
    )


def fusionner_calendrier_et_tv(matchs, diffusions):
    resultat = []

    for match in matchs:
        match_final = dict(match)
        match_final["chaines"] = list(match["chaines"])

        candidats = []

        for diffusion in diffusions:
            if cle_match(diffusion) != cle_match(match):
                continue

            ecart = abs(
                (
                    diffusion["debut"]
                    - match["debut"]
                ).total_seconds()
            )

            # On accepte jusqu'à 6 h de différence,
            # utile si un horaire vient d'être reprogrammé.
            if ecart <= 6 * 60 * 60:
                candidats.append((ecart, diffusion))

        if candidats:
            _, diffusion = min(
                candidats,
                key=lambda valeur: valeur[0],
            )

            match_final["debut"] = diffusion["debut"]

            for chaine in diffusion["chaines"]:
                if chaine not in match_final["chaines"]:
                    match_final["chaines"].append(chaine)

            if diffusion["lien"]:
                match_final["lien"] = diffusion["lien"]

        resultat.append(match_final)

    return sorted(
        resultat,
        key=lambda match: match["debut"],
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
        with open(fichier, encoding="utf-8") as calendrier:
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


def construire_evenement(match, equipe, dtstamp):
    debut = match["debut"]

    # Deux heures pour un match de football.
    fin = debut + timedelta(minutes=120)

    affiche = (
        f"{match['equipe1']} – "
        f"{match['equipe2']}"
    )

    chaines = (
        " / ".join(match["chaines"])
        if match["chaines"]
        else "À confirmer"
    )

    resume = (
        f"{equipe['emoji']} "
        f"{equipe['nom']} — "
        f"{affiche} — "
        f"{match['competition']}"
    )

    description = (
        f"Compétition : {match['competition']}\n"
        f"Diffusion TV : {chaines}\n"
        f"Source : {match['lien']}"
    )

    empreinte = hashlib.sha256(
        (
            f"{equipe['prefixe']}|"
            f"{match['debut'].year}|"
            f"{normaliser(match['competition'])}|"
            f"{normaliser(match['equipe1'])}|"
            f"{normaliser(match['equipe2'])}"
        ).encode()
    ).hexdigest()[:24]

    return [
        "BEGIN:VEVENT",
        (
            f"UID:{equipe['prefixe'].lower()}-"
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
        f"DESCRIPTION:{echapper_ics(description)}",
        f"LOCATION:{echapper_ics(chaines)}",
        f"URL:{match['lien']}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
    ]


def ecrire_calendrier(matchs, equipe):
    dtstamp = recuperer_dtstamp_existant(
        equipe["fichier"]
    )

    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        (
            f"PRODID:-//sports-us-bein-calendar//"
            f"{equipe['prefixe']}//FR"
        ),
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        (
            f"X-WR-CALNAME:"
            f"{echapper_ics(equipe['nom_calendrier'])}"
        ),
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for match in matchs:
        lignes.extend(
            construire_evenement(
                match,
                equipe,
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
        equipe["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write(
            "\r\n".join(lignes_pliees)
            + "\r\n"
        )


def recuperer_page(url):
    reponse = requests.get(
        url,
        headers=EN_TETES,
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.text


def traiter_equipe(equipe):
    print(
        f"\nTéléchargement du calendrier "
        f"{equipe['nom']}…"
    )

    page_calendrier = recuperer_page(
        equipe["url_calendrier"]
    )

    matchs = extraire_matchs(
        page_calendrier,
        equipe["url_calendrier"],
    )

    print(
        f"{len(matchs)} match(s) trouvé(s) "
        f"dans le calendrier."
    )

    print(
        f"Téléchargement des diffusions TV "
        f"{equipe['nom']}…"
    )

    try:
        page_tv = recuperer_page(
            equipe["url_tv"]
        )

        diffusions = extraire_matchs(
            page_tv,
            equipe["url_tv"],
        )

    except requests.RequestException as erreur:
        print(
            f"Avertissement : page TV inaccessible "
            f"({erreur})."
        )
        diffusions = []

    matchs = fusionner_calendrier_et_tv(
        matchs,
        diffusions,
    )

    ecrire_calendrier(
        matchs,
        equipe,
    )

    print(
        f"{len(matchs)} match(s) écrit(s) dans "
        f"{equipe['fichier']}."
    )

    for match in matchs:
        chaines = (
            " / ".join(match["chaines"])
            if match["chaines"]
            else "TV à confirmer"
        )

        print(
            f"  "
            f"{match['debut']:%Y-%m-%d %H:%M} UTC — "
            f"{match['equipe1']} – "
            f"{match['equipe2']} — "
            f"{match['competition']} — "
            f"{chaines}"
        )


def main():
    for equipe in EQUIPES:
        traiter_equipe(equipe)


if __name__ == "__main__":
    main()
