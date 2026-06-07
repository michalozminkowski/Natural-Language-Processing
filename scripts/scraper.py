import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re

BASE_URL = "https://pieknotatr.pl/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_article_links(base_url):
    response = requests.get(base_url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Filter valid article links
        if href.startswith(base_url) and href != base_url:
            # Exclude unwanted paths or fragments
            if any(x in href for x in ['/author/', '/category/', '/tag/', '#', '/page/']):
                continue
            links.add(href)
            
    return list(links)

def parse_article(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Title usually in h1
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else url.split('/')[-1].replace('-', ' ').title()
        
        # We can collect text from paragraphs.
        # Often articles are in an <article> tag or a div with class like 'entry-content'
        content_div = soup.find('div', class_='entry-content') or soup.find('article')
        
        if content_div:
            paragraphs = content_div.find_all('p')
        else:
            paragraphs = soup.find_all('p')
            
        text_content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                text_content.append(text)
                
        full_text = " ".join(text_content)
        
        return {
            "id": url.split('/')[-1] or url.split('/')[-2],
            "url": url,
            "nazwa": title,
            "pasmo_gorskie": "Tatry",
            "opis": full_text
        }
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

def main():
    print("Pobieranie linków...")
    links = get_article_links(BASE_URL)
    print(f"Znaleziono {len(links)} potencjalnych artykułów.")
    
    data = []
    
    from tqdm import tqdm
    print("Rozpoczęto pobieranie i parsowanie artykułów...")
    for url in tqdm(links, desc="Pobieranie"):
        article_data = parse_article(url)
        if article_data and len(article_data['opis']) > 100:  # Skip very short or empty
            data.append(article_data)
        time.sleep(1)
        
    os.makedirs('../data', exist_ok=True)
    with open('../data/dataset_trails.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"\nZakończono. Zapisano pomyślnie {len(data)} artykułów do data/dataset_trails.json")

if __name__ == "__main__":
    main()
