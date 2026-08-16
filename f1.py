import requests
from bs4 import BeautifulSoup


print("🔎 DIAGNOSTIC DES DIFFUSIONS DU DIMANCHE")
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


evenements = soup.select(
    "ol.schedule-list li.schedule-item"
)


for evenement in evenements:

    if evenement.get("data-sport-id") != "102":
        continue

    time_element = evenement.select_one(
        "time.schedule-time"
    )

    if not time_element:
        continue

    datetime_str = time_element.get("datetime")

    if not datetime_str:
        continue

    # On cible uniquement le dimanche 23 août
    if not datetime_str.startswith("2026-08-23"):
        continue


    print()
    print("=" * 80)
    print("🏎️ ÉVÉNEMENT")
    print("=" * 80)


    # -----------------------------------------------------
    # ATTRIBUTS DU LI
    # -----------------------------------------------------

    print()
    print("📌 ATTRIBUTS")
    print("-" * 80)

    for cle, valeur in evenement.attrs.items():

        print(
            f"{cle} = {valeur}"
        )


    # -----------------------------------------------------
    # TEXTE
    # -----------------------------------------------------

    print()
    print("📄 TEXTE")
    print("-" * 80)

    print(
        evenement.get_text(
            " ",
            strip=True
        )
    )


    # -----------------------------------------------------
    # LIENS
    # -----------------------------------------------------

    print()
    print("🔗 LIENS")
    print("-" * 80)

    for lien in evenement.select("a"):

        print(
            "href =",
            lien.get("href")
        )

        print(
            "title =",
            lien.get("title")
        )

        print(
            "texte =",
            lien.get_text(
                " ",
                strip=True
            )
        )


    # -----------------------------------------------------
    # IMAGES
    # -----------------------------------------------------

    print()
    print("🖼️ IMAGES")
    print("-" * 80)

    for image in evenement.select("img"):

        print(
            "alt =",
            image.get("alt")
        )

        print(
            "src =",
            image.get("src")
        )


    # -----------------------------------------------------
    # CLASSES
    # -----------------------------------------------------

    print()
    print("🏷️ CLASSES")
    print("-" * 80)

    for element in evenement.find_all():

        classes = element.get("class")

        if classes:

            print(
                element.name,
                classes
            )


print()
print("=" * 80)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 80)
