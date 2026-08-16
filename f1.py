import requests
import json

URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/2026.json"

print("=" * 80)
print("🏎️ TEST SOURCE F1 — SPORTSTIMES")
print("=" * 80)

response = requests.get(URL, timeout=20)

print("STATUS :", response.status_code)
print("TYPE   :", response.headers.get("content-type"))
print("TAILLE :", len(response.content), "octets")

response.raise_for_status()

data = response.json()

print()
print("TYPE JSON :", type(data).__name__)

print()
print("=" * 80)
print("STRUCTURE")
print("=" * 80)

if isinstance(data, dict):
    print("CLÉS :", list(data.keys()))

print()
print("=" * 80)
print("🇳🇱 GRAND PRIX DES PAYS-BAS")
print("=" * 80)

courses = data.get("races", [])

print("Nombre de courses :", len(courses))

for course in courses:

    if (
        course.get("name", "").lower() in ["dutch", "netherlands"]
        or
        course.get("location", "").lower() == "zandvoort"
    ):

        print(
            json.dumps(
                course,
                indent=2,
                ensure_ascii=False
            )
        )

        break

else:
    print("❌ Grand Prix des Pays-Bas introuvable")

print()
print("=" * 80)
print("✅ FIN DU TEST")
print("=" * 80)
