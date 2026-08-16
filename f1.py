def construire_vevent(session, diffusion, dtstamp):
    course = session["course"]
    debut = session["horaire"]
    fin = debut + timedelta(minutes=session["duree_minutes"])

    resume = f"🏎️ F1 — {course['location']} — {session['nom']}"

    description = [
        f"Grand Prix : {course['name']} ({course['location']})"
    ]

    if diffusion:
        description.extend(
            (
                f"Diffusion : {diffusion['titre']}",
                diffusion["lien"],
            )
        )
    else:
        description.append("Diffusion TV : non trouvée")

    return [
        "BEGIN:VEVENT",
        f"UID:f1-{course['round']}-{session['cle']}@sports-us-bein-calendar",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{debut.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{fin.strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{echapper_ics(resume)}",
        f"DESCRIPTION:{echapper_ics(chr(10).join(description))}",
        f"LOCATION:{echapper_ics(course['location'])}",
        "END:VEVENT",
    ]
