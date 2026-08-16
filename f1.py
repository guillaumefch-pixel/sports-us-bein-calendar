import requests
from bs4 import BeautifulSoup

URL = "https://tv-sports.fr/formule-1/"

print("🔎 EXTRACTION DES DIFFUSIONS F1")
print("=" * 80)

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# On récupère les blocs de programme
schedule_lists = soup.select("ol.schedule-list")

print(f"Nombre de blocs trouvés : {len(schedule_lists)}")
print()

for schedule in schedule_lists:

    print("=" * 80)
    print(schedule.get_text(" ", strip=True)[:3000])
    print()
