import requests
from bs4 import BeautifulSoup


print("🔎 ANALYSE DE LA STRUCTURE TV-SPORTS.FR")
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


print()
print(f"✅ Page téléchargée : {len(response.text)} caractères")
print()


# =========================================================
# FONCTION DE NETTOYAGE
# =========================================================

def nettoyer(texte):
    if not texte:
        return ""

    return " ".join(texte.split())


# =========================================================
# RECHERCHE DE PROGRAMMES CONCRETS
# =========================================================

CIBLES = [
    "20h59",
    "Grand Prix de Hongrie",
    "Canal+ Sport 360",
]


for cible in CIBLES:

    print()
    print("=" * 80)
    print(f"🎯 RECHERCHE : {cible}")
    print("=" * 80)

    elements = soup.find_all(
        string=lambda text: (
            text
            and cible.lower() in text.lower()
        )
    )

    print(
        f"Occurrences trouvées : {len(elements)}"
    )

    for index, element in enumerate(
        elements[:5],
        start=1
    ):

        print()
        print("-" * 80)
        print(f"ÉLÉMENT #{index}")
        print("-" * 80)

        print(
            "Texte direct :",
            repr(nettoyer(str(element)))
        )

        print(
            "Balise :",
            element.parent.name
        )

        print(
            "Classes :",
            element.parent.get("class")
        )

        print(
            "ID :",
            element.parent.get("id")
        )

        # -------------------------------------------------
        # PARENTS
        # -------------------------------------------------

        parent = element.parent

        for niveau in range(1, 9):

            parent = parent.parent

            if parent is None:
                break

            texte_parent = nettoyer(
                parent.get_text(
                    " ",
                    strip=True
                )
            )

            print()
            print(
                f"📦 NIVEAU {niveau}"
            )

            print(
                "Balise :",
                parent.name
            )

            print(
                "Classes :",
                parent.get("class")
            )

            print(
                "ID :",
                parent.get("id")
            )

            print(
                "Longueur :",
                len(texte_parent)
            )

            # On ne veut pas faire exploser le log
            # avec plusieurs milliers de caractères.

            if len(texte_parent) > 1000:
                texte_parent = (
                    texte_parent[:1000]
                    + "..."
                )

            print(
                "TEXTE :",
                texte_parent
            )


# =========================================================
# RECHERCHE DES ÉLÉMENTS AVEC UNE HEURE
# =========================================================

print()
print("=" * 80)
print("🕐 RECHERCHE DES ÉLÉMENTS CONTENANT UNE HEURE")
print("=" * 80)


elements_heure = soup.find_all(
    string=lambda text: (
        text
        and any(
            f"{h:02d}h" in text
            for h in range(24)
        )
    )
)


print(
    f"Éléments contenant une heure : "
    f"{len(elements_heure)}"
)


# On affiche uniquement les 20 premiers
# éléments intéressants.

compteur = 0

for element in elements_heure:

    texte = nettoyer(
        str(element)
    )

    if not texte:
        continue

    compteur += 1

    print()
    print("-" * 80)
    print(f"HEURE #{compteur}")
    print("-" * 80)

    print(
        "Texte :",
        texte
    )

    print(
        "Balise :",
        element.parent.name
    )

    print(
        "Classes :",
        element.parent.get("class")
    )

    print(
        "ID :",
        element.parent.get("id")
    )

    if compteur >= 20:
        break


print()
print("=" * 80)
print("✅ ANALYSE TERMINÉE")
print("=" * 80)
