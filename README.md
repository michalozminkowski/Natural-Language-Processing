# Semantic Mountain Trail Search Engine

This project aims to build an intelligent recommendation system for mountain trails using NLP embeddings.

## Data Collection (Phase 1)

The data for this project is scraped from the web (e.g., pieknotatr.pl) to build a corpus of text descriptions.

### Setup Environment

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### How to Download Data

To download the raw articles and save them as JSON files, run the scraper script. 
The script will crawl the target website, extract the text from articles, and save them in the `data/articles/` directory. It will also create an aggregated dataset `data/dataset_trails.json`.

```bash
cd scripts
python scraper.py
```

*Note: The `data/` directory is ignored in `.gitignore` by default to avoid uploading scraped datasets to the repository.*
