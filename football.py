import re

import requests


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
            elif suivant == ",":
                resultat.append(",")
            elif suivant == ";":
                resultat.append(";")
            elif suivant == "\\":
                resultat.append("\\")
            else:
                resultat.append(suivant)

            index += 2
            continue

        resultat.append(caractere)
        index += 1

    return "".join(resultat)


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
            resultat.append(ligne)

    return resultat


def valeur_propriete(lignes, propriete):
    motif = re.compile(
        rf"^{re.escape(propriete)}(?:;[^:]*)?:(.*)$"
    )

    for ligne in lignes:
        correspondance = motif.match(ligne)

        if correspondance:
            return correspondance.group(1)

    return None


def extraire_infos_description(description):
    if not description:
        return None

    description = deschapper_ics(description)

    premiere_ligne = description.splitlines()[0].strip()

    premiere_ligne = re.sub(
        r"^\[[^\]]+\]\s*",
        "",
        premiere_ligne,
    )

    parties = [
        partie.strip()
        for partie in premiere_ligne.split(" | ")
        if partie.strip()
    ]

    if len(parties) < 2:
        return None

    match = parties[0]

    competition_brute = parties[1]

    correspondance = re.match(
        r"^Football\s*-\s*(.+)$",
        competition_brute,
        flags=re.IGNORECASE,
    )

    if correspondance:
        competition = correspondance.group(1).strip()
    else:
        competition = competition_brute.strip()

    chaines = []

    if len(parties) >= 3:
        for chaine in parties[2:]:
            chaine = chaine.strip()

            if chaine and chaine not in chaines:
                chaines.append(chaine)

    return {
        "match": match,
        "competition": competition,
        "chaines": chaines,
    }


def lire_dtstamps_existants(fichier):
    try:
        with open(
            fichier,
            encoding="utf-8",
        ) as calendrier:
            lignes = deplier_ics(
                calendrier.read()
            )
    except OSError:
        return {}

    resultat = {}
    evenement = []
    dans_evenement = False

    for ligne in lignes:
        if ligne == "BEGIN:VEVENT":
            evenement = [ligne]
            dans_evenement = True
            continue

        if dans_evenement:
            evenement.append(ligne)

        if ligne == "END:VEVENT" and dans_evenement:
            uid = valeur_propriete(
                evenement,
                "UID",
            )

            dtstamp = valeur_propriete(
                evenement,
                "DTSTAMP",
            )

            if uid and dtstamp:
                resultat[uid] = dtstamp

            evenement = []
            dans_evenement = False

    return resultat


def transformer_evenement(
    lignes,
    equipe,
    dtstamps_existants,
):
    uid = valeur_propriete(
        lignes,
        "UID",
    )

    description = valeur_propriete(
        lignes,
        "DESCRIPTION",
    )

    url = valeur_propriete(
        lignes,
        "URL",
    )

    infos = extraire_infos_description(
        description
    )

    if infos is None:
        raise RuntimeError(
            f"Impossible d'analyser l'événement "
            f"{uid or 'sans UID'} de {equipe['nom']}."
        )

    match = infos["match"]
    competition = infos["competition"]
    chaines = infos["chaines"]

    # Pour la Ligue 1 2026-2027, les matchs sont diffusés
    # sur Ligue 1+. Si TV-Sports n'a pas encore renseigné
    # la chaîne individuellement, on la complète automatiquement.
    if (
        not chaines
        and competition.strip().casefold() == "ligue 1"
    ):
        chaines = ["Ligue 1+"]

    diffusion = (
        " / ".join(chaines)
        if chaines
        else "À confirmer"
    )

    resume = (
        f"{equipe['emoji']} "
        f"{equipe['nom']} — "
        f"{match} — "
        f"{competition}"
    )

    if chaines:
        resume += f" — 📺 {diffusion}"

    description_finale = (
        f"Compétition : {competition}\n"
        f"Diffusion TV : {diffusion}"
    )

    if url:
        description_finale += (
            f"\n\nVoir sur TV Sports : {url}"
        )

    resultat = []

    resume_remplace = False
    description_remplacee = False

    for ligne in lignes:
        if re.match(
            r"^SUMMARY(?:;[^:]*)?:",
            ligne,
        ):
            resultat.append(
                f"SUMMARY:{echapper_ics(resume)}"
            )
            resume_remplace = True
            continue

        if re.match(
            r"^DESCRIPTION(?:;[^:]*)?:",
            ligne,
        ):
            resultat.append(
                "DESCRIPTION:"
                + echapper_ics(
                    description_finale
                )
            )
            description_remplacee = True
            continue

        if (
            ligne.startswith("DTSTAMP:")
            and uid
            and uid in dtstamps_existants
        ):
            resultat.append(
                "DTSTAMP:"
                + dtstamps_existants[uid]
            )
            continue

        if ligne == "END:VEVENT":
            if not resume_remplace:
                resultat.append(
                    f"SUMMARY:{echapper_ics(resume)}"
                )

            if not description_remplacee:
                resultat.append(
                    "DESCRIPTION:"
                    + echapper_ics(
                        description_finale
                    )
                )

        resultat.append(ligne)

    return resultat, {
        "match": match,
        "competition": competition,
        "diffusion": diffusion,
    }


