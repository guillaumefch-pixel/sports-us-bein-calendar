import requests
from bs4 import BeautifulSoup
import re


print("🔎 DIAGNOSTIC DES ÉVÉNEMENTS F1 CANAL+")
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
    f"✅ Page téléchargée : "
    f"{len(response.text)} caractères"
)


# =========================================================
# NETTOYAGE
# =========================================================

def nettoyer(texte):

    if not texte:
        return ""

    return " ".join(
        texte.split()
    )


# =========================================================
# RECHERCHE DES LISTES
# =========================================================

schedule_lists = soup.select(
    "ol.schedule-list"
)


print(
    f"📋 Listes trouvées : "
    f"{len(schedule_lists)}"
)


if not schedule_lists:

    print(
        "❌ Aucune liste de programmes trouvée."
    )

    raise SystemExit(1)


# =========================================================
# ANALYSE
# =========================================================

numero = 0


for schedule in schedule_lists:

    evenements = schedule.find_all(
        "li",
        recursive=False
    )


    for evenement in evenements:

        texte = nettoyer(
            evenement.get_text(
                " ",
                strip=True
            )
        )

        texte_lower = texte.lower()


        # -------------------------------------------------
        # ON NE GARDE QUE :
        #
        # - Formule 1
        # - Canal+
        # - DIRECT
        # -------------------------------------------------

        if "formule 1" not in texte_lower:
            continue

        if "canal+" not in texte_lower:
            continue

        if "direct" not in texte_lower:
            continue

        if "rediff" in texte_lower:
            continue


        # -------------------------------------------------
        # HEURE
        # -------------------------------------------------

        match_heure = re.search(
            r"\b(\d{1,2})h(\d{2})\b",
            texte
        )

        if not match_heure:
            continue


        heure = (
            f"{int(match_heure.group(1)):02d}h"
            f"{int(match_heure.group(2)):02d}"
        )


        # -------------------------------------------------
        # NOUVEL ÉVÉNEMENT
        # -------------------------------------------------

        numero += 1


        print()
        print()
        print("=" * 100)
        print(
            f"🏎️ ÉVÉNEMENT F1 #{numero}"
        )
        print("=" * 100)


        # -------------------------------------------------
        # TEXTE GLOBAL
        # -------------------------------------------------

        print()
        print("📄 TEXTE GLOBAL")
        print("-" * 100)

        print(
            texte
        )


        # -------------------------------------------------
        # TEXTE DE CHAQUE ENFANT
        # -------------------------------------------------

        print()
        print("🧩 ÉLÉMENTS ENFANTS")
        print("-" * 100)


        enfants = evenement.find_all(
            recursive=True
        )


        compteur_enfant = 0


        for enfant in enfants:

            texte_enfant = nettoyer(
                enfant.get_text(
                    " ",
                    strip=True
                )
            )

            if not texte_enfant:
                continue


            # Évite les blocs gigantesques

            if len(texte_enfant) > 300:
                continue


            compteur_enfant += 1


            print()
            print(
                f"[{compteur_enfant}] "
                f"<{enfant.name}>"
            )

            print(
                "classes =",
                enfant.get("class")
            )

            print(
                "id =",
                enfant.get("id")
            )

            print(
                "texte =",
                repr(texte_enfant)
            )


        # -------------------------------------------------
        # HTML BRUT DE L'ÉVÉNEMENT
        # -------------------------------------------------

        print()
        print("🧱 HTML BRUT DE L'ÉVÉNEMENT")
        print("-" * 100)


        html = evenement.prettify()


        # Limite de sécurité
        # mais normalement les <li> restent petits.

        if len(html) > 12000:

            html = (
                html[:12000]
                + "\n\n... HTML TRONQUÉ ..."
            )


        print(
            html
        )


print()
print()
print("=" * 100)
print(
    f"✅ {numero} événement(s) F1 Canal+ direct analysé(s)"
)
print("=" * 100)
