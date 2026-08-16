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

# Mots indiquant une diffusion en direct
MOTS_DIRECT = [
    "direct",
    "live",
]

# Mots indiquant une rediffusion
MOTS_REDIF = [
    "rediff",
    "rediffusion",
    "replay",
]

# Programmes F1 que nous voulons récupérer
# Attention : l'ordre est important.
PROGRAMMES = [
    "qualifications sprint",
    "qualification sprint",
    "qualifs sprint",
    "qualif sprint",

    "essais libres 1",
    "essais libres 2",
    "essais libres 3",
    "essai libre 1",
    "essai libre 2",
    "essai libre 3",

    "essais libres",
    "essai libre",

    "qualifications",
    "qualification",
    "qualifs",
    "qualif",

    "sprint",

    "grand prix",
]

# Émissions / magazines explicitement exclus
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
# OUTILS
# =========================================================

def nettoyer(texte):
    return " ".join(texte.split())


def est_canal(texte):
    """
    Vérifie si le texte correspond à une chaîne Canal+.
    """
    texte = texte.lower()

    return any(chaine in texte for chaine in CHAINES_CANAL)


def est_direct(texte):
    """
    Vérifie que la diffusion est bien un direct.
    """
    texte_lower = texte.lower()

    return any(mot in texte_lower for mot in MOTS_DIRECT)


def est_rediffusion(texte):
    """
    Vérifie que la diffusion n'est PAS une rediffusion.
    """
    texte_lower = texte.lower()

    return any(mot in texte_lower for mot in MOTS_REDIF)


def trouver_heure(texte):
    """
    Recherche une heure au format 15h00.
    """

    match = re.search(
        r"\b(\d{1,2})h(\d{2})\b",
        texte,
        re.IGNORECASE
    )

    if not match:
        return None

    return f"{int(match.group(1)):02d}h{match.group(2)}"


def trouver_date(texte):
    """
    Recherche une date du type :
    vendredi 21 août 2026
    """

    jours = (
        "lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche"
    )

    mois = (
        "janvier|février|fevrier|mars|avril|mai|juin|juillet|"
        "août|aout|septembre|octobre|novembre|décembre|decembre"
    )

    pattern = (
        rf"(?:{jours})\s+"
        rf"(\d{{1,2}})\s+"
        rf"({mois})\s+"
        rf"(\d{{4}})"
    )

    match = re.search(
        pattern,
        texte,
        re.IGNORECASE
    )

    if not match:
        return None

    mois = match.group(2)

    # Normalisation des accents pour le tri
    mois = mois.replace("fevrier", "février")
    mois = mois.replace("aout", "août")
    mois = mois.replace("decembre", "décembre")

    return (
        f"{int(match.group(1)):02d} "
        f"{mois} "
        f"{match.group(3)}"
    )


def trouver_programme(texte):
    """
    Identifie le type de session F1.

    On traite les qualifications sprint AVANT
    les qualifications classiques.
    """

    texte_lower = texte.lower()

    # -----------------------------------------------------
    # EXCLUSIONS
    # -----------------------------------------------------

    for exclusion in EXCLUSIONS:

        if exclusion in texte_lower:
            return None

    # -----------------------------------------------------
    # QUALIFICATIONS SPRINT
    # -----------------------------------------------------

    if (
        "qualifications sprint" in texte_lower
        or "qualification sprint" in texte_lower
        or "qualifs sprint" in texte_lower
        or "qualif sprint" in texte_lower
    ):
        return "Qualifications Sprint"

    # -----------------------------------------------------
    # ESSAIS LIBRES
    # -----------------------------------------------------

    for numero in ("1", "2", "3"):

        if (
            f"essais libres {numero}" in texte_lower
            or f"essai libre {numero}" in texte_lower
            or f"essais libre {numero}" in texte_lower
        ):
            return f"Essais Libres {numero}"

    # -----------------------------------------------------
    # ESSAIS LIBRES SANS NUMÉRO
    # -----------------------------------------------------

    if (
        "essais libres" in texte_lower
        or "essai libre" in texte_lower
    ):
        return "Essais Libres"

    # -----------------------------------------------------
    # QUALIFICATIONS
    # -----------------------------------------------------

    if (
        "qualifications" in texte_lower
        or "qualification" in texte_lower
        or "qualifs" in texte_lower
        or "qualif" in texte_lower
    ):
        return "Qualifications"

    # -----------------------------------------------------
    # SPRINT
    # -----------------------------------------------------

    if re.search(r"\bsprint\b", texte_lower):
        return "Sprint"

    # -----------------------------------------------------
    # GRAND PRIX
    # -----------------------------------------------------

    if "grand prix" in texte_lower:

        # On essaie de récupérer le nom du Grand Prix.
        # Exemples :
        # Grand Prix des Pays-Bas
        # Grand Prix d'Italie
        # Grand Prix de Belgique

        match = re.search(
            r"(grand prix(?:\s+(?:de|du|des|d'|de la|de l')"
            r"\s+[^|,\n]+)?)",
            texte,
            re.IGNORECASE
        )

        if match:

            programme = nettoyer(match.group(1))

            # On évite de récupérer des informations
            # supplémentaires après le nom du GP.
            programme = re.split(
                r"\s+(?:canal\+|canal\s*\+)\b",
                programme,
                flags=re.IGNORECASE
            )[0]

            return programme

        return "Grand Prix"

    return None