def modifier_calendrier(
    texte,
    equipe,
    dtstamps_existants,
):
    lignes = deplier_ics(texte)

    resultat = []
    evenement = []
    dans_evenement = False

    infos_evenements = []

    nom_calendrier_trouve = False

    for ligne in lignes:
        if ligne == "BEGIN:VEVENT":
            dans_evenement = True
            evenement = [ligne]
            continue

        if dans_evenement:
            evenement.append(ligne)

            if ligne == "END:VEVENT":
                evenement_modifie, infos = (
                    transformer_evenement(
                        evenement,
                        equipe,
                        dtstamps_existants,
                    )
                )

                resultat.extend(
                    evenement_modifie
                )

                infos_evenements.append(
                    infos
                )

                evenement = []
                dans_evenement = False

            continue

        if ligne.startswith("X-WR-CALNAME"):
            resultat.append(
                "X-WR-CALNAME:"
                + equipe["nom_calendrier"]
            )
            nom_calendrier_trouve = True
            continue

        if ligne:
            resultat.append(ligne)

    if dans_evenement:
        raise RuntimeError(
            f"Événement ICS incomplet pour "
            f"{equipe['nom']}."
        )

    if not infos_evenements:
        raise RuntimeError(
            f"Aucun événement trouvé dans "
            f"le calendrier {equipe['nom']}."
        )

    if not nom_calendrier_trouve:
        position = 1

        for index, ligne in enumerate(
            resultat
        ):
            if ligne == "VERSION:2.0":
                position = index + 1
                break

        resultat.insert(
            position,
            "X-WR-CALNAME:"
            + equipe["nom_calendrier"],
        )

    lignes_pliees = []

    for ligne in resultat:
        lignes_pliees.extend(
            plier_ligne_ics(ligne)
        )

    calendrier = (
        "\r\n".join(lignes_pliees)
        + "\r\n"
    )

    return calendrier, infos_evenements


def recuperer_calendrier(equipe):
    reponse = requests.get(
        equipe["url"],
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

    dtstamps_existants = (
        lire_dtstamps_existants(
            equipe["fichier"]
        )
    )

    calendrier_source = (
        recuperer_calendrier(
            equipe
        )
    )

    calendrier_final, evenements = (
        modifier_calendrier(
            calendrier_source,
            equipe,
            dtstamps_existants,
        )
    )

    with open(
        equipe["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as fichier:
        fichier.write(
            calendrier_final
        )

    print(
        f"{len(evenements)} événement(s) "
        f"écrit(s) dans "
        f"{equipe['fichier']}."
    )

    for evenement in evenements:
        ligne = (
            f"  {equipe['emoji']} "
            f"{equipe['nom']} — "
            f"{evenement['match']} — "
            f"{evenement['competition']}"
        )

        if evenement["diffusion"] != "À confirmer":
            ligne += (
                f" — 📺 "
                f"{evenement['diffusion']}"
            )

        else:
            ligne += " — TV à confirmer"

        print(ligne)


def main():
    for equipe in EQUIPES:
        traiter_equipe(equipe)


if __name__ == "__main__":
    main()
