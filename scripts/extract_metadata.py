import os
import sys
import json
import re
import requests
from tqdm import tqdm
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from config import OLLAMA_METADATA_MODEL, OLLAMA_URL
from schemas import TrailMetadata




DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_float(patterns, text):
    text = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1).replace(",", "."))
            except ValueError:
                return None

    return None


def regex_extract(text):
    duration_hours = extract_float([
        r"czas przejścia[:\s]+(\d+(?:[,.]\d+)?)",
        r"czas[:\s]+(\d+(?:[,.]\d+)?)\s*(?:h|godz|godzin)",
        r"(\d+(?:[,.]\d+)?)\s*(?:h|godz|godzin)"
    ], text)

    distance_km = extract_float([
        r"długość[:\s]+(\d+(?:[,.]\d+)?)\s*km",
        r"dystans[:\s]+(\d+(?:[,.]\d+)?)\s*km",
        r"trasa[:\s]+(\d+(?:[,.]\d+)?)\s*km",
        r"(\d+(?:[,.]\d+)?)\s*km"
    ], text)

    elevation_gain_m = extract_float([
        r"przewyższenie[:\s]+(\d+)\s*m",
        r"suma podejść[:\s]+(\d+)\s*m",
        r"podejścia[:\s]+(\d+)\s*m"
    ], text)

    return {
        "duration_hours": duration_hours,
        "distance_km": distance_km,
        "elevation_gain_m": int(elevation_gain_m) if elevation_gain_m is not None else None
    }


def llm_extract(article):
    description = article.get("opis", "")

    prompt = f"""
Jesteś systemem ekstrakcji informacji z artykułów o szlakach górskich.
Na podstawie artykułu zwróć WYŁĄCZNIE poprawny JSON.
Nie używaj markdown.
Nie dodawaj komentarzy.
Nie zgaduj. Jeśli informacji nie ma w tekście, wpisz null albo pustą listę.

Skala difficulty:
1 = bardzo łatwa
2 = łatwa
3 = średnia
4 = trudna
5 = bardzo trudna

Skala technical_difficulty:
1 = brak trudności technicznych
2 = łatwe technicznie
3 = umiarkowane trudności
4 = trudne technicznie
5 = bardzo trudne technicznie

Skala fitness_difficulty:
1 = bardzo mały wysiłek
2 = mały wysiłek
3 = średni wysiłek
4 = duży wysiłek
5 = bardzo duży wysiłek

Skala exposure:
0 = brak ekspozycji
1 = mała ekspozycja
2 = umiarkowana ekspozycja
3 = duża ekspozycja
4 = bardzo duża ekspozycja
5 = ekstremalna ekspozycja

Zwróć JSON dokładnie z tymi polami:
{{
  "region": null,
  "difficulty": null,
  "technical_difficulty": null,
  "fitness_difficulty": null,
  "exposure": null,
  "trail_type": null,
  "route_type": null,
  "suitable_for_beginners": null,
  "suitable_for_children": null,
  "suitable_for_families": null,
  "suitable_for_winter": null,
  "requires_experience": null,
  "requires_equipment": [],
  "risks": [],
  "main_attractions": [],
  "recommended_season": [],
  "start_point": null,
  "end_point": null,
  "short_summary": null
}}

ARTYKUŁ:
Nazwa: {article.get("nazwa")}
URL: {article.get("url")}

Opis:
{description[:5000]}
"""

    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_METADATA_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0
        }
    })

    response.raise_for_status()

    content = response.json()["message"]["content"]
    return json.loads(content)


def collect_raw_article_files():
    raw_files = []

    ignored_files = {
        "index_mapping.json",
        "processed_trails.json",
        "dataset_trails.json"
    }

    for root, _, files in os.walk(DATA_DIR):
        if "processed" in root:
            continue

        for file in files:
            if not file.endswith(".json"):
                continue

            if file in ignored_files:
                continue

            raw_files.append(os.path.join(root, file))

    return raw_files


