import requests
from bs4 import BeautifulSoup
import re
import json


print("🔎 RECHERCHE DES DONNÉES CACHÉES F1")
print("=" * 90)


URL = "https://tv-sports.fr/formule-1/grand-prix-des-pays-bas/course-direct"


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

html = response.text

soup = BeautifulSoup(
    html,
    "html.parser"
)


print()
print("=" * 90)
print("📄 PAGE")
print("=" * 90)

print("URL :", URL)
print("Taille HTML :", len(html), "caractères")


# =========================================================
# 1. SCRIPTS
# =========================================================

print()
print("=" * 90)
print("📜 SCRIPTS JAVASCRIPT")
print("=" * 90)


scripts = soup.find_all("script")

print(
    "Nombre de scripts :",
    len(scripts)
)


for i, script in enumerate(scripts, start=1):

    contenu = script.string or script.get_text()

    if not contenu:
        contenu = ""

    print()
    print("-" * 90)
    print("SCRIPT", i)
    print("-" * 90)

    print(
        "type =",
        script.get("type")
    )

    print(
        "src =",
        script.get("src")
    )

    print(
        "taille =",
        len(contenu)
    )

    # On affiche uniquement les scripts qui semblent
    # contenir des données ou des informations utiles.

    contenu_test = contenu.lower()

    mots_interessants = [
        "formula",
        "formule",
        "grand prix",
        "qualification",
        "qualif",
        "sprint",
        "session",
        "schedule",
        "calendar",
        "event",
        "api",
        "json",
        "canal",
        "sport",
    ]

    if any(
        mot in contenu_test
        for mot in mots_interessants
    ):

        print()
        print("⭐ SCRIPT POTENTIELLEMENT INTÉRESSANT")

        print(
            contenu[:5000]
        )


# =========================================================
# 2. JSON-LD
# =========================================================

print()
print("=" * 90)
print("🧩 JSON-LD")
print("=" * 90)


json_ld = soup.select(
    'script[type="application/ld+json"]'
)


print(
    "Nombre de blocs JSON-LD :",
    len(json_ld)
)


for i, bloc in enumerate(json_ld, start=1):

    contenu = bloc.string or bloc.get_text()

    print()
    print("-" * 90)
    print("JSON-LD", i)
    print("-" * 90)

    try:

        data = json.loads(contenu)

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )[:10000]
        )

    except Exception:

        print(
            contenu[:5000]
        )


# =========================================================
# 3. ATTRIBUTS DATA-*
# =========================================================

print()
print("=" * 90)
print("🏷️ ATTRIBUTS DATA-*")
print("=" * 90)


elements_data = soup.find_all(
    lambda tag: any(
        attribut.startswith("data-")
        for attribut in tag.attrs
    )
)


print(
    "Éléments contenant des data-* :",
    len(elements_data)
)


compteur = 0


for element in elements_data:

    attributs_interessants = {}

    for cle, valeur in element.attrs.items():

        if cle.startswith("data-"):

            attributs_interessants[cle] = valeur


    texte = element.get_text(
        " ",
        strip=True
    )


    texte_test = texte.lower()


    if (
        any(
            mot in texte_test
            for mot in [
                "grand prix",
                "canal",
                "qualif",
                "sprint",
                "course",
                "direct",
                "formule"
            ]
        )
        or any(
            "session" in cle.lower()
            or "event" in cle.lower()
            or "schedule" in cle.lower()
            for cle in attributs_interessants
        )
    ):

        print()
        print("-" * 90)

        print(
            element.name,
            element.get("class")
        )

        print(
            "TEXTE :",
            texte[:500]
        )

        for cle, valeur in attributs_interessants.items():

            print(
                f"{cle} = {valeur}"
            )

        compteur += 1


        if compteur >= 50:

            break


# =========================================================
# 4. RECHERCHE D'URLS API
# =========================================================

print()
print("=" * 90)
print("🌐 URLS / API DÉTECTÉES DANS LE HTML")
print("=" * 90)


urls = set(
    re.findall(
        r'https?://[^"\'\s<>]+',
        html
    )
)


for url in sorted(urls):

    url_test = url.lower()

    if any(
        mot in url_test
        for mot in [
            "api",
            "json",
            "ajax",
            "schedule",
            "calendar",
            "event",
            "sport",
            "tv"
        ]
    ):

        print(
            url[:500]
        )


# =========================================================
# 5. RECHERCHE DE MOTS-CLÉS DIRECTEMENT DANS LE HTML
# =========================================================

print()
print("=" * 90)
print("🔍 MOTS-CLÉS DANS LE HTML BRUT")
print("=" * 90)


mots = [
    "qualification",
    "qualif",
    "sprint",
    "session",
    "schedule",
    "event",
    "calendar",
    "formula",
    "formule",
    "canal",
    "course",
]


for mot in mots:

    occurrences = [
        match.start()
        for match in re.finditer(
            re.escape(mot),
            html,
            re.IGNORECASE
        )
    ]


    print()
    print(
        f"{mot:<20}: {len(occurrences)} occurrence(s)"
    )


    # Affiche quelques extraits du HTML
    # autour des occurrences.

    for position in occurrences[:3]:

        debut = max(
            0,
            position - 250
        )

        fin = min(
            len(html),
            position + 500
        )

        extrait = html[
            debut:fin
        ]

        print()
        print(
            extrait
        )


# =========================================================
# FIN
# =========================================================

print()
print("=" * 90)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 90)
