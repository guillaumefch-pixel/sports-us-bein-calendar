import requests
from bs4 import BeautifulSoup
from datetime import datetime


print("🔎 EXTRACTION DES DIFFUSIONS F1")
print("=" * 80)


# =========================================================
# CONFIGURATION
# =========================================================

URL = "https://tv-sports.fr/formule-1/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}


# =========================================================
# TÉLÉCHARGEMENT
# =========================================================

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

print(
    f"✅ Page téléchargée : {len(response.text)} caractères"
)


# =========================================================
# RECHERCHE DES ÉVÉNEMENTS
# =========================================================

evenements = soup.select(
    "ol.schedule-list li.schedule-item"
)

print(
    f"📋 Événements trouvés : {len(evenements)}"
)


# =========================================================
# EXTRACTION
# =========================================================

resultats = []


for evenement in evenements:

    # -----------------------------------------------------
    # FILTRE F1
    # -----------------------------------------------------

    if evenement.get("data-sport-id") != "102":
        continue


    # -----------------------------------------------------
    # UNIQUEMENT LES DIRECTS
    # -----------------------------------------------------

    if evenement.get("data-diffusion-type") != "live":
        continue


    # -----------------------------------------------------
    # DATE + HEURE
    # -----------------------------------------------------

    time_element = evenement.select_one(
        "time.schedule-time"
    )

    if not time_element:
        continue

    datetime_str = time_element.get("datetime")

    if not datetime_str:
        continue

    try:

        dt = datetime.fromisoformat(
            datetime_str
        )

    except ValueError:

        continue


    # -----------------------------------------------------
    # TITRE
    # -----------------------------------------------------

    lien_programme = evenement.select_one(
        ".schedule-program a[href]"
    )

    if lien_programme:

        titre = (
            lien_programme.get("title")
            or lien_programme.get_text(
                " ",
                strip=True
            )
        )

    else:

        titre = None


    # -----------------------------------------------------
    # CHAÎNE
    # -----------------------------------------------------

    texte_evenement = evenement.get_text(
        " ",
        strip=True
    )

    chaine = None

    for nom_chaine in [
        "Canal+ Sport 360",
        "Canal+ Sport",
        "Canal+"
    ]:

        if nom_chaine in texte_evenement:

            chaine = nom_chaine
            break


    # -----------------------------------------------------
    # STOCKAGE
    # -----------------------------------------------------

    resultats.append({
        "datetime": dt,
        "date": dt.strftime("%d/%m/%Y"),
        "heure": dt.strftime("%H:%M"),
        "titre": titre,
        "chaine": chaine
    })


# =========================================================
# TRI CHRONOLOGIQUE
# =========================================================

resultats.sort(
    key=lambda x: x["datetime"]
)


# =========================================================
# AFFICHAGE
# =========================================================

print()
print("=" * 80)
print("📺 DIFFUSIONS F1 CANAL+ EN DIRECT")
print("=" * 80)


for i, resultat in enumerate(
    resultats,
    start=1
):

    print(
        f"{i:02d}. "
        f"🏎️ {resultat['date']} "
        f"⚡ {resultat['heure']} "
        f"🏁 {resultat['titre']} "
        f"📺 {resultat['chaine'] or 'Chaîne inconnue'}"
    )


print()
print("=" * 80)
print(
    f"📊 Événements analysés : {len(evenements)}"
)
print(
    f"✅ Diffusions retenues : {len(resultats)}"
)
print("=" * 80)
