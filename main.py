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

# On parcourt chaque chaîne trouvée
for i, channel in enumerate(channels, 1):

    # On remonte jusqu'au bloc contenant la diffusion
    bloc = channel

    for _ in range(4):
        bloc = bloc.parent

    texte = bloc.get_text(" ", strip=True)

    # On cherche le bloc de date qui contient cette diffusion
    date_bloc = bloc

    while date_bloc is not None:

        # On regarde si un élément contenant une date est présent
        date_element = date_bloc.find_previous(
            class_="schedule-date"
        )

        if date_element:
            date = date_element.get_text(" ", strip=True)
            break

        date_bloc = date_bloc.parent

    else:
        date = "DATE INCONNUE"

    print(f"{i:02d}. [{date}] {texte}")
