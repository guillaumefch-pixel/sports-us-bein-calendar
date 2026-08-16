import requests
from bs4 import BeautifulSoup


print("🔎 DIAGNOSTIC DE LA PAGE « COURSE EN DIRECT »")
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

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# =========================================================
# INFORMATIONS GÉNÉRALES
# =========================================================

print()
print("=" * 90)
print("📄 TITRE")
print("=" * 90)

print(soup.title.get_text(strip=True) if soup.title else "Aucun titre")


print()
print("=" * 90)
print("📊 INFORMATIONS PAGE")
print("=" * 90)

print("Taille HTML :", len(response.text), "caractères")


# =========================================================
# RECHERCHE DES MOTS-CLÉS
# =========================================================

mots_cles = [
    "EL1",
    "EL2",
    "EL3",
    "FP1",
    "FP2",
    "FP3",
    "Essais libres",
    "Essai libre",
    "Qualification",
    "Qualifications",
    "Qualif",
    "Sprint",
    "Course",
    "Grand Prix",
    "Direct",
    "Canal+",
    "Canal+ Sport",
]


print()
print("=" * 90)
print("🔎 RECHERCHE DES MOTS-CLÉS")
print("=" * 90)


texte_complet = soup.get_text(
    " ",
    strip=True
)


for mot in mots_cles:

    print(
        f"{mot:<20}: {texte_complet.lower().count(mot.lower())} occurrence(s)"
    )


# =========================================================
# LIENS CONTENANT DES INFORMATIONS
# =========================================================

print()
print("=" * 90)
print("🔗 LIENS INTÉRESSANTS")
print("=" * 90)


for lien in soup.select("a"):

    texte = lien.get_text(
        " ",
        strip=True
    )

    href = lien.get("href")

    title = lien.get("title")


    texte_test = (
        (texte or "")
        + " "
        + (title or "")
        + " "
        + (href or "")
    ).lower()


    mots_recherche = [
        "el1",
        "el2",
        "el3",
        "fp1",
        "fp2",
        "fp3",
        "qualif",
        "qualification",
        "sprint",
        "course",
        "grand-prix",
        "direct",
        "formule-1",
    ]


    if any(
        mot in texte_test
        for mot in mots_recherche
    ):

        print()
        print("texte :", texte)
        print("href  :", href)
        print("title :", title)


# =========================================================
# ÉLÉMENTS SCHEDULE
# =========================================================

print()
print("=" * 90)
print("📺 ÉLÉMENTS DE PROGRAMMATION")
print("=" * 90)


elements_schedule = soup.select(
    ".schedule-item"
)


print(
    "Nombre de .schedule-item :",
    len(elements_schedule)
)


for i, evenement in enumerate(
    elements_schedule,
    start=1
):

    print()
    print("-" * 90)
    print("ÉVÉNEMENT", i)
    print("-" * 90)

    print(
        evenement.get_text(
            " ",
            strip=True
        )
    )


    print()
    print("ATTRIBUTS :")

    for cle, valeur in evenement.attrs.items():

        print(
            f"{cle} = {valeur}"
        )


# =========================================================
# RECHERCHE DE BLOCS CONTENANT LES MOTS F1
# =========================================================

print()
print("=" * 90)
print("🧩 BLOCS HTML CONTENANT « QUALIF », « EL » OU « SPRINT »")
print("=" * 90)


trouves = 0


for element in soup.find_all():

    texte = element.get_text(
        " ",
        strip=True
    )


    if not texte:
        continue


    texte_test = texte.lower()


    if (
        "qualification" in texte_test
        or "qualif" in texte_test
        or "el1" in texte_test
        or "el2" in texte_test
        or "el3" in texte_test
        or "sprint" in texte_test
    ):

        # On évite d'afficher les énormes blocs parents
        if len(texte) > 500:

            continue


        print()
        print(
            element.name,
            element.get("class")
        )

        print(
            texte[:500]
        )

        trouves += 1


        if trouves >= 30:

            break


print()
print("=" * 90)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 90)
