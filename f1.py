import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

# ---------------------------------------------------------
# MOTS-CLÉS À CONSERVER
# ---------------------------------------------------------

PROGRAMMES_F1 = [
    "essais libres",
    "essai libre",
    "qualifications",
    "qualification",
    "qualifs",
    "qualif",
    "sprint",
    "grand prix",
]

# ---------------------------------------------------------
# MOTS-CLÉS À EXCLURE
# ---------------------------------------------------------

EXCLUSIONS = [
    "on board",
    "le podium",
    "formula one",
    "le mag",
    "la grille",
    "fractionné",
    "fractionne",
    "parade des pilotes",
    "fabrique des rêves",
]

# ---------------------------------------------------------
# CHAÎNES CANAL+ À CONSERVER
# ---------------------------------------------------------

CHAINES_CANAL = [
    "Canal+",
    "Canal +",
]

# ---------------------------------------------------------
# FONCTIONS
# ---------------------------------------------------------

def nettoyer_texte(texte):
    return " ".join(texte.split())


def est_chaine_canal(chaine):
    chaine = chaine.strip()

    for canal in CHAINES_CANAL:
        if canal.lower() in chaine.lower():
            return True

    return False


def est_programme_interessant(titre):
    titre_lower = titre.lower()

    # On élimine d'abord les émissions / magazines
    for exclusion in EXCLUSIONS:
        if exclusion in titre_lower:
            return False

    # Puis on cherche un des événements souhaités
    for mot in PROGRAMMES_F1:
        if mot in titre_lower:
            return True

    return False


# ---------------------------------------------------------
# EXTRACTION
# ---------------------------------------------------------

diffusions = []

# TV-Sports utilise principalement des blocs de programmes.
# On cherche tous les éléments contenant "Formule 1".
elements = soup.find_all(string=lambda text: text and "Formule 1" in text)

for element in elements:

    parent = element.parent

    # On remonte suffisamment dans le DOM pour retrouver
    # le bloc complet correspondant à la diffusion.
    bloc = parent

    for _ in range(6):
        if bloc.parent:
            bloc = bloc.parent

    texte = nettoyer_texte(bloc.get_text(" ", strip=True))

    if "Formule 1" not in texte:
        continue

    # -----------------------------------------------------
    # Recherche de la chaîne
    # -----------------------------------------------------

    chaine = None

    for texte_element in bloc.stripped_strings:
        texte_element = nettoyer_texte(texte_element)

        if est_chaine_canal(texte_element):
            chaine = texte_element
            break

    if not chaine:
        continue

    # -----------------------------------------------------
    # Recherche du titre
    # -----------------------------------------------------

    titre = None

    for texte_element in bloc.stripped_strings:
        texte_element = nettoyer_texte(texte_element)

        if est_programme_interessant(texte_element):
            titre = texte_element
            break

    if not titre:
        continue

    # -----------------------------------------------------
    # Recherche de l'heure
    # -----------------------------------------------------

    heure = None

    for texte_element in bloc.stripped_strings:
        texte_element = nettoyer_texte(texte_element)

        if len(texte_element) == 5 and texte_element[2] == "h":
            try:
                int(texte_element[:2])
                int(texte_element[3:])
                heure = texte_element
                break
            except ValueError:
                pass

    if not heure:
        continue

    # -----------------------------------------------------
    # Recherche du type : Direct / Rediffusion
    # -----------------------------------------------------

    type_diffusion = None

    for texte_element in bloc.stripped_strings:
        texte_element = nettoyer_texte(texte_element)

        if texte_element.lower() == "direct":
            type_diffusion = "Direct"
            break

        if texte_element.lower() in ["rediffusion", "rediff."]:
            type_diffusion = "Rediff."
            break

    if not type_diffusion:
        type_diffusion = "Programme"

    # -----------------------------------------------------
    # Recherche de la date
    # -----------------------------------------------------

    date = None

    # On cherche une date française dans le bloc.
    mois = {
        "janvier": "01",
        "février": "02",
        "mars": "03",
        "avril": "04",
        "mai": "05",
        "juin": "06",
        "juillet": "07",
        "août": "08",
        "septembre": "09",
        "octobre": "10",
        "novembre": "11",
        "décembre": "12",
    }

    import re

    match = re.search(
        r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+"
        r"(\d{1,2})\s+"
        r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)"
        r"\s+(\d{4})",
        texte,
        re.IGNORECASE,
    )

    if match:
        jour = match.group(2)
        mois_nom = match.group(3).lower()
        annee = match.group(4)

        date = f"{jour.zfill(2)}/{mois[mois_nom]}/{annee}"

    # -----------------------------------------------------
    # Éviter les doublons
    # -----------------------------------------------------

    diffusion = {
        "date": date,
        "heure": heure,
        "type": type_diffusion,
        "titre": titre,
        "chaine": chaine,
    }

    if diffusion not in diffusions:
        diffusions.append(diffusion)


# ---------------------------------------------------------
# TRI
# ---------------------------------------------------------

def cle_tri(diffusion):
    date = diffusion["date"] or "99/99/9999"
    heure = diffusion["heure"] or "99h99"

    try:
        dt = datetime.strptime(
            f"{date} {heure}",
            "%d/%m/%Y %Hh%M"
        )
        return dt
    except ValueError:
        return datetime.max


diffusions.sort(key=cle_tri)


# ---------------------------------------------------------
# AFFICHAGE
# ---------------------------------------------------------

print()

if not diffusions:
    print("❌ Aucune diffusion F1 trouvée.")
else:

    for i, diffusion in enumerate(diffusions, start=1):

        date = diffusion["date"] or "Date inconnue"
        heure = diffusion["heure"]
        type_diffusion = diffusion["type"]
        titre = diffusion["titre"]
        chaine = diffusion["chaine"]

        print(
            f"{i:02d}. 🏎️ {date} "
            f"⚡ {heure} "
            f"{type_diffusion} "
            f"🏎️ {titre} "
            f"📺 {chaine}"
        )

print()
print("=" * 80)
print(f"✅ {len(diffusions)} diffusion(s) F1 trouvée(s)")
