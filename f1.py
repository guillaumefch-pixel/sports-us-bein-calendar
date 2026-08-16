import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

F1_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"
TV_URL = "https://tv-sports.fr/rss/competition/1434/grand-prix-des-pays-bas?direct=1"

NOMS_SESSIONS = {
    "fp1": "Essais libres 1",
    "fp2": "Essais libres 2",
    "fp3": "Essais libres 3",
    "sprintQualifying": "Sprint Qualifying",
    "sprint": "Sprint",
    "qualifying": "Qualifications",
    "gp": "Grand Prix",
}

FENETRE_SECONDES = 6 * 60 * 60  # ±6h de tolérance pour le rapprochement


def titre(texte):
    print()
    print("=" * 90)
    print(texte)
    print("=" * 90)


def recuperer_course_f1(nom_course="dutch"):
    reponse = requests.get(F1_URL, timeout=10)
    reponse.raise_for_status()
    data = reponse.json()

    for course in data["races"]:
        if course["name"].lower() == nom_course:
            return course

    raise RuntimeError(f"Course '{nom_course}' introuvable dans le calendrier F1.")


def extraire_sessions(course):
    sessions = []
    for cle, valeur_iso in course["sessions"].items():
        horaire = datetime.fromisoformat(valeur_iso.replace("Z", "+00:00"))
        sessions.append({
            "cle": cle,
            "nom": NOMS_SESSIONS.get(cle, cle),
            "horaire": horaire,
        })
    sessions.sort(key=lambda s: s["horaire"])
    return sessions


def recuperer_diffusions_tv():
    reponse = requests.get(TV_URL, timeout=10)
    reponse.raise_for_status()
    root = ET.fromstring(reponse.content)

    evenements = []
    for item in root.findall("./channel/item"):
        pub_date = item.findtext("pubDate")
        if not pub_date:
            continue

        horaire = datetime.strptime(
            pub_date, "%a, %d %b %Y %H:%M:%S %z"
        ).astimezone(timezone.utc)

        evenements.append({
            "titre": item.findtext("title", ""),
            "lien": item.findtext("link", ""),
            "horaire": horaire,
        })

    return evenements


def trouver_diffusions_proches(session, evenements_tv):
    candidats = []
    for evenement in evenements_tv:
        ecart = abs((evenement["horaire"] - session["horaire"]).total_seconds())
        if ecart <= FENETRE_SECONDES:
            candidats.append((ecart, evenement))
    candidats.sort(key=lambda c: c[0])
    return candidats


def main():
    titre("🏎️ TEST SPORTSTIMES F1 / TV-SPORTS")

    print()
    print("📡 Téléchargement du calendrier F1...")
    course = recuperer_course_f1()
    sessions = extraire_sessions(course)

    titre("GRAND PRIX")
    print("Nom   :", course["name"])
    print("Lieu  :", course["location"])
    print("Round :", course["round"])

    print()
    print("SESSIONS F1")
    print("-" * 90)
    for session in sessions:
        print(
            f"{session['nom']:<22} "
            f"{session['horaire'].strftime('%d/%m/%Y %H:%M')} UTC"
        )

    print()
    print("📡 Téléchargement du flux TV-Sports...")
    evenements_tv = recuperer_diffusions_tv()

    titre("DIFFUSIONS TV-SPORTS")
    if not evenements_tv:
        print("Aucune diffusion trouvée.")
    for evenement in evenements_tv:
        print(
            f"{evenement['horaire'].strftime('%d/%m/%Y %H:%M')} UTC"
            f" | {evenement['titre']}"
            f" | {evenement['lien']}"
        )

    titre("🔎 RAPPROCHEMENT F1 / TV-SPORTS (±6h)")
    for session in sessions:
        print("-" * 90)
        print(
            f"🏎️ {session['nom']} — "
            f"{session['horaire'].strftime('%d/%m/%Y %H:%M')} UTC"
        )

        candidats = trouver_diffusions_proches(session, evenements_tv)
        if not candidats:
            print("  ❌ Aucun candidat dans la fenêtre de ±6h")
            continue

        for ecart, evenement in candidats:
            heures = ecart / 3600
            print(
                f"  → {evenement['horaire'].strftime('%d/%m/%Y %H:%M')} UTC"
                f" | écart {heures:.1f} h"
                f" | {evenement['titre']}"
            )

    titre("✅ FIN DU TEST")


if __name__ == "__main__":
    main()
