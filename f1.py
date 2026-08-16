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


# =========================================================
# CHAÎNES CANAL+ ACCEPTÉES
# =========================================================

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
# MOIS
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


print(
    f"✅ Page téléchargée : "
    f"{len(response.text)} caractères"
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

    return " ".join(
        texte.split()
    )


def lower(texte):
    return nettoyer(texte).lower()


# =========================================================
# CANAL+
# =========================================================

def trouver_chaine(texte):
    """
    Retourne le nom de la chaîne Canal+ présent
    dans le texte de l'événement.
    """

    texte_nettoye = nettoyer(texte)

    match = re.search(
        r"(Canal\s*\+\s*Sport\s*360|"
        r"Canal\s*\+\s*Sport|"
        r"Canal\s*\+)",
        texte_nettoye,
        re.IGNORECASE
    )

    if match:
        return nettoyer(
            match.group(1)
        )

    return None


# =========================================================
# DIRECT
# =========================================================

def est_direct(texte):
    """
    Un événement est considéré comme direct si
    son statut contient DIRECT.

    Attention :
    on ne considère PAS simplement la présence
    de 'en direct' dans la page entière.
    """

    texte_lower = lower(texte)

    return (
        "direct" in texte_lower
        and "rediff" not in texte_lower
    )


# =========================================================
# REDIFFUSION
# =========================================================

def est_rediffusion(texte):

    texte_lower = lower(texte)

    return (
        "rediffusion" in texte_lower
        or "rediff." in texte_lower
        or "rediff" in texte_lower
    )


# =========================================================
# EXCLUSION
# =========================================================

def est_exclu(texte):

    texte_lower = lower(texte)

    for exclusion in EXCLUSIONS:

        if exclusion in texte_lower:
            return True

    return False


# =========================================================
# HEURE
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

        if not match:
            continue

        heure = int(
            match.group(1)
        )

        minute = int(
            match.group(2)
        )

        if (
            0 <= heure <= 23
            and
            0 <= minute <= 59
        ):

            return (
                f"{heure:02d}h"
                f"{minute:02d}"
            )

    return None


# =========================================================
# DATE COMPLÈTE
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

    jour = int(
        match.group(1)
    )

    mois = match.group(2).lower()

    annee = int(
        match.group(3)
    )

    if mois not in MOIS:
        return None

    try:

        return datetime(
            annee,
            MOIS[mois],
            jour
        ).date()

    except ValueError:

        return None


# =========================================================
# DATE COURTE
# =========================================================

def trouver_date_courte(texte):

    pattern = (
        r"\b"
        r"(\d{1,2})"
        r"/"
        r"(\d{1,2})"
        r"(?:/(\d{4}))?"
        r"\b"
    )

    match = re.search(
        pattern,
        texte
    )

    if not match:
        return None

    jour = int(
        match.group(1)
    )

    mois = int(
        match.group(2)
    )

    if match.group(3):

        annee = int(
            match.group(3)
        )

    else:

        annee = AUJOURD_HUI.year

    try:

        return datetime(
            annee,
            mois,
            jour
        ).date()

    except ValueError:

        return None


# =========================================================
# DATE RELATIVE
# =========================================================

def trouver_date_relative(texte):

    texte_lower = lower(texte)

    if "aujourd'hui" in texte_lower:

        return AUJOURD_HUI

    if "demain" in texte_lower:

        return (
            AUJOURD_HUI
            + timedelta(days=1)
        )

    if "après-demain" in texte_lower:

        return (
            AUJOURD_HUI
            + timedelta(days=2)
        )

    return None


# =========================================================
# EXTRACTION DATE
# =========================================================

def extraire_date(texte):

    date = trouver_date_complete(
        texte
    )

    if date:
        return date

    date = trouver_date_courte(
        texte
    )

    if date:
        return date

    date = trouver_date_relative(
        texte
    )

    if date:
        return date

    return None


# =========================================================
# PROGRAMME
# =========================================================

def trouver_programme(texte):

    texte_original = nettoyer(
        texte
    )

    texte_lower = texte_original.lower()

    # -----------------------------------------------------
    # EXCLUSIONS
    # -----------------------------------------------------

    if est_exclu(
        texte_original
    ):
        return None


    # -----------------------------------------------------
    # GRAND PRIX
    # -----------------------------------------------------

    if "grand prix" in texte_lower:

        # Exemple :
        #
        # Formule 1
        # Grand Prix de Hongrie
        # Canal+ Sport 360
        #
        # On récupère uniquement le nom du GP.

        match = re.search(
            r"\b("
            r"grand prix"
            r"(?:\s+de|\s+du|\s+des|\s+d'|\s+de la|\s+de l')?"
            r"\s+"
            r"[^|]+?"
            r")"
            r"(?=\s+"
            r"(?:canal|direct|rediff|"
            r"\d{1,2}h\d{2}|$))",
            texte_original,
            re.IGNORECASE
        )

        if match:

            programme = nettoyer(
                match.group(1)
            )

            # On retire d'éventuels doublons
            # du type :
            #
            # Grand Prix de Hongrie Grand Prix de Hongrie

            programme = re.sub(
                r"\b("
                r"Grand Prix"
                r"[^,]*?"
                r")\s+\1\b",
                r"\1",
                programme,
                flags=re.IGNORECASE
            )

            return programme

        return "Grand Prix"


    # -----------------------------------------------------
    # QUALIFICATIONS SPRINT
    # -----------------------------------------------------

    if (
        "qualifications sprint"
        in texte_lower
        or
        "qualification sprint"
        in texte_lower
        or
        "qualifs sprint"
        in texte_lower
        or
        "qualif sprint"
        in texte_lower
    ):

        return "Qualifications Sprint"


    # -----------------------------------------------------
    # SPRINT
    # -----------------------------------------------------

    if re.search(
        r"\bsprint\b",
        texte_lower
    ):

        return "Sprint"


    # -----------------------------------------------------
    # QUALIFICATIONS
    # -----------------------------------------------------

    if (
        "qualifications"
        in texte_lower
        or
        "qualification"
        in texte_lower
        or
        "qualifs"
        in texte_lower
        or
        "qualif"
        in texte_lower
    ):

        return "Qualifications"


    # -----------------------------------------------------
    # ESSAIS LIBRES
    # -----------------------------------------------------

    if (
        "essais libres"
        in texte_lower
        or
        "essai libre"
        in texte_lower
    ):

        return "Essais libres"


    return None


# =========================================================
# FORMAT DATE
# =========================================================

def formater_date(date):

    mois_nom = list(
        MOIS.keys()
    )[date.month - 1]

    return (
        f"{date.day:02d} "
        f"{mois_nom} "
        f"{date.year}"
    )


# =========================================================
# RECHERCHE DE LA LISTE DES PROGRAMMES
# =========================================================

schedule_lists = soup.select(
    "ol.schedule-list"
)


print()
print(
    f"📋 Listes de programmes trouvées : "
    f"{len(schedule_lists)}"
)


if not schedule_lists:

    print()
    print(
        "❌ Impossible de trouver "
        "ol.schedule-list"
    )

    raise SystemExit(1)


# =========================================================
# EXTRACTION DES ÉVÉNEMENTS
# =========================================================

diffusions = []

evenements_total = 0


for schedule in schedule_lists:

    # -----------------------------------------------------
    # Les événements sont les enfants directs <li>
    # -----------------------------------------------------

    evenements = schedule.find_all(
        "li",
        recursive=False
    )

    evenements_total += len(
        evenements
    )

    print(
        f"   → {len(evenements)} événements "
        f"dans cette liste"
    )


    # Date courante du groupe

    date_courante = None


    for evenement in evenements:

        texte = nettoyer(
            evenement.get_text(
                " ",
                strip=True
            )
        )

        if not texte:
            continue


        # -------------------------------------------------
        # DATE
        # -------------------------------------------------

        date_trouvee = extraire_date(
            texte
        )

        if date_trouvee:

            date_courante = date_trouvee


        # -------------------------------------------------
        # HEURE
        # -------------------------------------------------

        heure = trouver_heure(
            texte
        )

        if not heure:
            continue


        # -------------------------------------------------
        # CANAL+
        # -------------------------------------------------

        chaine = trouver_chaine(
            texte
        )

        if not chaine:
            continue


        # -------------------------------------------------
        # REDIFFUSION
        # -------------------------------------------------

        if est_rediffusion(
            texte
        ):
            continue


        # -------------------------------------------------
        # DIRECT
        # -------------------------------------------------

        if not est_direct(
            texte
        ):

            # DEBUG léger :
            # on ne conserve pas les magazines,
            # mais on peut vérifier pourquoi
            # une entrée n'est pas retenue.

            continue


        # -------------------------------------------------
        # EXCLUSIONS
        # -------------------------------------------------

        if est_exclu(
            texte
        ):
            continue


        # -------------------------------------------------
        # PROGRAMME
        # -------------------------------------------------

        programme = trouver_programme(
            texte
        )

        if not programme:
            continue


        # -------------------------------------------------
        # DATE
        # -------------------------------------------------

        if not date_courante:
            continue


        # -------------------------------------------------
        # OBJET
        # -------------------------------------------------

        diffusion = {

            "date_obj": date_courante,

            "date": formater_date(
                date_courante
            ),

            "heure": heure,

            "programme": programme,

            "chaine": chaine,

        }


        # -------------------------------------------------
        # DÉDOUBLONNAGE
        # -------------------------------------------------

        existe = any(

            d["date_obj"]
            == diffusion["date_obj"]

            and

            d["heure"]
            == diffusion["heure"]

            and

            d["programme"]
            == diffusion["programme"]

            and

            d["chaine"]
            == diffusion["chaine"]

            for d in diffusions

        )


        if not existe:

            diffusions.append(
                diffusion
            )


# =========================================================
# TRI
# =========================================================

diffusions.sort(
    key=lambda diffusion: (
        diffusion["date_obj"],
        int(
            diffusion["heure"]
            .split("h")[0]
        ),
        int(
            diffusion["heure"]
            .split("h")[1]
        ),
    )
)


# =========================================================
# AFFICHAGE
# =========================================================

print()
print("=" * 80)
print("📺 DIFFUSIONS F1 CANAL+ EN DIRECT")
print("=" * 80)


if not diffusions:

    print()
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
            f"🏁 {diffusion['programme']} "
            f"📺 {diffusion['chaine']}"
        )


# =========================================================
# RÉSUMÉ
# =========================================================

print()
print("=" * 80)

print(
    f"📊 Événements analysés : "
    f"{evenements_total}"
)

print(
    f"✅ Diffusions retenues : "
    f"{len(diffusions)}"
)

print("=" * 80)
