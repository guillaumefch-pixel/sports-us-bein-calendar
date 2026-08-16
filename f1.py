import requests

URL = "https://tv-sports.fr/calendrier/competition/1434/grand-prix-des-pays-bas?direct=1"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

print("=" * 100)
print("📅 TEST DU CALENDRIER ICS")
print("=" * 100)

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

print("STATUS :", response.status_code)
print("TYPE   :", response.headers.get("content-type"))
print("TAILLE :", len(response.content), "octets")

print()
print("=" * 100)
print("CONTENU")
print("=" * 100)

print(response.text[:30000])

print()
print("=" * 100)
print("RECHERCHE DES ÉVÉNEMENTS")
print("=" * 100)

for ligne in response.text.splitlines():

    if any(
        mot in ligne.lower()
        for mot in [
            "begin:VEVENT".lower(),
            "summary",
            "dtstart",
            "dtend",
            "description",
            "location"
        ]
    ):
        print(ligne)

print()
print("=" * 100)
print("FIN")
print("=" * 100)
