import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


print("🔎 EXTRACTION DES DIFFUSIONS F1")
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


# Chaînes Canal+ acceptées
CHAINES_CANAL = [
    "canal+",
    "canal +",
]


# =========================================================
# PROGRAMMES F1 AUTORISÉS
# =========================================================

PROGRAMMES = [
    "grand prix",
    "qualifications sprint",
    "qualification sprint",
    "qualifs sprint",
    "qualif sprint",
    "sprint",
    "essais libres",
    "essai libre",
    "qualifications",
    "qualification",
    "qualifs",
    "qualif",
]


# =========================================================
# PROGRAMMES / ÉMISSIONS À EXCLURE
# =========================================================

EXCLUSIONS = [
    "on board",
    "onboard",
    "le podium",
    "formula one",
    "formula one, le mag",
    "formula one - le mag",
    "le mag",
    "la grille",
    "fractionné",
    "fractionne",
    "parade des pilotes",
    "fabrique des rêves",
    "la fabrique des rêves",
    "bleu, blanc, vite",
    "vivez en direct les évènements",
]


# =========================================================
# MOIS / JOURS
# =========================================================

MOIS = {
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

JOURS = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}


# =========================================================
# DATE ACTUELLE
# =========================================================

AUJOURD_HUI = datetime.now(
    ZoneInfo("Europe/Paris")
).date()


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


# =========================================================
# FONCTIONS GÉNÉRALES
# =========================================================

def nettoyer(texte):
    """
    Nettoie les espaces et retours à la ligne.
    """
    if not texte:
        return ""

    return " ".join(texte.split())


def texte_lower(texte):
    return nettoyer(texte).lower()


def est_canal(texte):
    """
    Vérifie si le texte contient une chaîne Canal+.
    """
    texte = texte_lower(texte)

    return any(
        chaine in texte
        for chaine in CHAINES_CANAL
    )


def est_direct(texte):
    """
    Vrai uniquement si le bloc contient DIRECT.
    """
    texte = texte_lower(texte)

    return (
        "direct" in texte
        or "en direct" in texte
    )


def est_rediffusion(texte):
    """
    Détecte les rediffusions.
    """
    texte = texte_lower(texte)

    mots = [
        "rediffusion",
        "rediff.",
        "rediff",
    ]

    return any(
        mot in texte
        for mot in mots
    )


def est_exclu(texte):
    """
    Exclut les magazines et émissions F1
    qui ne sont pas les sessions / courses.
    """
    texte = texte_lower(texte)

    return any(
        exclusion in texte
        for exclusion in EXCLUSIONS
    )


# =========================================================
# EXTRACTION DE L'HEURE
# =========================================================

def trouver_heure(texte):

    patterns = [
        r"\b(\d{1,2})h(\d{2})\b",
        r"\b(\d{1,2}):(\d{2})\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            texte,
            re.IGNORECASE
        )

        if match:

            heure = int(match.group(1))
            minute = int(match.group(2))

            if 0 <= heure <= 23 and 0 <= minute <= 59:

                return (
                    f"{heure:02d}h"
                    f"{minute:02d}"
                )

    return None


# =========================================================
# EXTRACTION DATE COMPLÈTE
# =========================================================

def trouver_date_complete(texte):

    pattern = (
        r"(?:lundi|mardi|mercredi|jeudi|vendredi|"
        r"samedi|dimanche)"
        r"\s+"
        r"(\d{1,2})"
        r"\s+"
        r"(janvier|février|mars|avril|mai|juin|juillet|"
        r"août|septembre|octobre|novembre|décembre)"
        r"\s+"
        r"(\d{4})"
    )

    match = re.search(
        pattern,
        texte,
        re.IGNORECASE
    )

    if not match:
        return None

    jour = int(match.group(1))
    mois = match.group(2).lower()
    annee = int(match.group(3))

    if mois not in MOIS:
        return None

    try:

        date = datetime(
            annee,
            MOIS[mois],
            jour
        ).date()

    except ValueError:
        return None

    return date


# =========================================================
# EXTRACTION DES DATES COURTES
# =========================================================

def trouver_date_courte(texte):

    pattern = (
        r"\b(\d{1,2})/(\d{1,2})"
        r"(?:/(\d{4}))?\b"
    )

    match = re.search(
        pattern,
        texte
    )

    if not match:
        return None

    jour = int(match.group(1))
    mois = int(match.group(2))

    annee = (
        int(match.group(3))
        if match.group(3)
        else AUJOURD_HUI.year
    )

    try:

        return datetime(
            annee,
            mois,
            jour
        ).date()

    except ValueError:
        return None


# =========================================================
# DATES RELATIVES
# =========================================================