def safe_filename(value):
    value = value.replace("/", "_")
    value = value.replace("\\", "_")
    value = value.replace(":", "_")
    return value
def clean_llm_data(data):
    list_fields = [
        "requires_equipment",
        "risks",
        "main_attractions",
        "recommended_season"
    ]

    int_fields = [
        "difficulty",
        "technical_difficulty",
        "fitness_difficulty",
        "exposure"
    ]

    bool_fields = [
        "suitable_for_beginners",
        "suitable_for_children",
        "suitable_for_families",
        "suitable_for_winter",
        "requires_experience"
    ]

    string_fields = [
        "region",
        "trail_type",
        "route_type",
        "start_point",
        "end_point",
        "short_summary"
    ]

    # Listy: null -> [], [null] -> [], "tekst" -> ["tekst"]
    for field in list_fields:
        value = data.get(field)

        if value is None:
            data[field] = []
        elif isinstance(value, list):
            data[field] = [
                str(item) for item in value
                if item is not None and str(item).strip() != ""
            ]
        else:
            data[field] = [str(value)]

    # Liczby: string/int/float -> int, błędne -> None
    for field in int_fields:
        value = data.get(field)

        if value is None:
            continue

        try:
            parsed = int(value)

            if field == "exposure":
                if 0 <= parsed <= 5:
                    data[field] = parsed
                else:
                    data[field] = None
            else:
                if 1 <= parsed <= 5:
                    data[field] = parsed
                else:
                    data[field] = None

        except (ValueError, TypeError):
            data[field] = None

    # Boole: "tak"/"nie" -> True/False
    for field in bool_fields:
        value = data.get(field)

        if isinstance(value, bool) or value is None:
            continue

        if isinstance(value, str):
            lower = value.lower().strip()

            if lower in ["true", "tak", "yes", "1"]:
                data[field] = True
            elif lower in ["false", "nie", "no", "0"]:
                data[field] = False
            else:
                data[field] = None
        else:
            data[field] = None

    # Pola tekstowe: dict/list -> sensowny tekst
    for field in string_fields:
        value = data.get(field)

        if value is None:
            data[field] = None

        elif isinstance(value, str):
            cleaned = value.strip()
            data[field] = cleaned if cleaned else None

        elif isinstance(value, dict):
            # Jeśli LLM zwróci {"name": "...", "description": "..."}
            if value.get("name"):
                data[field] = str(value["name"])
            elif value.get("title"):
                data[field] = str(value["title"])
            else:
                data[field] = json.dumps(value, ensure_ascii=False)

        elif isinstance(value, list):
            cleaned_items = [
                str(item) for item in value
                if item is not None and str(item).strip() != ""
            ]
            data[field] = ", ".join(cleaned_items) if cleaned_items else None

        else:
            data[field] = str(value)

    return data

def main():
    raw_files = collect_raw_article_files()
    print(f"Found {len(raw_files)} raw articles.")

    for path in tqdm(raw_files, desc="Extracting metadata"):
        with open(path, "r", encoding="utf-8") as f:
            article = json.load(f)

        text = article.get("opis", "")
        regex_data = regex_extract(text)

        try:
            llm_data = llm_extract(article)
        except Exception as e:
            print(f"\nLLM extraction failed for {path}: {e}")
            llm_data = {}

        merged = {
            "id": article.get("id"),
            "name": article.get("nazwa"),
            "source_url": article.get("url"),
            "description": text,
            **llm_data
        }

        merged = clean_llm_data(merged)

        for key, value in regex_data.items():
            if value is not None:
                merged[key] = value

        try:
            validated = TrailMetadata(**merged)
        except Exception as e:
            print(f"\nValidation failed for {path}: {e}")
            continue

        output_name = safe_filename(validated.id) + ".json"
        output_path = os.path.join(OUTPUT_DIR, output_name)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(validated.model_dump(), f, ensure_ascii=False, indent=2)

    print("\nDone. Processed files saved in data/processed/")


if __name__ == "__main__":
    main()