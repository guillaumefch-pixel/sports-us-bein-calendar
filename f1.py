from pathlib import Path

f1_code = '''import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# =============================================================================
# CONFIGURATION
# =============================================================================

F1_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"
TV_SPORTS_URL = "https://tv-sports.fr/formule-1/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

NOMS_SESSIONS = {
    "fp1": "Essais libres 1",
    "fp2": "Essais libres 2",
    "fp3": "Essais libres 3",
    "sprintQualifying": "Qualifications Sprint",
    "sprint": "Sprint",
    "qualifying": "Qualifications",
    "gp": "Grand Prix",
}

DUREES_MINUTES = {
    "fp1": 60,
    "fp2": 60,
    "fp3": 60,
    "sprintQualifying": 60,
    "sprint": 60,
    "qualifying": 60,
    "gp": 120,
}

# Une diffusion Canal+ commence généralement quelques minutes avant la session.
# 90 minutes est assez large pour absorber l'avant-course sans confondre
# deux séances différentes du même week-end.
FENETRE_RAPPROCHEMENT = 90 * 60

# Chaînes acceptées.
# "Canal+" couvre Canal+, Canal+ Sport, Canal+ Sport 360, etc.
PREFIXE_CHAINE = "canal+"


# =============================================================================
# OUTILS
# =============================================================================

def titre(texte):
    print()
    print("=" * 90)
    print(texte)
    print("=" * 90)


def echapper_ics(texte):
    return (
        str(texte)
        .replace("\\\\", "\\\\\\\\")
        .replace(",", "\\\\,")
        .replace(";", "\\\\;")
        .replace("\\n", "\\\\n")
    )


def plier_ligne_ics(ligne):
    """
    RFC 5545 : une ligne iCalendar ne devrait pas dépasser 75 octets.
    On replie proprement les longues lignes UTF-8.
    """
    morceaux = []
    courant = ""

    for caractere in ligne:
        test = courant + caractere
        limite = 75 if not morceaux else 74

        if len(test.encode("utf-8")) > limite:
            morceaux.append(courant)
            courant = caractere
        else:
            courant = test

    morceaux.append(courant)

    if len(morceaux) == 1:
        return morceaux

    return [morceaux[0]] + [" " + morceau for morceau in morceaux[1:]]


# =============================================================================
# SPORTSTIMES : CALENDRIER SPORTIF F1
# =============================================================================

def recuperer_calendrier_f1():
    reponse = requests.get(F1_URL, timeout=20)
    reponse.raise_for_status()
    return reponse.json()["races"]


def extraire_toutes_les_sessions(courses):
    sessions = []

    for course in courses:
        for cle, valeur_iso in course["sessions"].items():
            horaire = datetime.fromisoformat(
                valeur_iso.replace("Z", "+00:00")
            ).astimezone(timezone.utc)

            sessions.append({
                "course": course,
                "cle": cle,
                "nom": NOMS_SESSIONS.get(cle, cle),
                "horaire": horaire,
                "duree_minutes": DUREES_MINUTES.get(cle, 60),
                "diffusions": [],
            })

    sessions.sort(key=lambda s: s["horaire"])
    return sessions


# =============================================================================
# TV-SPORTS : TOUS LES DIRECTS F1 CANAL+
# =============================================================================

def recuperer_diffusions_tv():
    reponse = requests.get(
        TV_SPORTS_URL,
        headers=HEADERS,
        timeout=20,
    )
    reponse.raise_for_status()

    soup = BeautifulSoup(reponse.text, "html.parser")

    evenements = []

    # Le site marque directement les événements F1 avec data-sport-id="102".
    # data-is-live="1" permet d'écarter magazines et rediffusions.
    blocs = soup.select(
        'li.schedule-item[data-sport-id="102"][data-is-live="1"]'
    )

    for bloc in blocs:
        time_element = bloc.select_one("time.schedule-time")

        if not time_element:
            continue

        valeur_datetime = time_element.get("datetime")

        if not valeur_datetime:
            continue

        try:
            horaire = datetime.fromisoformat(
                valeur_datetime
            ).astimezone(timezone.utc)
        except ValueError:
            continue

        chaines = []

        for chaine_element in bloc.select(".schedule-channel__item"):
            nom = ""

            image = chaine_element.select_one("img[alt]")
            if image and image.get("alt"):
                nom = image.get("alt", "").strip()

            if not nom:
                nom_element = chaine_element.select_one(
                    ".schedule-channel__name"
                )
                if nom_element:
                    nom = nom_element.get_text(" ", strip=True)

            if nom and nom.lower().startswith(PREFIXE_CHAINE):
                chaines.append(nom)

        # Pas une diffusion Canal+ : on l'ignore.
        if not chaines:
            continue

        # Nom du programme.
        programme = ""

        liens_programme = bloc.select(
            ".schedule-program__body a"
        )

        for lien in liens_programme:
            texte = lien.get_text(" ", strip=True)
            if texte and "formule 1" not in texte.lower():
                programme = texte
                break

        if not programme:
            programme = "Formule 1"

        # Lien vers la fiche de diffusion.
        lien = ""

        for a in bloc.select("a[href]"):
            href = a.get("href", "")

            if (
                "-tv-x" in href
                or "-e" in href
            ):
                if href.startswith("/"):
                    lien = "https://tv-sports.fr" + href
                else:
                    lien = href
                break

        evenements.append({
            "horaire": horaire,
            "programme": programme,
            "chaines": sorted(set(chaines)),
            "lien": lien,
        })

    # Déduplication exacte.
    uniques = []
    signatures = set()

    for evenement in evenements:
        signature = (
            evenement["horaire"],
            tuple(evenement["chaines"]),
            evenement["lien"],
        )

        if signature in signatures:
            continue

        signatures.add(signature)
        uniques.append(evenement)

    uniques.sort(key=lambda e: e["horaire"])
    return uniques


# =============================================================================
# RAPPROCHEMENT TV -> SESSION F1
# =============================================================================

def associer_diffusions(sessions, diffusions):
    """
    Chaque diffusion TV est attribuée à UNE SEULE session :
    la session F1 chronologiquement la plus proche dans une fenêtre de 90 min.

    Une session peut en revanche recevoir plusieurs diffusions distinctes
    si elle passe sur plusieurs chaînes Canal+.
    """

    associations = 0

    for diffusion in diffusions:
        candidats = []

        for session in sessions:
            ecart = abs(
                (
                    diffusion["horaire"]
                    - session["horaire"]
                ).total_seconds()
            )

            if ecart <= FENETRE_RAPPROCHEMENT:
                candidats.append((ecart, session))

        if not candidats:
            continue

        candidats.sort(key=lambda x: x[0])
        _, session = candidats[0]

        session["diffusions"].append(diffusion)
        associations += 1

    # Déduplique d'éventuels doublons par session.
    for session in sessions:
        uniques = []
        signatures = set()

        for diffusion in session["diffusions"]:
            signature = (
                diffusion["horaire"],
                tuple(diffusion["chaines"]),
                diffusion["lien"],
            )

            if signature in signatures:
                continue

            signatures.add(signature)
            uniques.append(diffusion)

        session["diffusions"] = uniques

    return associations


# =============================================================================
# ICS
# =============================================================================

def construire_vevent(session, dtstamp):
    course = session["course"]
    debut = session["horaire"]
    fin = debut + timedelta(
        minutes=session["duree_minutes"]
    )

    summary = (
        f"F1 - {course['location']} - {session['nom']}"
    )

    description_lignes = [
        f"Grand Prix : {course['name']} ({course['location']})"
    ]

    if session["diffusions"]:
        for diffusion in session["diffusions"]:
            chaines = ", ".join(diffusion["chaines"])

            # Heure du début de la diffusion TV en UTC.
            # L'application calendrier la convertira automatiquement.
            heure_tv = diffusion["horaire"].strftime(
                "%d/%m/%Y %H:%M UTC"
            )

            description_lignes.append(
                f"Diffusion : {chaines} - {heure_tv}"
            )

            if diffusion["lien"]:
                description_lignes.append(
                    diffusion["lien"]
                )
    else:
        description_lignes.append(
            "Diffusion TV : non trouvée / pas encore publiée"
        )

    uid = (
        f"f1-{course['round']}-{session['cle']}"
        "@sports-us-bein-calendar"
    )

    lignes = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{debut.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{fin.strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{echapper_ics(summary)}",
        (
            "DESCRIPTION:"
            + echapper_ics(
                "\\n".join(description_lignes)
            )
        ),
        f"LOCATION:{echapper_ics(course['location'])}",
        "END:VEVENT",
    ]

    resultat = []

    for ligne in lignes:
        resultat.extend(plier_ligne_ics(ligne))

    return resultat


# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================

def main():
    titre(
        "🏎️ GÉNÉRATION DU CALENDRIER F1 2026 "
        "(sessions + directs Canal+)"
    )

    print()
    print("📡 Téléchargement du calendrier F1...")
    courses = recuperer_calendrier_f1()
    sessions = extraire_toutes_les_sessions(courses)

    print(f"  {len(courses)} Grands Prix trouvés.")
    print(f"  {len(sessions)} sessions trouvées.")

    print()
    print("📺 Lecture des directs F1 sur TV-Sports...")
    diffusions = recuperer_diffusions_tv()

    print(
        f"  {len(diffusions)} diffusion(s) Canal+ "
        "en direct trouvée(s) actuellement."
    )

    associations = associer_diffusions(
        sessions,
        diffusions,
    )

    print(
        f"  {associations} diffusion(s) associée(s) "
        "à une session F1."
    )

    print()
    print("-" * 90)
    print("DIFFUSIONS ASSOCIÉES")
    print("-" * 90)

    sessions_avec_tv = 0

    for session in sessions:
        if not session["diffusions"]:
            continue

        sessions_avec_tv += 1

        print()
        print(
            f"🏁 Round {session['course']['round']:02d} "
            f"- {session['course']['location']} "
            f"- {session['nom']}"
        )

        print(
            "   Session : "
            + session["horaire"].strftime(
                "%d/%m/%Y %H:%M UTC"
            )
        )

        for diffusion in session["diffusions"]:
            ecart_minutes = int(
                (
                    session["horaire"]
                    - diffusion["horaire"]
                ).total_seconds()
                / 60
            )

            print(
                "   📺 "
                + ", ".join(diffusion["chaines"])
                + " | "
                + diffusion["horaire"].strftime(
                    "%d/%m/%Y %H:%M UTC"
                )
                + f" | début TV {ecart_minutes} min avant la session"
            )

    dtstamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    lignes_ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//sports-us-bein-calendar//F1 2026//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:F1 2026",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for session in sessions:
        lignes_ics.extend(
            construire_vevent(
                session,
                dtstamp,
            )
        )

    lignes_ics.append("END:VCALENDAR")

    with open(
        "f1_calendar.ics",
        "w",
        encoding="utf-8",
        newline="",
    ) as fichier:
        fichier.write(
            "\\r\\n".join(lignes_ics)
            + "\\r\\n"
        )

    titre("✅ TERMINÉ")

    print(f"Grands Prix            : {len(courses)}")
    print(f"Sessions générées      : {len(sessions)}")
    print(f"Sessions avec TV       : {sessions_avec_tv}")
    print(f"Diffusions Canal+      : {associations}")
    print("Fichier écrit          : f1_calendar.ics")


if __name__ == "__main__":
    main()
'''

workflow = '''name: Test du calendrier

on:
  workflow_dispatch:
  schedule:
    - cron: "17 */6 * * *"

permissions:
  contents: write

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Récupérer nos fichiers
        uses: actions/checkout@v6

      - name: Installer Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Installer les bibliothèques
        run: pip install requests beautifulsoup4

      - name: Générer le calendrier F1
        run: python f1.py

      - name: Enregistrer le calendrier mis à jour
        run: |
          git config user.name "github-actions[
