import requests
from bs4 import BeautifulSoup
from datetime import datetime


print("🔎 EXTRACTION COMPLÈTE DU WEEK-END F1")
print("=" * 90)


URL = "https://tv-sports.fr/formule-1/"

HEADERS = {
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
    headers=HEADERS,
    timeout=20
)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

print(f"✅ Page téléchargée : {len(response.text)} caractères")


# =========================================================
# RÉCUPÉRATION DES ÉVÉNEMENTS
# =========================================================

evenements = soup.select(
    "ol.schedule-list li.schedule-item"
)

print(f"📋 Événements trouvés : {len(evenements)}")


# =========================================================
# WEEK-END DU GP DES PAYS-BAS
# =========================================================

DATE_DEBUT = "2026-08-21"
DATE_FIN = "2026-08-23"


diffusions = []


# =========================================================
# ANALYSE
# =========================================================

for evenement in evenements:

    # -----------------------------------------------------
    # On garde uniquement la Formule 1
    # -----------------------------------------------------

    if evenement.get("data-sport-id") != "102":
        continue


    # -----------------------------------------------------
    # Récupération de l'heure/date
    # -----------------------------------------------------

    time_element = evenement.select_one(
        "time.schedule-time"
    )

    if not time_element:
        continue


    datetime_str = time_element.get("datetime")

    if not datetime_str:
        continue


    # -----------------------------------------------------
    # Conversion date
    # -----------------------------------------------------

    try:
        date_obj = datetime.fromisoformat(
            datetime_str
        )

    except ValueError:
        continue


    date_str = date_obj.strftime("%Y-%m-%d")


    # -----------------------------------------------------
    # On garde uniquement vendredi → dimanche
    # -----------------------------------------------------

    if not (
        DATE_DEBUT <= date_str <= DATE_FIN
    ):
        continue


    # -----------------------------------------------------
    # Type de diffusion
    # -----------------------------------------------------

    diffusion_type = evenement.get(
        "data-diffusion-type",
        ""
    )


    # On veut uniquement le direct
    if diffusion_type != "live":
        continue


    # -----------------------------------------------------
    # Heure
    # -----------------------------------------------------

    heure = date_obj.strftime("%Hh%M")


    # -----------------------------------------------------
    # Nom du programme
    # -----------------------------------------------------

    titre = None

    lien_programme = evenement.select_one(
        "a[title]"
    )

    if lien_programme:
        titre = lien_programme.get("title")


    if not titre:

        titre_element = evenement.select_one(
            ".schedule-program__body"
        )

        if titre_element:
            titre = titre_element.get_text(
                " ",
                strip=True
            )


    if not titre:
        titre = "Formule 1"


    # -----------------------------------------------------
    # CHAÎNES
    # -----------------------------------------------------

    chaines = []


    # Les logos des chaînes ont généralement
    # la classe logoChaine
    for image in evenement.select(
        "img.logoChaine"
    ):

        alt = image.get("alt")

        if alt:
            chaines.append(
                alt.strip()
            )


    # -----------------------------------------------------
    # Fallback : nom texte de la chaîne
    # -----------------------------------------------------

    if not chaines:

        for element in evenement.select(
            ".schedule-channel__name"
        ):

            texte = element.get_text(
                " ",
                strip=True
            )

            if texte:
                chaines.append(
                    texte
                )


    # Suppression des doublons
    chaines = list(
        dict.fromkeys(chaines)
    )


    if chaines:
        chaine = " / ".join(chaines)
    else:
        chaine = "Chaîne inconnue"


    # -----------------------------------------------------
    # ID DES CHAÎNES
    # -----------------------------------------------------

    channel_id = evenement.get(
        "data-channel-id"
    )


    # -----------------------------------------------------
    # TEXTE COMPLET
    # -----------------------------------------------------

    texte_complet = evenement.get_text(
        " ",
        strip=True
    )


    # -----------------------------------------------------
    # DÉTECTION DU TYPE DE SÉANCE
    # -----------------------------------------------------

    texte_lower = texte_complet.lower()


    if "qualification" in texte_lower:
        session = "Qualifications"

    elif "qualif" in texte_lower:
        session = "Qualifications"

    elif "essai libre 1" in texte_lower:
        session = "EL1"

    elif "essais libres 1" in texte_lower:
        session = "EL1"

    elif "essai libre 2" in texte_lower:
        session = "EL2"

    elif "essais libres 2" in texte_lower:
        session = "EL2"

    elif "essai libre 3" in texte_lower:
        session = "EL3"

    elif "essais libres 3" in texte_lower:
        session = "EL3"

    elif "fp1" in texte_lower:
        session = "EL1"

    elif "fp2" in texte_lower:
        session = "EL2"

    elif "fp3" in texte_lower:
        session = "EL3"

    elif "sprint" in texte_lower:
        session = "Sprint"

    elif "grand prix" in texte_lower:
        session = "Grand Prix"

    else:
        session = "Autre"


    # -----------------------------------------------------
    # SAUVEGARDE
    # -----------------------------------------------------

    diffusions.append({
        "datetime": datetime_str,
        "date": date_str,
        "heure": heure,
        "titre": titre,
        "session": session,
        "chaine": chaine,
        "channel_id": channel_id,
        "diffusion_type": diffusion_type,
        "texte": texte_complet
    })


# =========================================================
# TRI CHRONOLOGIQUE
# =========================================================

diffusions.sort(
    key=lambda x: x["datetime"]
)


# =========================================================
# AFFICHAGE
# =========================================================

print()
print("=" * 90)
print("📺 TOUTES LES DIFFUSIONS F1 DU WEEK-END")
print("=" * 90)


if not diffusions:

    print("❌ Aucune diffusion trouvée.")

else:

    for i, diffusion in enumerate(
        diffusions,
        start=1
    ):

        print()
        print(
            f"{i:02d}. "
            f"🏎️ {diffusion['date']} "
            f"⚡ {diffusion['heure']} "
            f"🏁 {diffusion['titre']} "
            f"📺 {diffusion['chaine']} "
            f"(ID {diffusion['channel_id']})"
        )

        print(
            f"    🔖 Session : {diffusion['session']}"
        )

        print(
            f"    🔖 Type : {diffusion['diffusion_type']}"
        )


# =========================================================
# RÉSUMÉ PAR JOUR
# =========================================================

print()
print("=" * 90)
print("📅 RÉSUMÉ PAR JOUR")
print("=" * 90)


dates = [
    "2026-08-21",
    "2026-08-22",
    "2026-08-23"
]


for date in dates:

    jour = [
        d for d in diffusions
        if d["date"] == date
    ]

    print()
    print(f"📅 {date}")

    if not jour:
        print("   Aucun événement")

    else:

        for diffusion in jour:

            print(
                f"   {diffusion['heure']} — "
                f"{diffusion['session']} — "
                f"{diffusion['titre']} — "
                f"{diffusion['chaine']}"
            )


# =========================================================
# RÉSUMÉ FINAL
# =========================================================

print()
print("=" * 90)
print(
    f"📊 {len(diffusions)} diffusion(s) "
    f"F1 en direct trouvée(s)"
)
print("=" * 90)

print()
print("🏁 DIAGNOSTIC TERMINÉ")
print("=" * 90)
