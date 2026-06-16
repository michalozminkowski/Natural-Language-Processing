import json
import os
import sys
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from config import EMBEDDING_MODEL


def build_embedding_text(data):
    return f"""
Nazwa: {data.get("name")}
Region: {data.get("region")}
Typ trasy: {data.get("trail_type")}
Rodzaj trasy: {data.get("route_type")}

Czas przejścia: {data.get("duration_hours")} godzin
Dystans: {data.get("distance_km")} km
Przewyższenie: {data.get("elevation_gain_m")} m

Trudność ogólna: {data.get("difficulty")}/5
Trudność techniczna: {data.get("technical_difficulty")}/5
Trudność kondycyjna: {data.get("fitness_difficulty")}/5
Ekspozycja: {data.get("exposure")}/5

Dla początkujących: {data.get("suitable_for_beginners")}
Dla dzieci: {data.get("suitable_for_children")}
Dla rodzin: {data.get("suitable_for_families")}
Na zimę: {data.get("suitable_for_winter")}

Wymagane doświadczenie: {data.get("requires_experience")}
Wymagany sprzęt: {", ".join(data.get("requires_equipment", []))}
Ryzyka: {", ".join(data.get("risks", []))}
Atrakcje: {", ".join(data.get("main_attractions", []))}
Rekomendowany sezon: {", ".join(data.get("recommended_season", []))}

Punkt startowy: {data.get("start_point")}
Punkt końcowy: {data.get("end_point")}

Krótki opis: {data.get("short_summary")}
Pełny opis: {data.get("description")}
"""


def main():
    data_dir = os.path.join(PROJECT_ROOT, "data")
    processed_dir = os.path.join(data_dir, "processed")

    output_embeddings_path = os.path.join(data_dir, "embeddings.npy")
    output_mapping_path = os.path.join(data_dir, "index_mapping.json")

    if not os.path.exists(processed_dir):
        print("ERROR: data/processed does not exist.")
        print("Run: python scripts/extract_metadata.py")
        return

    print("Searching for processed JSON files...")

    all_json_files = []

    for file in os.listdir(processed_dir):
        if file.endswith(".json"):
            all_json_files.append(os.path.join(processed_dir, file))

    if not all_json_files:
        print("No processed trail JSON files found!")
        return

    print(f"Found {len(all_json_files)} processed trails. Building embedding texts...")

    texts_to_embed = []
    paths_mapping = []

    for file_path in all_json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "name" in data and "description" in data:
                text = build_embedding_text(data)
                texts_to_embed.append(text)

                rel_path = os.path.relpath(file_path, data_dir)
                paths_mapping.append(rel_path)

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    if not texts_to_embed:
        print("No valid processed trails found!")
        return

    print(f"Generating embeddings using: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(
        texts_to_embed,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    print("Saving embeddings and index mapping...")

    np.save(output_embeddings_path, embeddings)

    with open(output_mapping_path, "w", encoding="utf-8") as f:
        json.dump(paths_mapping, f, ensure_ascii=False, indent=2)

    print(f"Done! Generated embeddings for {len(texts_to_embed)} processed trails.")
    print(f"Saved: {output_embeddings_path}")
    print(f"Saved: {output_mapping_path}")


if __name__ == "__main__":
    main()