def trouver_date_relative(texte):

    texte_lower = texte_lower(texte)

    if "aujourd'hui" in texte_lower:
        return AUJOURD_HUI

    if "demain" in texte_lower:
        return AUJOURD_HUI + timedelta(days=1)

    if "après-demain" in texte_lower:
        return AUJOURD_HUI + timedelta(days=2)

    return None


# =========================================================
# DATE À PARTIR D'UN JOUR DE LA SEMAINE
# =========================================================

def trouver_date_jour_semaine(texte):

    texte_lower_value = texte_lower(texte)

    for nom_jour, numero_jour in JOURS.items():

        if nom_jour in texte_lower_value:

            delta = (
                numero_jour
                - AUJOURD_HUI.weekday()
            ) % 7

            return (
                AUJOURD_HUI
                + timedelta(days=delta)
            )

    return None


# =========================================================
# DATE DEPUIS UN TEXTE
# =========================================================

def extraire_date(texte):

    # 1. Date complète
    date = trouver_date_complete(texte)

    if date:
        return date

    # 2. Date courte
    date = trouver_date_courte(texte)

    if date:
        return date

    # 3. Aujourd'hui / demain
    date = trouver_date_relative(texte)

    if date:
        return date

    # 4. Jour de la semaine
    date = trouver_date_jour_semaine(texte)

    if date:
        return date

    return None


# =========================================================
# EXTRACTION DU PROGRAMME
# =========================================================

def trouver_programme(texte):

    texte_original = nettoyer(texte)
    texte_lower_value = texte_original.lower()

    # -----------------------------------------------------
    # EXCLUSIONS
    # -----------------------------------------------------

    if est_exclu(texte_original):
        return None

    # -----------------------------------------------------
    # GRAND PRIX
    # -----------------------------------------------------

    if "grand prix" in texte_lower_value:

        # On cherche notamment :
        # Grand Prix des Pays-Bas
        # Grand Prix de Hongrie
        # Grand Prix d'Italie
        # etc.

        match = re.search(
            r"(grand prix\s+"
            r"(?:de|du|des|d'|de la|de l')?"
            r"\s*"
            r"[^|]+?)"
            r"(?=\s+(?:sur|canal\+|canal \+|direct|rediffusion|"
            r"\d{1,2}h\d{2}|image|$))",
            texte_original,
            re.IGNORECASE
        )

        if match:

            programme = nettoyer(
                match.group(1)
            )

            # Nettoyage final
            programme = re.sub(
                r"\s+$",
                "",
                programme
            )

            return programme

        return "Grand Prix"

    # -----------------------------------------------------
    # QUALIFICATIONS SPRINT
    # -----------------------------------------------------

    if (
        "qualifications sprint" in texte_lower_value
        or "qualification sprint" in texte_lower_value
        or "qualifs sprint" in texte_lower_value
        or "qualif sprint" in texte_lower_value
    ):
        return "Qualifications Sprint"

    # -----------------------------------------------------
    # SPRINT
    # -----------------------------------------------------

    if re.search(
        r"\bsprint\b",
        texte_lower_value
    ):
        return "Sprint"

    # -----------------------------------------------------
    # QUALIFICATIONS
    # -----------------------------------------------------

    if (
        "qualifications" in texte_lower_value
        or "qualification" in texte_lower_value
        or "qualifs" in texte_lower_value
        or "qualif" in texte_lower_value
    ):
        return "Qualifications"

    # -----------------------------------------------------
    # ESSAIS LIBRES
    # -----------------------------------------------------

    if (
        "essais libres" in texte_lower_value
        or "essai libre" in texte_lower_value
    ):
        return "Essais libres"

    return None


# =========================================================
# EXTRACTION DE LA CHAÎNE
# =========================================================

def trouver_chaine(bloc):

    # On cherche d'abord les textes courts,
    # car le nom de la chaîne est généralement
    # isolé dans son propre élément.

    for element in bloc.stripped_strings:

        texte = nettoyer(element)

        if not texte:
            continue

        if est_canal(texte):

            # On évite de retourner tout un paragraphe
            # contenant Canal+.

            if len(texte) <= 80:
                return texte

    # Deuxième tentative :
    # recherche dans le texte global du bloc.

    texte = nettoyer(
        bloc.get_text(
            " ",
            strip=True
        )
    )

    match = re.search(
        r"(Canal\s*\+\s*Sport\s*360|"
        r"Canal\s*\+\s*Sport|"
        r"Canal\s*\+)",
        texte,
        re.IGNORECASE
    )

    if match:
        return nettoyer(
            match.group(1)
        )

    return None


# =========================================================
# RECHERCHE DU MEILLEUR BLOC DE DIFFUSION
# =========================================================

