import requests
from bs4 import BeautifulSoup


print("🔎 EXTRACTION DES DIFFUSIONS F1 DU DIMANCHE")
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


print()
print("=" * 80)
print("📺 DIFFUSIONS F1 DU DIMANCHE 23 AOÛT 2026")
print("=" * 80)


resultats = []


# ============================================================
# ANALYSE
# ============================================================

for evenement in evenements:

    # --------------------------------------------------------
    # Sport = Formule 1
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
    # On cible le dimanche 23 août 2026
    # --------------------------------------------------------

    if not datetime_str.startswith("2026-08-23"):
        continue


    # --------------------------------------------------------
    # Type de diffusion
    # --------------------------------------------------------

    diffusion_type = evenement.get(
        "data-diffusion-type"
    )


    # --------------------------------------------------------
    # On ignore les rediffusions
    # --------------------------------------------------------

    if diffusion_type != "live":
        continue


    # --------------------------------------------------------
    # Heure
    # --------------------------------------------------------

    heure = time_element.select_one(
        "strong"
    )

    if heure:
        heure = heure.get_text(
            " ",
            strip=True
        )
    else:
        heure = time_element.get_text(
            " ",
            strip=True
        )


    # --------------------------------------------------------
    # Nom de l'événement
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
    # Chaîne
    # --------------------------------------------------------

    chaine = None

    chaine_element = evenement.select_one(
        ".schedule-channel__name"
    )

    if chaine_element:
        chaine = chaine_element.get_text(
            " ",
            strip=True
        )


    # --------------------------------------------------------
    # ID chaîne
    # --------------------------------------------------------

    channel_id = evenement.get(
        "data-channel-id"
    )


    # --------------------------------------------------------
    # Affichage
    # --------------------------------------------------------

    print(
        f"{len(resultats) + 1:02d}. "
        f"🏎️ 23/08/2026 "
        f"⚡ {heure} "
        f"🏁 {titre} "
        f"📺 {chaine or 'Chaîne inconnue'} "
        f"(ID {channel_id or 'inconnu'})"
    )


    resultats.append(
        {
            "date": "23/08/2026",
            "heure": heure,
            "titre": titre,
            "chaine": chaine,
            "channel_id": channel_id,
            "type": diffusion_type,
            "datetime": datetime_str
        }
    )


# ============================================================
# RÉSUMÉ
# ============================================================

print()
print("=" * 80)
print(
    f"📊 Diffusions F1 en direct trouvées : "
    f"{len(resultats)}"
)
print("=" * 80)


if not resultats:

    print(
        "❌ Aucune diffusion F1 en direct trouvée "
        "pour le dimanche 23 août 2026."
    )

else:

    print()

    for evenement in resultats:

        print(
            f"📅 {evenement['date']} "
            f"à {evenement['heure']} — "
            f"{evenement['titre']} — "
            f"{evenement['chaine'] or 'Chaîne inconnue'}"
        )


print()
print("✅ DIAGNOSTIC TERMINÉ")
