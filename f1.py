import requests

BASE = "https://tv-sports.fr"

URLS = [
    "https://tv-sports.fr/rss/competition/1434/grand-prix-des-pays-bas?direct=1",
    "https://tv-sports.fr/calendrier/competition/1434/grand-prix-des-pays-bas?direct=1",
]

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

for url in URLS:

    print()
    print("=" * 100)
    print("URL")
    print("=" * 100)
    print(url)

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    print("STATUS :", response.status_code)
    print("TYPE   :", response.headers.get("content-type"))
    print("TAILLE :", len(response.text))

    print()
    print("=" * 100)
    print("CONTENU")
    print("=" * 100)

    print(response.text[:30000])

print()
print("=" * 100)
print("FIN")
print("=" * 100)
