import requests
from bs4 import BeautifulSoup

URL = "https://tv-sports.fr/base-ball/mlb_tv/"

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

# On prend la 2e diffusion :
# Houston Astros – Seattle Mariners
channel = channels[1]

print("=" * 80)
print("DIFFUSION TEST")
print("=" * 80)
print(channel.get_text(" ", strip=True))

print("\n" + "=" * 80)
print("PARENTS")
print("=" * 80)

element = channel

for niveau in range(1, 10):
    element = element.parent

    print(f"\n--- PARENT {niveau} ---")
    print("TAG :", element.name)
    print("CLASS :", element.get("class"))
    print("ID :", element.get("id"))
    print("TEXTE :")
    print(element.get_text(" ", strip=True)[:1000])
