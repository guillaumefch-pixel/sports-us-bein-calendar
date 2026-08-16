import requests
from bs4 import BeautifulSoup
import re

print("🔎 EXTRACTION DES DIFFUSIONS F1")
print("=" * 80)

URL = "https://tv-sports.fr/formule-1/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

response = requests.get(URL, headers=headers, timeout=20)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")


# =========================================================
# PARAMÈTRES
# =========================================================

CHAINES_CANAL = [
    "canal+",
    "canal +",
]

# On veut uniquement les directs
TYPE_DIRECT = "direct"

# Programmes autorisés
PROGRAMMES = [
    "essais libres",
    "essai libre",
    "qualifications sprint",
    "qualification sprint",
    "qualifs sprint",
    "qualif sprint",
    "qualifications",
    "qualification",
    "qualifs",
    "qualif",
    "sprint",
    "grand prix",
]

# Émissions que l'on ne veut surtout pas récupérer
EXCLUSIONS = [
    "on board",
    "le podium",
    "formula one",
    "formula one, le mag",
    "le mag",
    "la grille",
    "fractionné",
    "fractionne",
    "parade des pilotes",
    "fabrique des rêves",
]


# =========================================================
# FONCTIONS
# =========================================================

def nettoyer(texte):
    return " ".join(texte.split())


def est_canal(texte):
    texte = texte.lower()

    for chaine in CHAINES_CANAL:
        if chaine in texte:
            return True

    return False


def trouver_programme(texte):
    texte_lower = texte.lower()

    # Les exclusions passent en premier
    for exclusion in EXCLUSIONS:
        if exclusion in texte_lower:
            return None

    # Grand Prix
    if "grand prix" in texte_lower:
        match = re.search(
            r"(grand prix(?:\s+(?:de|du|d'|des|de la))?\s+[^|]+)",
            texte,
            re.IGNORECASE
        )

        if match:
            return nettoyer(match.group(1))

        return "Grand Prix"

    # Qualifications Sprint AVANT Qualifications
    if "qualification sprint" in texte_lower or "qualif sprint" in texte_lower:
        return "Qualifications Sprint"

    # Qualifications
    if (
        "qualifications" in texte_lower
        or "qualification" in texte_lower
        or "qualifs" in texte_lower
        or "qualif" in texte_lower
    ):
        return "Qualifications"

    # Essais libres
    if "essais libres" in texte_lower or "essai libre" in texte_lower:
        return "Essais libres"

    # Sprint
    if re.search(r"\bsprint\b", texte_lower):
        return "Sprint"

    return None


def trouver_heure(texte):
    match = re.search(r"\b(\d{1,2}h\d{2})\b", texte)

    if match:
        return match.group(1)

    return None


def trouver_date(texte):
    jours = (
        "lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche"
    )

    mois = (
        "janvier|février|mars|avril|mai|juin|juillet|août|"
        "septembre|octobre|novembre|décembre"
    )

    pattern = (
        rf"(?:{jours})\s+"
        rf"(\d{{1,2}})\s+"
        rf"({mois})\s+"
        rf"(\d{{4}})"
    )

    match = re.search(pattern, texte, re.IGNORECASE)

    if match:
        return (
            f"{match.group(1).zfill(2)} "
            f"{match.group(2)} "
            f"{match.group(3)}"
        )

    return None


# =========================================================
# EXTRACTION DES BLOCS
# =========================================================

diffusions = []

# On cherche les éléments contenant "Formule 1"
elements = soup.find_all(
    string=lambda text: text and "Formule 1" in text
)

for element in elements:

    # On remonte progressivement dans le DOM.
    # L'objectif est de trouver le bloc correspondant
    # à UNE diffusion, et non toute la page.
    bloc = element.parent

    candidats = []

    for niveau in range(1, 9):

        if bloc is None:
            break

        texte = nettoyer(bloc.get_text(" ", strip=True))

        # On cherche un bloc suffisamment petit contenant
        # les informations nécessaires.
        if (
            trouver_heure(texte)
            and "direct" in texte.lower()
            and est_canal(texte)
        ):
            candidats.append((len(texte), bloc, texte))

        bloc = bloc.parent

    if not candidats:
        continue

    # Le plus petit bloc contenant les informations pertinentes
    # est généralement celui qui correspond à la diffusion.
    candidats.sort(key=lambda x: x[0])

    _, bloc, texte = candidats[0]

    # -----------------------------------------------------
    # DIRECT UNIQUEMENT
    # -----------------------------------------------------

    if "direct" not in texte.lower():
        continue

    # Si le bloc indique explicitement une rediffusion,
    # on le rejette.
    if "rediff" in texte.lower():
        continue

    # -----------------------------------------------------
    # CHAÎNE
    # -----------------------------------------------------

    chaine = None

    for chaine_element in bloc.stripped_strings:

        chaine_element = nettoyer(chaine_element)

        if est_canal(chaine_element):

            # On ne garde que les chaînes Canal+
            chaine = chaine_element

            break

    if not chaine:
        continue

    # -----------------------------------------------------
    # PROGRAMME
    # -----------------------------------------------------

    programme = trouver_programme(texte)

    if not programme:
        continue

    # -----------------------------------------------------
    # HEURE
    # -----------------------------------------------------

    heure = trouver_heure(texte)

    if not heure:
        continue

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    date = trouver_date(texte)

    if not date:
        continue

    # -----------------------------------------------------
    # DÉDOUBLONNAGE
    # -----------------------------------------------------

    diffusion = {
        "date": date,
        "heure": heure,
        "programme": programme,
        "chaine": chaine,
    }

    if diffusion not in diffusions:
        diffusions.append(diffusion)


# =========================================================
# TRI CHRONOLOGIQUE
# =========================================================

mois_num = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}


def cle_tri(diffusion):

    jour, mois, annee = diffusion["date"].split()

    heure, minute = diffusion["heure"].split("h")

    return (
        int(annee),
        mois_num[mois.lower()],
        int(jour),
        int(heure),
        int(minute),
    )


diffusions.sort(key=cle_tri)


# =========================================================
# AFFICHAGE
# =========================================================

print()

if not diffusions:

    print("❌ Aucune diffusion F1 en direct trouvée.")

else:

    for i, diffusion in enumerate(diffusions, start=1):

        print(
            f"{i:02d}. "
            f"🏎️ {diffusion['date']} "
            f"⚡ {diffusion['heure']} "
            f"Direct "
            f"🏁 {diffusion['programme']} "
            f"📺 {diffusion['chaine']}"
        )

print()
print("=" * 80)
print(
    f"✅ {len(diffusions)} diffusion(s) F1 en direct trouvée(s)"
)
