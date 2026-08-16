import requests
from bs4 import BeautifulSoup
import re


print("🔎 DIAGNOSTIC TV-SPORTS.FR — F1")
print("=" * 100)


# =========================================================
# CONFIGURATION
# =========================================================

URL = "https://tv-sports.fr/formule-1/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


# =========================================================
# TÉLÉCHARGEMENT
# =========================================================

print()
print("🌐 Téléchargement de la page...")

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

print(f"HTTP : {response.status_code}")
print(f"Taille HTML : {len(response.text):,} caractères")

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# =========================================================
# INFORMATIONS GÉNÉRALES
# =========================================================

print()
print("📄 INFORMATIONS PAGE")
print("-" * 100)

title = soup.title.get_text(
    " ",
    strip=True
) if soup.title else "(pas de title)"

print(f"Title : {title}")

print(
    f"Occurrences 'Formule 1' : "
    f"{response.text.lower().count('formule 1')}"
)

print(
    f"Occurrences 'Canal+' : "
    f"{response.text.lower().count('canal+')}"
)

print(
    f"Occurrences 'direct' : "
    f"{response.text.lower().count('direct')}"
)

print(
    f"Occurrences 'rediff' : "
    f"{response.text.lower().count('rediff')}"
)


# =========================================================
# RECHERCHE DES TEXTES "FORMULE 1"
# =========================================================

print()
print("=" * 100)
print("🔍 ÉLÉMENTS CONTENANT « FORMULE 1 »")
print("=" * 100)

elements = soup.find_all(
    string=lambda text: (
        text
        and "formule 1" in text.lower()
    )
)

print(
    f"\nNombre d'éléments trouvés : {len(elements)}"
)


for index, element in enumerate(
    elements,
    start=1
):

    print()
    print("-" * 100)
    print(f"ÉLÉMENT #{index}")
    print("-" * 100)

    texte_element = " ".join(
        str(element).split()
    )

    print(
        f"Texte direct : {texte_element[:500]}"
    )

    parent = element.parent

    if parent is None:
        continue

    print(
        f"Balise parent : <{parent.name}>"
    )

    print(
        f"Classes parent : "
        f"{parent.get('class')}"
    )

    print(
        f"ID parent : "
        f"{parent.get('id')}"
    )


    # -----------------------------------------------------
    # REMONTÉE DOM
    # -----------------------------------------------------

    bloc = parent

    for niveau in range(1, 9):

        if bloc is None:
            break

        texte = " ".join(
            bloc.get_text(
                " ",
                strip=True
            ).split()
        )

        if not texte:
            bloc = bloc.parent
            continue

        print()
        print(
            f"  📦 NIVEAU {niveau}"
        )

        print(
            f"  Balise : <{bloc.name}>"
        )

        print(
            f"  Classes : {bloc.get('class')}"
        )

        print(
            f"  ID : {bloc.get('id')}"
        )

        print(
            f"  Longueur : {len(texte)}"
        )

        print(
            f"  TEXTE : {texte[:1000]}"
        )

        bloc = bloc.parent


# =========================================================
# RECHERCHE DES BLOCS CONTENANT DIRECT + CANAL+
# =========================================================

print()
print("=" * 100)
print("📺 BLOCS CONTENANT DIRECT + CANAL+")
print("=" * 100)


tous_elements = soup.find_all(True)

candidats = []

for element in tous_elements:

    texte = " ".join(
        element.get_text(
            " ",
            strip=True
        ).split()
    )

    texte_lower = texte.lower()

    if (
        "direct" in texte_lower
        and "canal+" in texte_lower
        and len(texte) < 2500
    ):

        candidats.append(
            (
                len(texte),
                element
            )
        )


# On trie du plus petit au plus grand
candidats.sort(
    key=lambda x: x[0]
)


print(
    f"\nNombre de blocs candidats : "
    f"{len(candidats)}"
)


# On affiche au maximum les 30 plus petits
for index, (longueur, element) in enumerate(
    candidats[:30],
    start=1
):

    texte = " ".join(
        element.get_text(
            " ",
            strip=True
        ).split()
    )

    print()
    print("-" * 100)

    print(
        f"CANDIDAT #{index}"
    )

    print(
        f"Balise : <{element.name}>"
    )

    print(
        f"Classes : {element.get('class')}"
    )

    print(
        f"ID : {element.get('id')}"
    )

    print(
        f"Longueur : {longueur}"
    )

    print(
        f"TEXTE : {texte[:1500]}"
    )


# =========================================================
# RECHERCHE DES BLOCS CONTENANT GRAND PRIX
# =========================================================

print()
print("=" * 100)
print("🏎️ BLOCS CONTENANT « GRAND PRIX »")
print("=" * 100)


candidats_gp = []

for element in tous_elements:

    texte = " ".join(
        element.get_text(
            " ",
            strip=True
        ).split()
    )

    texte_lower = texte.lower()

    if (
        "grand prix" in texte_lower
        and len(texte) < 2500
    ):

        candidats_gp.append(
            (
                len(texte),
                element
            )
        )


candidats_gp.sort(
    key=lambda x: x[0]
)


print(
    f"\nNombre de blocs : "
    f"{len(candidats_gp)}"
)


for index, (longueur, element) in enumerate(
    candidats_gp[:30],
    start=1
):

    texte = " ".join(
        element.get_text(
            " ",
            strip=True
        ).split()
    )

    print()
    print("-" * 100)

    print(
        f"GRAND PRIX #{index}"
    )

    print(
        f"Balise : <{element.name}>"
    )

    print(
        f"Classes : {element.get('class')}"
    )

    print(
        f"ID : {element.get('id')}"
    )

    print(
        f"Longueur : {longueur}"
    )

    print(
        f"TEXTE : {texte[:1500]}"
    )


# =========================================================
# RECHERCHE DES HEURES
# =========================================================

print()
print("=" * 100)
print("⏰ TEXTES CONTENANT UNE HEURE")
print("=" * 100)


heures = []

for element in tous_elements:

    texte = " ".join(
        element.get_text(
            " ",
            strip=True
        ).split()
    )

    if re.search(
        r"\b\d{1,2}h\d{2}\b",
        texte,
        re.IGNORECASE
    ):

        if (
            "formule 1" in texte.lower()
            or "grand prix" in texte.lower()
            or "canal+" in texte.lower()
        ):

            heures.append(
                (
                    len(texte),
                    element
                )
            )


heures.sort(
    key=lambda x: x[0]
)


print(
    f"\nNombre de blocs pertinents avec heure : "
    f"{len(heures)}"
)


for index, (longueur, element) in enumerate(
    heures[:30],
    start=1
):

    texte = " ".join(
        element.get_text(
            " ",
            strip=True
        ).split()
    )

    print()
    print("-" * 100)

    print(
        f"HEURE #{index}"
    )

    print(
        f"Balise : <{element.name}>"
    )

    print(
        f"Classes : {element.get('class')}"
    )

    print(
        f"Longueur : {longueur}"
    )

    print(
        f"TEXTE : {texte[:1500]}"
    )


# =========================================================
# FIN
# =========================================================

print()
print("=" * 100)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 100)

print()
print(
    "👉 Envoie-moi uniquement la sortie de "
    "« BLOCS CONTENANT DIRECT + CANAL+ » "
    "et « BLOCS CONTENANT GRAND PRIX »."
)
