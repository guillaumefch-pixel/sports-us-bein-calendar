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
    lignes = texte.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    ).split("\n")

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


def valeur_propriete(ligne):
    if ":" not in ligne:
        return ""

    return ligne.split(":", 1)[1]


def prefixer_resume(ligne, equipe):
    if ":" not in ligne:
        return ligne

    propriete, valeur = ligne.split(":", 1)

    prefixe = f"{equipe['emoji']} {equipe['nom']} — "

    # Évite de rajouter le préfixe plusieurs fois
    # lors des mises à jour successives.
    if valeur.startswith(prefixe):
        return ligne

    return f"{propriete}:{prefixe}{valeur}"


def modifier_calendrier(texte, equipe):
    lignes = deplier_ics(texte)

    resultat = []
    dans_evenement = False
    nom_calendrier_trouve = False
    nombre_evenements = 0

    resumes = []

    for ligne in lignes:
        if ligne == "BEGIN:VEVENT":
            dans_evenement = True
            nombre_evenements += 1

        elif ligne == "END:VEVENT":
            dans_evenement = False

        if ligne.startswith("X-WR-CALNAME"):
            resultat.append(
                f"X-WR-CALNAME:{equipe['nom_calendrier']}"
            )
            nom_calendrier_trouve = True
            continue

        if (
            dans_evenement
            and re.match(r"^SUMMARY(?:;[^:]*)?:", ligne)
        ):
            ligne = prefixer_resume(
                ligne,
                equipe,
            )

            resumes.append(
                valeur_propriete(ligne)
            )

        resultat.append(ligne)

    if nombre_evenements == 0:
        raise RuntimeError(
            f"Aucun événement trouvé dans le flux "
            f"TV-Sports de {equipe['nom']}."
        )

    if not nom_calendrier_trouve:
        position = 1

        for index, ligne in enumerate(resultat):
            if ligne == "VERSION:2.0":
                position = index + 1
                break

        resultat.insert(
            position,
            f"X-WR-CALNAME:{equipe['nom_calendrier']}",
        )

    lignes_pliees = []

    for ligne in resultat:
        lignes_pliees.extend(
            plier_ligne_ics(ligne)
        )

    return (
        "\r\n".join(lignes_pliees).rstrip()
        + "\r\n",
        nombre_evenements,
        resumes,
    )


def traiter_equipe(equipe):
    print(
        f"\nTéléchargement du calendrier "
        f"{equipe['nom']}…"
    )

    reponse = requests.get(
        equipe["url"],
        headers=EN_TETES,
        timeout=30,
    )

    reponse.raise_for_status()

    calendrier, nombre_evenements, resumes = (
        modifier_calendrier(
            reponse.text,
            equipe,
        )
    )

    with open(
        equipe["fichier"],
        "w",
        encoding="utf-8",
        newline="",
    ) as fichier:
        fichier.write(calendrier)

    print(
        f"{nombre_evenements} événement(s) écrit(s) "
        f"dans {equipe['fichier']}."
    )

    print("Événements trouvés :")

    for resume in resumes:
        print(f"  {resume}")


def main():
    for equipe in EQUIPES:
        traiter_equipe(equipe)


if __name__ == "__main__":
    main()
