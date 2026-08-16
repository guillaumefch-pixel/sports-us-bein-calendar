import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.tvsports.fr/sport/formule-1"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

print("🔎 EXTRACTION DES DIFFUSIONS F1")
print("=" * 80)

response = requests.get(URL, headers=HEADERS)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

blocks = soup.select("ol.schedule-list")

print(f"Nombre de blocs trouvés : {len(blocks)}")
print()
print("=" * 80)

EVENT_TYPES = [
    "Essais libres",
    "Qualifications Sprint",
    "Qualifs Sprint",
    "Qualifications",
    "Qualifs",
    "Sprint",
    "Grand Prix"
]

EXCLUDED_TYPES = [
    "Magazine",
    "On Board",
    "Le podium",
    "Formula One, le mag",
    "Fractionné",
    "Parade des pilotes",
    "La grille"
]

for block in blocks:

    items = block.select("li.schedule-item")

    current_date = None

    for item in items:

        text = item.get_text(" ", strip=True)

        # ---------------------------------------------------------
        # DATE
        # ---------------------------------------------------------

        date_element = item.find_previous(
            class_=lambda x: x and "schedule-date" in x
        )

        if date_element:
            current_date = date_element.get_text(" ", strip=True)

        # ---------------------------------------------------------
        # UNIQUEMENT CANAL+
        # ---------------------------------------------------------

        if "Canal+" not in text:
            continue

        # ---------------------------------------------------------
        # EXCLUSION DES MAGAZINES / ÉMISSIONS ANNEXES
        # ---------------------------------------------------------

        if any(
            excluded.lower() in text.lower()
            for excluded in EXCLUDED_TYPES
        ):
            continue

        # ---------------------------------------------------------
        # UNIQUEMENT LES ÉVÉNEMENTS F1 VOULUS
        # ---------------------------------------------------------

        if not any(
            event.lower() in text.lower()
            for event in EVENT_TYPES
        ):
            continue

        # ---------------------------------------------------------
        # EXCLUSION DES REDIFFUSIONS
        # ---------------------------------------------------------

        if "Rediff." in text:
            continue

        # ---------------------------------------------------------
        # EXTRACTION DE L'HEURE
        # ---------------------------------------------------------

        time_match = re.search(r"\b(\d{1,2}h\d{2})\b", text)

        if not time_match:
            continue

        time = time_match.group(1)

        # ---------------------------------------------------------
        # IDENTIFICATION DU TYPE D'ÉVÉNEMENT
        # ---------------------------------------------------------

        event_type = None

        if (
            "Qualifications Sprint" in text
            or "Qualifs Sprint" in text
        ):
            event_type = "Qualifications Sprint"

        elif "Sprint" in text:
            event_type = "Sprint"

        elif "Essais libres" in text:
            event_type = "Essais libres"

        elif (
            "Qualifications" in text
            or "Qualifs" in text
        ):
            event_type = "Qualifications"

        elif "Grand Prix" in text:
            event_type = "Grand Prix"

        if not event_type:
            continue

        # ---------------------------------------------------------
        # AFFICHAGE
        # ---------------------------------------------------------

        print(
            f"{current_date or 'DATE ?'} "
            f"🏎️ {time} "
            f"{event_type} "
            f"🏎️ {text}"
        )