def trouver_chaine(bloc):
    """
    Recherche la chaîne dans le bloc.
    """

    # On regarde d'abord les chaînes individuelles
    for element in bloc.stripped_strings:

        texte = nettoyer(element)

        if est_canal(texte):

            # On évite de retourner un énorme bloc.
            # On cherche simplement la partie Canal+.
            match = re.search(
                r"(Canal\s*\+\s*(?:Sport\s*360|Sport|Foot|Décalé)?|Canal\+)",
                texte,
                re.IGNORECASE
            )

            if match:
                return nettoyer(match.group(1))

            return texte

    # Si la chaîne n'est pas isolée, on la cherche
    # dans le texte complet du bloc.
    texte_bloc = nettoyer(
        bloc.get_text(" ", strip=True)
    )

    match = re.search(
        r"(Canal\s*\+\s*(?:Sport\s*360|Sport|Foot|Décalé)?|Canal\+)",
        texte_bloc,
        re.IGNORECASE
    )

    if match:
        return nettoyer(match.group(1))

    return None


# =========================================================
# EXTRACTION
# =========================================================

diffusions = []

# Nous partons des éléments contenant "Formule 1".
# Ensuite nous remontons progressivement dans le DOM
# pour trouver le bloc correspondant à une diffusion.

elements = soup.find_all(
    string=lambda text: (
        text is not None
        and "Formule 1" in text
    )
)

print()

for element in elements:

    bloc = element.parent

    candidats = []

    # -----------------------------------------------------
    # RECHERCHE DU BLOC DE DIFFUSION
    # -----------------------------------------------------

    for niveau in range(1, 10):

        if bloc is None:
            break

        texte = nettoyer(
            bloc.get_text(" ", strip=True)
        )

        # Le bloc doit au minimum contenir :
        # - une heure
        # - un direct
        # - Canal+
        #
        # On ne demande PAS encore le programme ici.
        # Cela évite le problème rencontré précédemment
        # avec la structure HTML de TV-Sports.

        if (
            trouver_heure(texte)
            and est_direct(texte)
            and est_canal(texte)
        ):
            candidats.append(
                (
                    len(texte),
                    bloc,
                    texte
                )
            )

        bloc = bloc.parent

    if not candidats:
        continue

    # Le plus petit bloc pertinent est généralement
    # celui correspondant à la diffusion.
    candidats.sort(
        key=lambda x: x[0]
    )

    _, bloc, texte = candidats[0]

    # -----------------------------------------------------
    # DIRECT UNIQUEMENT
    # -----------------------------------------------------

    if not est_direct(texte):
        continue

    # -----------------------------------------------------
    # PAS DE REDIFFUSION
    # -----------------------------------------------------

    if est_rediffusion(texte):
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
    # CHAÎNE
    # -----------------------------------------------------

    chaine = trouver_chaine(bloc)

    if not chaine:
        continue

    # -----------------------------------------------------
    # VÉRIFICATION FINALE
    # -----------------------------------------------------

    diffusion = {
        "date": date,
        "heure": heure,
        "programme": programme,
        "chaine": chaine,
    }

    # -----------------------------------------------------
    # DÉDOUBLONNAGE
    # -----------------------------------------------------

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


diffusions.sort(
    key=cle_tri
)


# =========================================================
# AFFICHAGE
# =========================================================

print()

if not diffusions:

    print("❌ Aucune diffusion F1 en direct trouvée.")

else:

    for i, diffusion in enumerate(
        diffusions,
        start=1
    ):

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
    f"✅ {len(diffusions)} diffusion(s) "
    f"F1 en direct trouvée(s)"
)
