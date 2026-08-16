import requests
from bs4 import BeautifulSoup


print("🔎 DIAGNOSTIC DES 6 DIFFUSIONS F1")
print("=" * 80)


URL = "https://tv-sports.fr/formule-1/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}


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


# =========================================================
# ÉVÉNEMENTS
# =========================================================

evenements = soup.select(
    "ol.schedule-list li.schedule-item"
)


compteur = 0


for evenement in evenements:

    texte = evenement.get_text(
        " ",
        strip=True
    )

    if "Formule 1" not in texte:
        continue

    time_element = evenement.select_one(
        "time.schedule-time"
    )

    if not time_element:
        continue

    texte_heure = time_element.get_text(
        " ",
        strip=True
    )

    if "Direct" not in texte_heure:
        continue

    compteur += 1

    if compteur > 6:
        break


    print()
    print("=" * 80)
    print(f"🏎️ DIFFUSION #{compteur}")
    print("=" * 80)


    # -----------------------------------------------------
    # TEXTE COMPLET
    # -----------------------------------------------------

    print()
    print("📄 TEXTE COMPLET")
    print("-" * 80)
    print(texte)


    # -----------------------------------------------------
    # STRUCTURE HTML DE L'ÉVÉNEMENT
    # -----------------------------------------------------

    print()
    print("🧩 HTML DE L'ÉVÉNEMENT")
    print("-" * 80)

    print(
        evenement.prettify()[:8000]
    )


    # -----------------------------------------------------
    # PARENTS
    # -----------------------------------------------------

    print()
    print("📦 PARENTS")
    print("-" * 80)

    parent = evenement

    for niveau in range(1, 6):

        parent = parent.parent

        if parent is None:
            break

        print()
        print(
            f"NIVEAU {niveau} : "
            f"<{parent.name}> "
            f"class={parent.get('class')}"
        )

        texte_parent = parent.get_text(
            " ",
            strip=True
        )

        print(
            texte_parent[:1500]
        )


print()
print("=" * 80)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 80)
