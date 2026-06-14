import json
import os
import glob
import numpy as np
from sentence_transformers import SentenceTransformer

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '../data')
    output_embeddings_path = os.path.join(data_dir, 'embeddings.npy')
    output_mapping_path = os.path.join(data_dir, 'index_mapping.json')

    print("Searching for JSON files in directories...")
    all_json_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.json') and file not in ['index_mapping.json', 'dataset_trails.json', 'processed_trails.json']:
                all_json_files.append(os.path.join(root, file))

    if not all_json_files:
        print("No JSON files with trails found!")
        return

    print(f"Found {len(all_json_files)} articles. Extracting data...")
    
    texts_to_embed = []
    paths_mapping = []

    for file_path in all_json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if 'nazwa' in data and 'opis' in data:
                    pasmo = data.get('pasmo_gorskie', 'Unknown')
                    text = f"Nazwa: {data['nazwa']}. Pasmo górskie: {pasmo}. Opis: {data['opis']}"
                    
                    texts_to_embed.append(text)
                    rel_path = os.path.relpath(file_path, data_dir)
                    paths_mapping.append(rel_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    print("Generating embeddings...")
    model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    model = SentenceTransformer(model_name)

    embeddings = model.encode(texts_to_embed, show_progress_bar=True, convert_to_numpy=True)
    
    print("Saving to disk...")
    np.save(output_embeddings_path, embeddings)
    
    with open(output_mapping_path, 'w', encoding='utf-8') as f:
        json.dump(paths_mapping, f, ensure_ascii=False, indent=2)
        
    print(f"Done! Generated embeddings for {len(texts_to_embed)} files.")

if __name__ == "__main__":
    main()
