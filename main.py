import requests
from bs4 import BeautifulSoup
import re

URL = "https://tv-sports.fr/base-ball/mlb_tv/"

print("🔎 EXTRACTION DES DIFFUSIONS MLB")
print("=" * 60)

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

schedule = soup.find(
    "ol",
    class_="schedule-list"
)

if not schedule:
    raise Exception("Planning MLB introuvable")

# Dates françaises présentes dans la page
pattern_date = re.compile(
    r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)"
    r"\s+\d{1,2}\s+"
    r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)"
    r"\s+\d{4}",
    re.IGNORECASE
)

date_actuelle = None
numero = 0

# On parcourt TOUS les éléments du planning dans leur ordre réel
for element in schedule.find_all(["li", "h2", "h3", "div"], recursive=True):

    texte = element.get_text(" ", strip=True)

    # Cherche une date dans cet élément
    match_date = pattern_date.search(texte)

    if match_date:
        date_actuelle = match_date.group(0)

    # Une diffusion est identifiée par schedule-item
    if (
        element.name == "li"
        and "schedule-item" in (element.get("class") or [])
    ):
        channel = element.find(
            "span",
            class_="schedule-channel__name"
        )

        if not channel:
            continue

        numero += 1

        diffusion = element.get_text(" ", strip=True)

        print(
            f"{numero:02d}. "
            f"[{date_actuelle or 'DATE INCONNUE'}] "
            f"{diffusion}"
        )
