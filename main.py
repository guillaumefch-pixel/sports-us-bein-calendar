import requests
from bs4 import BeautifulSoup

URL = "https://tv-sports.fr/base-ball/mlb_tv/"

print("🔎 Recherche de la structure des diffusions MLB")
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

print(f"Nombre de chaînes trouvées : {len(channels)}")
print()

for i, channel in enumerate(channels[:3], 1):

    print(f"================ DIFFUSION {i} ================")

    # On remonte progressivement dans le HTML
    parent = channel

    for niveau in range(1, 7):
        parent = parent.parent

        if parent is None:
            break

        texte = parent.get_text(" ", strip=True)

        print(f"\n--- Niveau {niveau} ---")
        print(texte[:1500])

    print("\n")
