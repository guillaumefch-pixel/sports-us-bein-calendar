import requests
from bs4 import BeautifulSoup

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

channels = soup.find_all(
    "span",
    class_="schedule-channel__name"
)

for i, channel in enumerate(channels, 1):

    # Le niveau 4 correspond à la diffusion individuelle
    bloc = channel

    for _ in range(4):
        bloc = bloc.parent

    texte = bloc.get_text(" ", strip=True)

    print(f"{i:02d}. {texte}")
