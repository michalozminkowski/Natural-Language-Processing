def text_contains_any(text, keywords):
    if not text:
        return False

    text_lower = text.lower()

    return any(keyword.lower() in text_lower for keyword in keywords)


def normalize_user_profile(user):
    if not isinstance(user, dict):
        return {}

    normalized = {}

    for key, value in user.items():
        if isinstance(value, str):
            normalized[key] = value.lower()
        else:
            normalized[key] = value

    return normalized


def extract_duration_limit_hours(user):
    value = user.get("czas_lub_dystans")

    if not value:
        return None

    value = str(value).lower().replace(",", ".")

    import re
    match = re.search(r"(\d+(?:\.\d+)?)", value)

    if not match:
        return None

    return float(match.group(1))


def desired_difficulty_to_number(user):
    value = user.get("poziom_trudnosci")

    if not value:
        return None

    value = str(value).lower()

    if "bardzo łat" in value or "bardzo lat" in value:
        return 1
    if "łat" in value or "lat" in value:
        return 2
    if "śred" in value or "sred" in value:
        return 3
    if "trud" in value:
        return 4

    return None
def extract_duration_from_trail_text(text):
    if not text:
        return None

    import re

    text_lower = text.lower()

    match = re.search(
        r"czas przejścia[:\s]*(\d+)\s*h\s*(\d+)?",
        text_lower
    )

    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2)) if match.group(2) else 0
        return hours + minutes / 60

    match = re.search(r"(\d+)\s*h\s*(\d+)", text_lower)

    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours + minutes / 60

    match = re.search(r"(\d+)\s*h", text_lower)

    if match:
        return float(match.group(1))

    return None

def format_duration(hours):
    if hours is None:
        return "brak danych"

    try:
        total_minutes = int(round(float(hours) * 60))
    except (TypeError, ValueError):
        return str(hours)

    h = total_minutes // 60
    m = total_minutes % 60

    if h > 0 and m > 0:
        return f"{h} h {m} min"
    if h > 0:
        return f"{h} h"
    return f"{m} min"

