import requests
from bs4 import BeautifulSoup

URL = "https://tv-sports.fr/base-ball/mlb_tv/"

print("🔎 Inspection de la page MLB TV-Sports")
print("=" * 60)

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# On cherche tous les éléments contenant une chaîne beIN
elements = soup.find_all(string=lambda s: s and "beIN SPORTS" in s)

print(f"Nombre d'éléments beIN trouvés : {len(elements)}")
print()

for i, element in enumerate(elements[:10], 1):
    parent = element.parent

    print(f"--- ÉLÉMENT {i} ---")
    print(parent.get_text(" ", strip=True))
    print()
    print("HTML du parent :")
    print(parent.prettify()[:3000])
    print()
