import requests
from bs4 import BeautifulSoup

URL = "https://tv-sports.fr/base-ball/mlb_tv/"

print("🔎 Recherche des matchs MLB diffusés sur beIN SPORTS...")
print()

response = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

text = soup.get_text(" ", strip=True)

print("Page récupérée avec succès.")
print()
print("Contient 'beIN' :", "beIN" in text)
print("Contient 'MLB' :", "MLB" in text)
print()
print("Premiers éléments trouvés contenant 'beIN' :")

for element in soup.find_all(string=lambda s: s and "beIN" in s):
    print("-", element.strip())
