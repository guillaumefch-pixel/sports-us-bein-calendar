import requests
from bs4 import BeautifulSoup


print("🔎 EXTRACTION DU WEEK-END F1")
print("=" * 80)


URL = "https://tv-sports.fr/formule-1/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}


# ============================================================
# TÉLÉCHARGEMENT
# ============================================================

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

response.raise_for_status()

print(
    f"✅ Page téléchargée : {len(response.text)} caractères"
)


soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# ============================================================
# RECHERCHE DES ÉVÉNEMENTS
# ============================================================

evenements = soup.select(
    "ol.schedule-list li.schedule-item"
)

print(
    f"📋 Événements trouvés : {len(evenements)}"
)


# ============================================================
# PÉRIODE DU WEEK-END
# ============================================================

DATES_WEEK_END = (
    "2026-08-21",
    "2026-08-22",
    "2026-08-23",
)


print()
print("=" * 80)
print("📺 DIFFUSIONS F1 CANAL+ EN DIRECT")
print("=" * 80)


resultats = []


# ============================================================
# ANALYSE
# ============================================================

for evenement in evenements:

    # --------------------------------------------------------
    # F1 uniquement
    # --------------------------------------------------------

    if evenement.get("data-sport-id") != "102":
        continue


    # --------------------------------------------------------
    # Date / heure
    # --------------------------------------------------------

    time_element = evenement.select_one(
        "time.schedule-time"
    )

    if not time_element:
        continue


    datetime_str = time_element.get("datetime")

    if not datetime_str:
        continue


    # --------------------------------------------------------
    # Uniquement le week-end du GP des Pays-Bas
    # --------------------------------------------------------

    if not datetime_str.startswith(DATES_WEEK_END):
        continue


    # --------------------------------------------------------
    # Uniquement les directs
    # --------------------------------------------------------

    if evenement.get("data-diffusion-type") != "live":
        continue


    # --------------------------------------------------------
    # Uniquement Canal+
    #
    # Canal+ = ID 81
    # --------------------------------------------------------

    if evenement.get("data-channel-id") != "81":
        continue


    # --------------------------------------------------------
    # Heure
    # --------------------------------------------------------

    heure_element = time_element.select_one(
        "strong"
    )

    if heure_element:

        heure = heure_element.get_text(
            " ",
            strip=True
        )

    else:

        heure = time_element.get_text(
            " ",
            strip=True
        )


    # --------------------------------------------------------
    # Titre
    # --------------------------------------------------------

    titre = None


    lien_competition = evenement.select_one(
        "a.schedule-entity-visual"
    )


    if lien_competition:

        titre = lien_competition.get(
            "title"
        )


    if not titre:

        lien = evenement.select_one(
            "a[title]"
        )

        if lien:

            titre = lien.get(
                "title"
            )


    if not titre:

        titre = "Événement F1"


    # --------------------------------------------------------
    # Texte complet
    # --------------------------------------------------------

    texte = evenement.get_text(
        " ",
        strip=True
    )


    # --------------------------------------------------------
    # Jour
    # --------------------------------------------------------

    date = datetime_str[:10]


    if date == "2026-08-21":
        jour = "VENDREDI"

    elif date == "2026-08-22":
        jour = "SAMEDI"

    elif date == "2026-08-23":
        jour = "DIMANCHE"

    else:
        jour = date


    # --------------------------------------------------------
    # Affichage
    # --------------------------------------------------------

    print()
    print(
        f"📅 {jour} {date}"
    )

    print(
        f"   ⚡ {heure}"
    )

    print(
        f"   🏁 {titre}"
    )

    print(
        f"   📺 Canal+"
    )

    print(
        f"   🔖 diffusion = "
        f"{evenement.get('data-diffusion-type')}"
    )


    resultats.append(
        {
            "date": date,
            "jour": jour,
            "heure": heure,
            "titre": titre,
            "chaine": "Canal+",
            "channel_id": evenement.get(
                "data-channel-id"
            ),
            "type": evenement.get(
                "data-diffusion-type"
            ),
            "datetime": datetime_str,
            "texte": texte
        }
    )


# ============================================================
# TRI CHRONOLOGIQUE
# ============================================================

resultats.sort(
    key=lambda evenement: evenement["datetime"]
)


# ============================================================
# RÉSUMÉ
# ============================================================

print()
print("=" * 80)
print("📊 RÉSUMÉ DU WEEK-END")
print("=" * 80)


if not resultats:

    print(
        "❌ Aucune diffusion F1 Canal+ trouvée."
    )

else:

    for i, evenement in enumerate(
        resultats,
        start=1
    ):

        print(
            f"{i:02d}. "
            f"{evenement['date']} "
            f"{evenement['heure']} — "
            f"{evenement['titre']} — "
            f"{evenement['chaine']}"
        )


print()
print(
    f"✅ {len(resultats)} diffusion(s) "
    f"F1 Canal+ en direct trouvée(s)"
)

print("=" * 80)
print("🏁 DIAGNOSTIC TERMINÉ")
print("=" * 80)
