import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.formula1.com/en/latest/article/formula-1-heineken-dutch-grand-prix-2026.VYghWPhEDqYBlWbd1iKe6"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

print("=" * 100)
print("🏎️ DIAGNOSTIC FORMULA1.COM")
print("=" * 100)

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

response.raise_for_status()

html = response.text

print("STATUS :", response.status_code)
print("TYPE   :", response.headers.get("content-type"))
print("TAILLE :", len(html), "caractères")

soup = BeautifulSoup(html, "html.parser")


# =========================================================
# 1. TITRE
# =========================================================

print()
print("=" * 100)
print("📄 TITRE")
print("=" * 100)

print(soup.title.get_text(strip=True) if soup.title else "Aucun titre")


# =========================================================
# 2. RECHERCHE DES SESSIONS DANS LE HTML
# =========================================================

print()
print("=" * 100)
print("🔎 RECHERCHE DES SESSIONS F1")
print("=" * 100)

sessions = [
    "FIRST PRACTICE SESSION",
    "SECOND PRACTICE SESSION",
    "THIRD PRACTICE SESSION",
    "SPRINT QUALIFYING",
    "SPRINT",
    "QUALIFYING SESSION",
    "GRAND PRIX",
]

for session in sessions:

    positions = [
        m.start()
        for m in re.finditer(
            re.escape(session),
            html,
            re.IGNORECASE
        )
    ]

    print()
    print(f"{session:<30} : {len(positions)} occurrence(s)")

    for position in positions[:3]:

        debut = max(0, position - 300)
        fin = min(len(html), position + 700)

        print("-" * 100)
        print(
            html[debut:fin]
            .replace("\\u003c", "<")
            .replace("\\u003e", ">")
        )


# =========================================================
# 3. RECHERCHE DES HEURES
# =========================================================

print()
print("=" * 100)
print("⏰ HEURES DÉTECTÉES")
print("=" * 100)

patterns = [
    r"\b\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\b",
    r"\b\d{1,2}:\d{2}\b",
]

heures = set()

for pattern in patterns:

    for match in re.findall(
        pattern,
        html
    ):
        heures.add(match)

for heure in sorted(
    heures,
    key=lambda x: (
        int(re.search(r"\d+", x).group()),
        int(re.search(r":(\d+)", x).group(1))
    )
):

    print(heure)


# =========================================================
# 4. DONNÉES JSON / NEXT.JS
# =========================================================

print()
print("=" * 100)
print("🧩 STRUCTURES DE DONNÉES")
print("=" * 100)

for script in soup.find_all("script"):

    contenu = script.string or script.get_text()

    if not contenu:
        continue

    contenu_test = contenu.lower()

    mots = [
        "first practice session",
        "sprint qualifying",
        "qualifying session",
        "grand prix",
        "schedule",
        "timetable",
    ]

    if any(mot in contenu_test for mot in mots):

        print()
        print("-" * 100)
        print("SCRIPT TROUVÉ")
        print("type :", script.get("type"))
        print("id   :", script.get("id"))
        print("taille :", len(contenu))
        print("-" * 100)

        print(contenu[:15000])


# =========================================================
# 5. LIENS CALENDRIER
# =========================================================

print()
print("=" * 100)
print("📅 LIENS CALENDRIER")
print("=" * 100)

for link in soup.find_all("a", href=True):

    href = link["href"]

    texte = link.get_text(
        " ",
        strip=True
    )

    test = (
        href.lower()
        + " "
        + texte.lower()
    )

    if any(
        mot in test
        for mot in [
            "calendar",
            "schedule",
            "timetable",
            "download",
            "sync",
            "ics",
            "ical"
        ]
    ):

        print()
        print("TEXTE :", texte[:300])
        print("HREF  :", href)


print()
print("=" * 100)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 100)