def score_trail(user_profile, trail):
    if not isinstance(trail, dict):
        return {
            "trail": {},
            "score": -9999,
            "reasons": [],
            "warnings": ["DYSKWALIFIKACJA: uszkodzony albo pusty rekord trasy"],
            "disqualified": True
        }
    user = normalize_user_profile(user_profile)

    score = 0
    reasons = []
    warnings = []

    name = trail.get("name") or trail.get("nazwa") or "Nieznany szlak"
    description = trail.get("description") or trail.get("opis") or ""
    risks = trail.get("risks") or []
    risks_text = " ".join(risks) if isinstance(risks, list) else str(risks)

    full_text = f"{name} {description} {risks_text}"

    max_duration = extract_duration_limit_hours(user)

    duration = trail.get("duration_hours")
    duration_from_text = extract_duration_from_trail_text(full_text)

    if duration_from_text is not None:
        duration = duration_from_text

    if max_duration and duration:
        try:
            duration = float(duration)

            if duration <= max_duration:
                score += 25
                reasons.append(f"mieści się w limicie czasu: około {format_duration(duration)}")
            elif duration <= max_duration + 0.5:
                score -= 10
                warnings.append(f"lekko przekracza limit czasu: około {format_duration(duration)}")
            else:
                score -= 40
                warnings.append(f"przekracza limit czasu: około {format_duration(duration)}")
        except (TypeError, ValueError):
            pass

    desired_difficulty = desired_difficulty_to_number(user)
    difficulty = trail.get("difficulty")

    if desired_difficulty and difficulty:
        try:
            difficulty = int(difficulty)

            if desired_difficulty == 1:
                if difficulty == 1:
                    score += 30
                    reasons.append("trasa jest bardzo łatwa, zgodnie z preferencją")
                elif difficulty == 2:
                    score -= 10
                    warnings.append("trasa może być trochę trudniejsza niż oczekiwano")
                else:
                    score -= 60
                    warnings.append(f"trudność {difficulty}/5 jest za wysoka")

            elif desired_difficulty == 2:
                if difficulty in [1, 2]:
                    score += 30
                    reasons.append(f"trudność {difficulty}/5 pasuje do łatwej trasy")
                elif difficulty == 3:
                    score -= 15
                    warnings.append("trasa może być trochę trudniejsza niż łatwa")
                else:
                    score -= 60
                    warnings.append(f"trudność {difficulty}/5 jest za wysoka")

            elif desired_difficulty == 3:
                if difficulty == 3:
                    score += 30
                    reasons.append("trasa ma średnią trudność, zgodnie z preferencją")
                elif difficulty == 2:
                    score += 5
                    warnings.append("trasa może być trochę łatwiejsza niż oczekiwano")
                elif difficulty == 4:
                    score -= 20
                    warnings.append("trasa może być trudniejsza niż oczekiwano")
                else:
                    score -= 40
                    warnings.append(f"trudność {difficulty}/5 słabo pasuje do preferencji")

            elif desired_difficulty == 4:
                if difficulty in [4, 5]:
                    score += 35
                    reasons.append(f"trudność {difficulty}/5 pasuje do trudnej trasy")
                elif difficulty == 3:
                    score += 10
                    warnings.append("trasa jest raczej średnio-trudna, nie bardzo trudna")
                else:
                    score -= 50
                    warnings.append(f"trasa jest zbyt łatwa względem preferencji: {difficulty}/5")

        except (TypeError, ValueError):
            pass

    if "początkują" in str(user.get("doswiadczenie")) or "poczatkuj" in str(user.get("doswiadczenie")):
        if trail.get("suitable_for_beginners") is True:
            score += 25
            reasons.append("opis wskazuje, że trasa nadaje się dla początkujących")

        if trail.get("suitable_for_beginners") is False:
            score -= 60
            warnings.append("trasa nie wygląda na odpowiednią dla początkujących")

        if trail.get("difficulty") and int(trail.get("difficulty")) >= 4:
            score -= 50
            warnings.append("trasa jest zbyt trudna dla początkującego")

    elevation_gain = trail.get("elevation_gain_m")

    if elevation_gain:
        try:
            elevation_gain = int(elevation_gain)

            if "śred" in str(user.get("kondycja")) or "sred" in str(user.get("kondycja")):
                if elevation_gain > 900:
                    score -= 45
                    warnings.append(f"bardzo duże przewyższenie jak na średnią kondycję: {elevation_gain} m")
                elif elevation_gain > 600:
                    score -= 20
                    warnings.append(f"dość duże przewyższenie: {elevation_gain} m")

            if "słab" in str(user.get("kondycja")) or "slab" in str(user.get("kondycja")):
                if elevation_gain > 500:
                    score -= 50
                    warnings.append(f"za duże przewyższenie dla słabej kondycji: {elevation_gain} m")
        except (TypeError, ValueError):
            pass

    user_avoids_exposure = (
        "unika" in str(user.get("ekspozycja"))
        or "bez" in str(user.get("ekspozycja"))
        or "przepa" in str(user.get("ekspozycja"))
    )

    exposure = trail.get("exposure")

    dangerous_keywords = [
        "łańcuch",
        "lancuch",
        "klamr",
        "ekspozycj",
        "przepa",
        "żleb",
        "zleb",
        "ubezpieczenia",
        "trudności techniczne",
        "trudnosci techniczne",
        "giewont"
    ]

    has_dangerous_fragments = text_contains_any(full_text, dangerous_keywords)

    disqualified = False

    if user_avoids_exposure:
        if exposure is not None:
            try:
                exposure = int(exposure)

                if exposure >= 2:
                    score -= 200
                    disqualified = True
                    warnings.append(
                        f"DYSKWALIFIKACJA: ekspozycja {exposure}/5 jest niezgodna z preferencją unikania przepaści"
                    )
                else:
                    score += 20
                    reasons.append("niska ekspozycja pasuje do preferencji")
            except (TypeError, ValueError):
                pass

        if has_dangerous_fragments:
            score -= 250
            disqualified = True
            warnings.append(
                "DYSKWALIFIKACJA: opis zawiera łańcuchy, żleb, ekspozycję albo ubezpieczenia"
            )

    if user.get("dzieci") is True:
        if trail.get("suitable_for_children") is True:
            score += 20
            reasons.append("trasa wygląda na odpowiednią dla dzieci")
        elif trail.get("suitable_for_children") is False:
            score -= 60
            warnings.append("trasa nie wygląda na odpowiednią dla dzieci")

    preferences = str(user.get("preferencje") or "").lower()
    attractions = trail.get("main_attractions") or []
    attractions_text = " ".join(attractions).lower() if isinstance(attractions, list) else str(attractions).lower()
    full_text_lower = full_text.lower()

    bad_view_keywords = [
        "miejsc widokowych jak na lekarstwo",
        "miejsca widokowe jak na lekarstwo",
        "brak widoków",
        "brak widokow",
        "mało widoków",
        "malo widokow",
        "niewiele widoków",
        "niewiele widokow",
        "trasa nudna",
        "nudna i długa",
        "nudna i dluga",
        "równie nudna",
        "rownie nudna",
        "długa i nudna",
        "dluga i nudna",
        "niestety równie nudna",
        "niestety rownie nudna",
        "miejsc widokowych",
        "jak na lekarstwo"
    ]

    good_view_keywords = [
        "piękna panorama",
        "piekna panorama",
        "piękne widoki",
        "piekne widoki",
        "ładne widoki",
        "ladne widoki",
        "widokowa",
        "widokowy",
        "widokowe",
        "panorama",
        "roztacza się",
        "roztacza sie",
        "widok na",
        "widoki na"
    ]
    if "szczyt" in preferences:
        peak_keywords = [
            "szczyt",
            "wierzchołek",
            "wierzch",
            "wierch",
            "kopieniec",
            "kasprowy",
            "giewont",
            "czerwone wierchy",
            "grześ",
            "nosal"
        ]

        non_peak_keywords = [
            "hala",
            "polana",
            "dolina",
            "staw",
            "morskie oko",
            "wodogrzmoty"
        ]

        if text_contains_any(full_text_lower, peak_keywords):
            score += 35
            reasons.append("trasa prowadzi na szczyt lub w rejon szczytowy")
        elif text_contains_any(full_text_lower, non_peak_keywords):
            score -= 45
            warnings.append("trasa nie wygląda jak typowa trasa na szczyt")
        else:
            score -= 20
            warnings.append("brak mocnej informacji, że trasa prowadzi na szczyt")

    if "widok" in preferences:
        if text_contains_any(full_text_lower, bad_view_keywords):
            score -= 120
            warnings.append(
                "NIE SPEŁNIA PREFERENCJI: opis sugeruje, że trasa nie jest szczególnie widokowa"
            )
        elif "widok" in attractions_text or text_contains_any(full_text_lower, good_view_keywords):
            score += 35
            reasons.append("trasa pasuje do preferencji widokowych")
        else:
            score -= 30
            warnings.append(
                "brak mocnych informacji, że trasa jest szczególnie widokowa"
            )
    return {
        "trail": trail,
        "score": score,
        "reasons": reasons,
        "warnings": warnings,
        "disqualified": disqualified
    }


def rank_trails(user_profile, trails):
    if not isinstance(trails, list):
        trails = []

    valid_trails = [
        trail for trail in trails
        if isinstance(trail, dict)
    ]

    scored = [score_trail(user_profile, trail) for trail in valid_trails]

    safe_trails = [
        item for item in scored
        if not item.get("disqualified", False)
    ]

    if safe_trails:
        return sorted(safe_trails, key=lambda item: item["score"], reverse=True)

    return sorted(scored, key=lambda item: item["score"], reverse=True)