def trouver_bloc_diffusion(element):

    """
    À partir d'un élément contenant "Formule 1",
    on remonte dans le DOM pour trouver le plus petit
    bloc contenant simultanément :

    - Formule 1
    - DIRECT
    - Canal+
    - une heure
    """

    bloc = element.parent

    candidats = []

    for niveau in range(1, 12):

        if bloc is None:
            break

        texte = nettoyer(
            bloc.get_text(
                " ",
                strip=True
            )
        )

        texte_lower_value = texte.lower()

        if len(texte) > 1800:
            bloc = bloc.parent
            continue

        if (
            "formule 1" in texte_lower_value
            and est_direct(texte)
            and est_canal(texte)
            and trouver_heure(texte)
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
        return None

    candidats.sort(
        key=lambda x: x[0]
    )

    return candidats[0]


# =========================================================
# RECHERCHE DU CONTEXTE DE DATE
# =========================================================

def trouver_date_dans_contexte(element):

    """
    Si la date n'est pas dans le bloc de diffusion,
    on remonte dans les éléments précédents de la page.

    Le site utilise notamment des sections du type :

        Aujourd'hui

        ... diffusion ...

        lundi 17 août 2026

        ... diffusion ...
    """

    # -----------------------------------------------------
    # 1. Chercher dans les parents immédiats
    # -----------------------------------------------------

    parent = element.parent

    for _ in range(6):

        if parent is None:
            break

        texte_parent = nettoyer(
            parent.get_text(
                " ",
                strip=True
            )
        )

        date = extraire_date(
            texte_parent
        )

        if date:
            return date

        parent = parent.parent

    # -----------------------------------------------------
    # 2. Chercher dans les éléments précédents
    # -----------------------------------------------------

    courant = element

    for _ in range(30):

        precedent = courant.find_previous()

        if precedent is None:
            break

        texte = nettoyer(
            precedent.get_text(
                " ",
                strip=True
            )
        )

        if not texte:
            courant = precedent
            continue

        # On limite la recherche aux textes
        # qui ressemblent réellement à un titre de date.

        if len(texte) <= 100:

            date = extraire_date(
                texte
            )

            if date:
                return date

        courant = precedent

    return None


# =========================================================
# EXTRACTION PRINCIPALE
# =========================================================

diffusions = []


# On recherche toutes les occurrences de "Formule 1"
# sans dépendre de la casse.

elements_formule_1 = soup.find_all(
    string=lambda text: (
        text
        and "formule 1" in text.lower()
    )
)


for element in elements_formule_1:

    resultat = trouver_bloc_diffusion(
        element
    )

    if not resultat:
        continue

    _, bloc, texte = resultat

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
    # PAS DE MAGAZINE / ÉMISSION
    # -----------------------------------------------------

    if est_exclu(texte):
        continue

    # -----------------------------------------------------
    # CHAÎNE
    # -----------------------------------------------------

    chaine = trouver_chaine(
        bloc
    )

    if not chaine:
        continue

    # -----------------------------------------------------
    # PROGRAMME
    # -----------------------------------------------------

    programme = trouver_programme(
        texte
    )

    if not programme:
        continue

    # -----------------------------------------------------
    # HEURE
    # -----------------------------------------------------

    heure = trouver_heure(
        texte
    )

    if not heure:
        continue

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    date = extraire_date(
        texte
    )

    # Si la date n'est pas directement dans
    # le bloc, on cherche son contexte.

    if not date:

        date = trouver_date_dans_contexte(
            element
        )

    if not date:
        continue

    # -----------------------------------------------------
    # FORMAT DATE
    # -----------------------------------------------------

    date_formatee = (
        f"{date.day:02d} "
        f"{list(MOIS.keys())[date.month - 1]} "
        f"{date.year}"
    )

    # -----------------------------------------------------
    # DIFFUSION
    # -----------------------------------------------------

    diffusion = {
        "date_obj": date,
        "date": date_formatee,
        "heure": heure,
        "programme": programme,
        "chaine": chaine,
    }

    # -----------------------------------------------------
    # DÉDOUBLONNAGE
    # -----------------------------------------------------

    existe = any(
        d["date_obj"] == diffusion["date_obj"]
        and d["heure"] == diffusion["heure"]
        and d["programme"] == diffusion["programme"]
        and d["chaine"] == diffusion["chaine"]
        for d in diffusions
    )

    if not existe:
        diffusions.append(
            diffusion
        )


# =========================================================
# TRI CHRONOLOGIQUE
# =========================================================

diffusions.sort(
    key=lambda diffusion: (
        diffusion["date_obj"],
        int(diffusion["heure"].split("h")[0]),
        int(diffusion["heure"].split("h")[1]),
    )
)


# =========================================================
# AFFICHAGE
# =========================================================

print()


if not diffusions:

    print(
        "❌ Aucune diffusion F1 en direct trouvée."
    )

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
