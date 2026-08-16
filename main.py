import requests
from bs4 import BeautifulSoup
import re

URL = "https://tv-sports.fr/base-ball/mlb_tv/"

print("🔎 RECHERCHE DES DATES ASSOCIÉES AUX DIFFUSIONS MLB")
print("=" * 60)

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

channels = soup.find_all(
    "span",
    class_="schedule-channel__name"
)

# Reconnaît par exemple :
# lundi 17 août 2026
# mardi 18 août 2026
date_pattern = re.compile(
    r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)"
    r"\s+\d{1,2}\s+"
    r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)"
    r"\s+\d{4}",
    re.IGNORECASE
)

for i, channel in enumerate(channels, 1):

    # Bloc de diffusion
    bloc = channel

    for _ in range(4):
        bloc = bloc.parent

    texte = bloc.get_text(" ", strip=True)

    # On remonte progressivement dans les parents
    # jusqu'à trouver un conteneur contenant une date.
    parent = bloc
    date_trouvee = None

    for niveau in range(1, 10):

        parent = parent.parent

        if parent is None:
            break

        texte_parent = parent.get_text(" ", strip=True)

        match = date_pattern.search(texte_parent)

        if match:
            date_trouvee = match.group(0)
            break

    print(f"{i:02d}. [{date_trouvee or 'DATE INCONNUE'}] {texte}")
