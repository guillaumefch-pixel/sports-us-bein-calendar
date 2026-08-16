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

    texte = evenement.get_text(
        " ",
        strip=True
    )

    # -----------------------------------------------------
    # ON NE GARDE QUE LA F1
    # -----------------------------------------------------

    if "Formule 1" not in texte:
        continue


    # -----------------------------------------------------
    # TYPE D'ÉMISSION
    # -----------------------------------------------------

    time_element = evenement.select_one(
        "time.schedule-time"
    )

    if not time_element:
        continue

    texte_heure = time_element.get_text(
        " ",
        strip=True
    )


    # -----------------------------------------------------
    # HEURE
    # -----------------------------------------------------

    heure = None

    for partie in texte_heure.split():

        if "h" in partie:

            try:
                heure = partie
                break
            except:
                pass

    if not heure:
        continue


    # -----------------------------------------------------
    # DIRECT / REDIFFUSION
    # -----------------------------------------------------

    est_direct = "Direct" in texte_heure

    if not est_direct:
        continue


    # -----------------------------------------------------
    # PROGRAMME
    # -----------------------------------------------------

    titre = None

    # On cherche les liens du programme
    liens = evenement.select(
        "a"
    )

    for lien in liens:

        texte_lien = lien.get_text(
            " ",
            strip=True
        )

        if (
            texte_lien
            and "Formule 1" not in texte_lien
            and texte_lien != "🏎️"
        ):
            titre = texte_lien
            break


    # -----------------------------------------------------
    # CHAÎNE
    # -----------------------------------------------------

    chaine = None

    texte_complet = evenement.get_text(
        " ",
        strip=True
    )

    chaines = [
        "Canal+ Sport 360",
        "Canal+ Sport",
        "Canal+"
    ]

    for nom_chaine in chaines:

        if nom_chaine in texte_complet:

            chaine = nom_chaine
            break


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    # On remonte dans le DOM pour trouver le groupe
    # correspondant à la journée.

    date = None

    parent = evenement

    for _ in range(5):

        parent = parent.parent

        if parent is None:
            break

        texte_parent = parent.get_text(
            " ",
            strip=True
        )

        # On cherche une date française
        # dans les éléments <time> du parent.

        date_elements = parent.select(
            "time"
        )

        for d in date_elements:

            texte_date = d.get_text(
                " ",
                strip=True
            )

            if "2026" in texte_date:

                date = texte_date
                break

        if date:
            break


    # -----------------------------------------------------
    # STOCKAGE
    # -----------------------------------------------------

    resultats.append({
        "date": date,
        "heure": heure,
        "titre": titre,
        "chaine": chaine,
        "texte": texte
    })


# =========================================================
# AFFICHAGE
# =========================================================

print()
print("=" * 80)
print("📺 DIFFUSIONS F1 EN DIRECT")
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
        f"📺 {resultat['chaine']}"
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
