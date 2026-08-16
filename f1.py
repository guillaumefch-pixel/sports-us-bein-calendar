import requests
from bs4 import BeautifulSoup


print("🔎 DIAGNOSTIC DE LA PAGE DU GRAND PRIX")
print("=" * 90)


URL = "https://tv-sports.fr/formule-1/grand-prix-des-pays-bas"


HEADERS = {
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
    headers=HEADERS,
    timeout=20
)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


print(
    f"✅ Page téléchargée : "
    f"{len(response.text)} caractères"
)


# =========================================================
# TITRE DE LA PAGE
# =========================================================

print()
print("=" * 90)
print("📄 TITRE")
print("=" * 90)

title = soup.title

if title:
    print(title.get_text(" ", strip=True))
else:
    print("Aucun titre")


# =========================================================
# TEXTE DES ÉLÉMENTS IMPORTANTS
# =========================================================

print()
print("=" * 90)
print("🔎 RECHERCHE DES MOTS-CLÉS")
print("=" * 90)


mots_cles = [
    "EL1",
    "EL2",
    "EL3",
    "FP1",
    "FP2",
    "FP3",
    "Qualification",
    "Qualifications",
    "Qualif",
    "Sprint",
    "Grand Prix"
]


texte_page = soup.get_text(
    " ",
    strip=True
)


for mot in mots_cles:

    compteur = texte_page.lower().count(
        mot.lower()
    )

    print(
        f"{mot:<20} : {compteur} occurrence(s)"
    )


# =========================================================
# RECHERCHE DES LIENS
# =========================================================

print()
print("=" * 90)
print("🔗 LIENS CONTENANT DES INFORMATIONS F1")
print("=" * 90)


for lien in soup.select("a"):

    href = lien.get("href")

    texte = lien.get_text(
        " ",
        strip=True
    )


    if not href:
        continue


    texte_lower = (
        texte + " " + href
    ).lower()


    mots = [
        "essai",
        "qualif",
        "qualification",
        "sprint",
        "grand-prix",
        "gp"
    ]


    if any(
        mot in texte_lower
        for mot in mots
    ):

        print()
        print(
            f"texte : {texte}"
        )

        print(
            f"href  : {href}"
        )

        print(
            f"title : {lien.get('title')}"
        )


# =========================================================
# TABLES / LISTES
# =========================================================

print()
print("=" * 90)
print("📋 ÉLÉMENTS SCHEDULE")
print("=" * 90)


elements = soup.select(
    "li.schedule-item"
)


print(
    f"Nombre d'événements trouvés : "
    f"{len(elements)}"
)


for i, element in enumerate(
    elements,
    start=1
):

    print()
    print("-" * 90)
    print(
        f"🏎️ ÉVÉNEMENT #{i}"
    )
    print("-" * 90)


    # -----------------------------------------------------
    # ATTRIBUTS
    # -----------------------------------------------------

    print()
    print("ATTRIBUTS :")

    for cle, valeur in element.attrs.items():

        print(
            f"  {cle} = {valeur}"
        )


    # -----------------------------------------------------
    # TEXTE
    # -----------------------------------------------------

    print()
    print("TEXTE :")

    print(
        element.get_text(
            " ",
            strip=True
        )
    )


    # -----------------------------------------------------
    # TIME
    # -----------------------------------------------------

    time_element = element.select_one(
        "time.schedule-time"
    )

    if time_element:

        print()
        print("DATETIME :")

        print(
            time_element.get("datetime")
        )


    # -----------------------------------------------------
    # LIENS
    # -----------------------------------------------------

    print()
    print("LIENS :")

    for lien in element.select("a"):

        print(
            "  href =",
            lien.get("href")
        )

        print(
            "  title =",
            lien.get("title")
        )

        print(
            "  texte =",
            lien.get_text(
                " ",
                strip=True
            )
        )


    # -----------------------------------------------------
    # IMAGES
    # -----------------------------------------------------

    print()
    print("IMAGES :")

    for image in element.select("img"):

        print(
            "  alt =",
            image.get("alt")
        )

        print(
            "  src =",
            image.get("src")
        )


# =========================================================
# FIN
# =========================================================

print()
print("=" * 90)
print("🏁 DIAGNOSTIC TERMINÉ")
print("=" * 90)
