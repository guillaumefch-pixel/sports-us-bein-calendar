import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests


VERSION_SCRIPT = "2026-08-22-history-dedupe-v3"

EN_TETES = {
    "User-Agent": "Mozilla/5.0 (compatible; SportsCalendarBot/1.0)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

EQUIPES = (
    {
        "nom": "PSG",
        "emoji": "⚽",
        "url": "https://tv-sports.fr/calendrier/equipe/1/psg?direct=1",
        "fichier": "psg_calendar.ics",
        "nom_calendrier": "PSG — Tous les matchs",
    },
    {
        "nom": "France",
        "emoji": "🇫🇷",
        "url": "https://tv-sports.fr/calendrier/equipe/177/france?direct=1",
        "fichier": "france_calendar.ics",
        "nom_calendrier": "Équipe de France — Tous les matchs",
    },
)

# Corrections officielles connues qui doivent primer sur une ancienne donnée
# TV-Sports encore présente dans le même flux.
LIEUX_PSG_OFFICIELS = {
    (
        "20260823",
        frozenset(("psg", "rennes")),
    ): "Roazhon Park",
}

LIEUX_EDF_OFFICIELS = {
    "turquie - france": "Kocaeli Stadyumu, Kocaeli",
    "belgique - france": "King Baudouin Stadium, Bruxelles",
    "france - italie": "Stade de France, Saint-Denis",
    "france - belgique": "Stade de France, Saint-Denis",
    "italie - france": "San Siro, Milan",
    "france - turquie": "Stade Atlantique, Bordeaux",
}

STADES_FOOTBALL_FALLBACK = {
    "psg": "Parc des Princes",
    "lille": "Stade Pierre-Mauroy",
    "monaco": "Stade Louis II",
    "brest": "Stade Francis-Le Blé",
    "marseille": "Stade Orange Vélodrome",
    "le mans": "Stade Marie-Marvingt",
    "strasbourg": "Stade de la Meinau",
    "lyon": "Parc Olympique Lyonnais",
    "le havre": "Stade Océane",
    "troyes": "Stade de l'Aube",
    "nice": "Allianz Riviera",
    "lorient": "Stade du Moustoir",
    "toulouse": "Stadium de Toulouse",
    "paris fc": "Stade Jean Bouin",
    "lens": "Stade Bollaert-Delelis",
    "angers": "Stade Raymond-Kopa",
    "auxerre": "Stade de l'Abbé Deschamps",
    "rennes": "Roazhon Park",
}

STADES_NATIONAUX_FALLBACK = {
    "france": "Stade de France, Saint-Denis",
    "belgique": "King Baudouin Stadium, Bruxelles",
    "italie": "Stadio Olimpico, Rome",
    "turquie": "Atatürk Olimpiyat Stadyumu, Istanbul",
}


class AnalyseurTexteHTML(HTMLParser):
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


def echapper_ics(texte):
    return (
        str(texte)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


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


def deplier_ics(texte):
    lignes = texte.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    resultat = []

    for ligne in lignes:
        if ligne.startswith((" ", "\t")) and resultat:
            resultat[-1] += ligne[1:]
        else:
            resultat.append(ligne)

    return resultat


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


def parse_datetime_ics(valeur):
    if not valeur:
        return None

    for format_date in (
        "%Y%m%dT%H%M%SZ",
        "%Y%m%dT%H%M%S",
        "%Y%m%dT%H%M",
    ):
        try:
            resultat = datetime.strptime(valeur, format_date)
            return resultat.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def normaliser_nom(texte):
    return " ".join(str(texte or "").strip().casefold().replace("’", "'").split())


def normaliser_equipe(texte):
    nom = normaliser_nom(texte)

    alias = {
        "edf": "france",
        "paris sg": "psg",
        "paris-sg": "psg",
        "paris saint germain": "psg",
        "paris saint-germain": "psg",
        "paris saint-germain fc": "psg",
    }

    return alias.get(nom, nom)


def formater_match(match):
    match = re.sub(r"\s*/\s*", " - ", str(match or "").strip())
    return re.sub(r"\s+[–—-]\s+", " - ", match)


def extraire_equipes_match(match):
    match = formater_match(match)
    morceaux = re.split(r"\s+-\s+", match, maxsplit=1)

    if len(morceaux) != 2:
        return None, None

    return morceaux[0].strip(), morceaux[1].strip()


def cle_equipes_match(match):
    equipe_1, equipe_2 = extraire_equipes_match(match)
    if not equipe_1 or not equipe_2:
        return None

    return frozenset(
        (
            normaliser_equipe(equipe_1),
            normaliser_equipe(equipe_2),
        )
    )


def cle_match_ordonnee(match):
    return formater_match(match).casefold().replace("edf", "france")


def formater_match_affichage(equipe, match):
    match_formate = formater_match(match)
    if equipe["nom"] != "France":
        return match_formate

    domicile, exterieur = extraire_equipes_match(match_formate)
    if not domicile or not exterieur:
        return match_formate

    if normaliser_equipe(domicile) == "france":
        domicile = "EDF"
    if normaliser_equipe(exterieur) == "france":
        exterieur = "EDF"

    return f"{domicile} - {exterieur}"


def construire_resume(equipe, match, competition):
    return (
        f"{equipe['emoji']} {competition} : "
        f"{formater_match_affichage(equipe, match)}"
    )


def extraire_infos_description_source(description):
    if not description:
        return None

    premiere_ligne = deschapper_ics(description).splitlines()[0].strip()
    premiere_ligne = re.sub(r"^\[[^\]]+\]\s*", "", premiere_ligne)

    parties = [
        partie.strip()
        for partie in premiere_ligne.split(" | ")
        if partie.strip()
    ]

    if len(parties) < 2:
        return None

    match = formater_match(parties[0])
    competition_brute = parties[1]
    correspondance = re.match(
        r"^Football\s*-\s*(.+)$",
        competition_brute,
        flags=re.IGNORECASE,
    )
    competition = (
        correspondance.group(1).strip()
        if correspondance
        else competition_brute.strip()
    )

    chaines = []
    for chaine in parties[2:]:
        chaine = chaine.strip()
        if chaine and chaine not in chaines:
            chaines.append(chaine)

    return {
        "match": match,
        "competition": competition,
        "chaines": chaines,
    }


def determiner_diffusion(equipe, competition, chaines):
    if chaines:
        return " / ".join(chaines)

    if competition.strip().casefold() == "ligue 1":
        return "Ligue 1+"

    if (
        equipe["nom"] == "France"
        and competition.strip().casefold() == "uefa nations league"
    ):
        return "Groupe TF1 (chaîne à confirmer)"

    return "À confirmer"


def extraire_lieu_page_match(page):
    analyseur = AnalyseurTexteHTML()
    analyseur.feed(page)
    analyseur.close()
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

    for index, texte in enumerate(textes):
        if texte.strip().casefold() not in {"lieu", "stade"}:
            continue

        for suivant in textes[index + 1:]:
            suivant = suivant.strip()
            if not suivant:
                continue
            if suivant.casefold() in fins:
                return None
            return suivant

    return None


def recuperer_lieu_page_match(url, cache_lieux):
    if not url:
        return None

    if url in cache_lieux:
        return cache_lieux[url]

    try:
        reponse = requests.get(url, headers=EN_TETES, timeout=20)
        reponse.raise_for_status()
        lieu = extraire_lieu_page_match(reponse.text)
    except requests.RequestException:
        lieu = None

    cache_lieux[url] = lieu
    return lieu


def lieu_source_valide(lignes):
    valeur = valeur_propriete(lignes, "LOCATION")
    if not valeur:
        return None

    lieu = deschapper_ics(valeur).strip()
    if not lieu:
        return None

    compact = lieu.casefold()
    if compact.startswith(("bein sports", "canal+", "ligue 1+", "tf1")):
        return None

    return lieu


def lieu_officiel_exception(equipe, match, dtstart):
    debut = parse_datetime_ics(dtstart)
    if debut is None:
        return None

    if equipe["nom"] == "PSG":
        cle = (
            debut.strftime("%Y%m%d"),
            cle_equipes_match(match),
        )
        return LIEUX_PSG_OFFICIELS.get(cle)

    if equipe["nom"] == "France":
        return LIEUX_EDF_OFFICIELS.get(cle_match_ordonnee(match))

    return None


def stade_fallback(equipe, match):
    domicile, _ = extraire_equipes_match(match)
    if not domicile:
        return None

    domicile = normaliser_equipe(domicile)

    if equipe["nom"] == "PSG":
        return STADES_FOOTBALL_FALLBACK.get(domicile)

    if equipe["nom"] == "France":
        return STADES_NATIONAUX_FALLBACK.get(domicile)

    return None


def determiner_lieu(lignes, equipe, match, dtstart, url, cache_lieux):
    officiel = lieu_officiel_exception(equipe, match, dtstart)
    if officiel:
        return officiel, "officiel"

    source = lieu_source_valide(lignes)
    if source:
        return source, "source"

    lieu_page = recuperer_lieu_page_match(url, cache_lieux)
    if lieu_page:
        return lieu_page, "source"

    fallback = stade_fallback(equipe, match)
    if fallback:
        return fallback, "estimation"

    return None, None


def timestamp_dtstamp(valeur):
    date = parse_datetime_ics(valeur)
    if date is None:
        return 0.0
    return date.timestamp()


def parser_evenement_source(lignes, equipe, cache_lieux):
    uid = valeur_propriete(lignes, "UID")
    dtstart = valeur_propriete(lignes, "DTSTART")

    if not uid or not dtstart:
        return None

    infos = extraire_infos_description_source(
        valeur_propriete(lignes, "DESCRIPTION")
    )
    if infos is None:
        return None

    url_brute = valeur_propriete(lignes, "URL")
    url = deschapper_ics(url_brute).strip() if url_brute else None

    lieu, statut_lieu = determiner_lieu(
        lignes,
        equipe,
        infos["match"],
        dtstart,
        url,
        cache_lieux,
    )

    return {
        "uid": uid,
        "dtstamp": (
            valeur_propriete(lignes, "DTSTAMP")
            or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ),
        "dtstart": dtstart,
        "dtend": valeur_propriete(lignes, "DTEND"),
        "match": infos["match"],
        "competition": infos["competition"],
        "diffusion": determiner_diffusion(
            equipe,
            infos["competition"],
            infos["chaines"],
        ),
        "url": url,
        "lieu": lieu,
        "statut_lieu": statut_lieu,
    }


def parser_evenement_existant(lignes, equipe):
    uid = valeur_propriete(lignes, "UID")
    dtstart = valeur_propriete(lignes, "DTSTART")
    summary_brut = valeur_propriete(lignes, "SUMMARY")

    if not uid or not dtstart or not summary_brut:
        return None

    summary = deschapper_ics(summary_brut).strip()
    if ":" not in summary:
        return None

    gauche, match = summary.split(":", 1)
    competition = gauche.strip()
    prefixe = equipe["emoji"] + " "
    if competition.startswith(prefixe):
        competition = competition[len(prefixe):].strip()

    match = formater_match(match.strip())
    if equipe["nom"] == "France":
        domicile, exterieur = extraire_equipes_match(match)
        if domicile and exterieur:
            if domicile.casefold() == "edf":
                domicile = "France"
            if exterieur.casefold() == "edf":
                exterieur = "France"
            match = f"{domicile} - {exterieur}"

    description = valeur_propriete(lignes, "DESCRIPTION")
    diffusion = deschapper_ics(description).strip() if description else "À confirmer"

    lieu_brut = valeur_propriete(lignes, "LOCATION")
    lieu = deschapper_ics(lieu_brut).strip() if lieu_brut else None

    url_brute = valeur_propriete(lignes, "URL")
    url = deschapper_ics(url_brute).strip() if url_brute else None

    return {
        "uid": uid,
        "dtstamp": (
            valeur_propriete(lignes, "DTSTAMP")
            or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ),
        "dtstart": dtstart,
        "dtend": valeur_propriete(lignes, "DTEND"),
        "match": match,
        "competition": competition,
        "diffusion": diffusion,
        "url": url,
        "lieu": lieu,
        "statut_lieu": "conserve" if lieu else None,
    }


def charger_evenements_existants(fichier, equipe):
    try:
        with open(fichier, encoding="utf-8") as calendrier:
            sources = extraire_evenements_ics(calendrier.read())
    except OSError:
        return []

    resultat = []
    for source in sources:
        evenement = parser_evenement_existant(source, equipe)
        if evenement:
            resultat.append(evenement)

    return resultat


def meme_fixture(evenement_1, evenement_2):
    if evenement_1.get("uid") and evenement_1.get("uid") == evenement_2.get("uid"):
        return True

    cle_1 = cle_equipes_match(evenement_1.get("match"))
    cle_2 = cle_equipes_match(evenement_2.get("match"))
    if cle_1 is None or cle_1 != cle_2:
        return False

    debut_1 = parse_datetime_ics(evenement_1.get("dtstart"))
    debut_2 = parse_datetime_ics(evenement_2.get("dtstart"))
    if debut_1 is None or debut_2 is None:
        return False

    # Une inversion domicile/extérieur ou un programme TV commençant quelques
    # minutes avant le coup d'envoi ne doit jamais créer un deuxième match.
    return abs((debut_1 - debut_2).total_seconds()) <= 12 * 60 * 60


def evenement_est_passe(evenement, maintenant=None):
    maintenant = maintenant or datetime.now(timezone.utc)
    fin = parse_datetime_ics(
        evenement.get("dtend") or evenement.get("dtstart")
    )
    return fin is not None and fin <= maintenant


def choisir_identite_canonique(groupe):
    evenements_fixture = [
        evenement
        for evenement in groupe
        if str(evenement.get("uid", "")).startswith("event-")
    ]

    candidats = evenements_fixture or groupe
    return max(
        candidats,
        key=lambda evenement: timestamp_dtstamp(evenement.get("dtstamp")),
    )


def fusionner_groupe_doublons(groupe, equipe):
    if len(groupe) == 1:
        return dict(groupe[0])

    identite = choisir_identite_canonique(groupe)
    recent = max(
        groupe,
        key=lambda evenement: timestamp_dtstamp(evenement.get("dtstamp")),
    )

    resultat = dict(identite)

    # On garde l'UID et l'horaire du vrai événement calendrier lorsque
    # TV-Sports fournit en parallèle un "episode-*" de diffusion TV.
    # En revanche les informations les plus récentes corrigent le match,
    # le lieu et la chaîne. C'est exactement le cas d'une inversion de stade.
    for cle in ("match", "competition", "diffusion", "url"):
        if recent.get(cle):
            resultat[cle] = recent[cle]

    lieux = [
        evenement
        for evenement in groupe
        if evenement.get("lieu")
    ]
    if lieux:
        meilleur_lieu = max(
            lieux,
            key=lambda evenement: (
                {
                    "officiel": 4,
                    "source": 3,
                    "conserve": 2,
                    "estimation": 1,
                    None: 0,
                }.get(evenement.get("statut_lieu"), 0),
                timestamp_dtstamp(evenement.get("dtstamp")),
            ),
        )
        resultat["lieu"] = meilleur_lieu["lieu"]
        resultat["statut_lieu"] = meilleur_lieu.get("statut_lieu")

    # L'exception officielle PSG-Rennes prime même si une vieille entrée
    # source avec le Parc des Princes est encore présente.
    officiel = lieu_officiel_exception(
        equipe,
        resultat.get("match"),
        resultat.get("dtstart"),
    )
    if officiel:
        resultat["lieu"] = officiel
        resultat["statut_lieu"] = "officiel"

    resultat["dtstamp"] = max(
        (
            evenement.get("dtstamp")
            for evenement in groupe
            if evenement.get("dtstamp")
        ),
        key=timestamp_dtstamp,
        default=resultat.get("dtstamp"),
    )

    return resultat


def dedupliquer_evenements(evenements, equipe):
    groupes = []

    for evenement in sorted(
        evenements,
        key=lambda item: item.get("dtstart", ""),
    ):
        groupe_trouve = None

        for groupe in groupes:
            if meme_fixture(groupe[0], evenement):
                groupe_trouve = groupe
                break

        if groupe_trouve is None:
            groupes.append([evenement])
        else:
            groupe_trouve.append(evenement)

    resultat = [
        fusionner_groupe_doublons(groupe, equipe)
        for groupe in groupes
    ]
    resultat.sort(key=lambda item: item.get("dtstart", ""))
    return resultat


def fusionner_avec_historique(evenements_frais, evenements_existants, equipe):
    frais = dedupliquer_evenements(evenements_frais, equipe)
    anciens = dedupliquer_evenements(evenements_existants, equipe)
    resultat = []
    maintenant = datetime.now(timezone.utc)

    for nouveau in frais:
        precedent = next(
            (
                ancien
                for ancien in anciens
                if meme_fixture(ancien, nouveau)
            ),
            None,
        )

        copie = dict(nouveau)
        if precedent:
            # UID stable : une modification d'horaire, de stade ou même une
            # inversion domicile/extérieur met à jour le même événement Apple.
            copie["uid"] = precedent["uid"]

            # Si la nouvelle source n'a momentanément plus un champ secondaire,
            # on ne jette pas une information déjà connue.
            for cle in ("lieu", "url", "dtend"):
                if not copie.get(cle) and precedent.get(cle):
                    copie[cle] = precedent[cle]

        resultat.append(copie)

    # Tout ce qui est déjà passé devient de l'historique permanent, même si
    # TV-Sports ne le renvoie plus lors des runs suivants.
    for ancien in anciens:
        if not evenement_est_passe(ancien, maintenant):
            continue

        if any(meme_fixture(ancien, actuel) for actuel in resultat):
            continue

        resultat.append(dict(ancien))

    resultat = dedupliquer_evenements(resultat, equipe)
    resultat.sort(key=lambda item: item.get("dtstart", ""))
    return resultat


def construire_evenement(evenement, equipe):
    resume = construire_resume(
        equipe,
        evenement["match"],
        evenement["competition"],
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
            "DESCRIPTION:" + echapper_ics(evenement["diffusion"]),
        ]
    )

    if evenement.get("url"):
        lignes.append("URL:" + evenement["url"])

    if evenement.get("lieu"):
        lignes.append("LOCATION:" + echapper_ics(evenement["lieu"]))

    lignes.extend(
        [
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]
    )

    return lignes


def ecrire_calendrier(evenements, equipe):
    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "PRODID:-//sports-us-bein-calendar//Football//FR",
        "X-WR-CALNAME:" + echapper_ics(equipe["nom_calendrier"]),
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for evenement in evenements:
        lignes.extend(construire_evenement(evenement, equipe))

    lignes.append("END:VCALENDAR")

    lignes_pliees = []
    for ligne in lignes:
        lignes_pliees.extend(plier_ligne_ics(ligne))

    with open(
        equipe["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as calendrier:
        calendrier.write("\r\n".join(lignes_pliees) + "\r\n")


def recuperer_calendrier(equipe):
    reponse = requests.get(
        equipe["url"],
        headers=EN_TETES,
        timeout=30,
    )
    reponse.raise_for_status()

    if "BEGIN:VCALENDAR" not in reponse.text:
        raise RuntimeError(
            f"Flux ICS {equipe['nom']} invalide."
        )

    return reponse.text


def afficher_evenements(evenements, equipe):
    for evenement in evenements:
        ligne = (
            "  "
            + construire_resume(
                equipe,
                evenement["match"],
                evenement["competition"],
            )
            + " — 📺 "
            + evenement["diffusion"]
        )

        if evenement.get("lieu"):
            ligne += " — 📍 " + evenement["lieu"]
            if evenement.get("statut_lieu") == "estimation":
                ligne += " (estimation)"
        else:
            ligne += " — 📍 lieu à confirmer"

        print(ligne)


def traiter_equipe(equipe):
    print(f"\nTéléchargement du calendrier {equipe['nom']}…")

    existants = charger_evenements_existants(
        equipe["fichier"],
        equipe,
    )

    try:
        calendrier_source = recuperer_calendrier(equipe)
    except (requests.RequestException, RuntimeError) as erreur:
        print(
            "  AVERTISSEMENT : source indisponible, "
            "le fichier existant est conservé : "
            f"{erreur}"
        )
        return False

    cache_lieux = {}
    frais = []

    for lignes in extraire_evenements_ics(calendrier_source):
        evenement = parser_evenement_source(
            lignes,
            equipe,
            cache_lieux,
        )
        if evenement:
            frais.append(evenement)

    if not frais:
        print(
            "  AVERTISSEMENT : aucun événement exploitable dans la source ; "
            "le fichier existant est conservé."
        )
        return False

    avant_dedup = len(frais)
    frais_dedup = dedupliquer_evenements(frais, equipe)
    doublons_supprimes = avant_dedup - len(frais_dedup)

    evenements = fusionner_avec_historique(
        frais_dedup,
        existants,
        equipe,
    )

    ecrire_calendrier(evenements, equipe)

    historique = sum(
        1
        for evenement in evenements
        if evenement_est_passe(evenement)
    )

    print(
        f"{len(evenements)} événement(s) écrit(s) dans {equipe['fichier']}."
    )
    print(f"  Historique conservé : {historique} événement(s) passé(s).")
    print(f"  Doublon(s) source fusionné(s) : {doublons_supprimes}.")

    afficher_evenements(evenements, equipe)
    return True


def main():
    print(f"Version football : {VERSION_SCRIPT}")

    for equipe in EQUIPES:
        traiter_equipe(equipe)


if __name__ == "__main__":
    main()
