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
        if href.startswith(base_url) and href != base_url:
            if any(x in href for x in ['/author/', '/category/', '/tag/', '#', '/page/']):
                continue
            links.add(href)
            
    return list(links)

def parse_article(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else url.split('/')[-1].replace('-', ' ').title()
        
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
            "name": title,
            "mountain_range": "Tatry",
            "description": full_text
        }
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

def main():
    print("Fetching links...")
    links = get_article_links(BASE_URL)
    print(f"Found {len(links)} potential articles.")
    
    os.makedirs('../data/articles', exist_ok=True)
    data = []
    
    from tqdm import tqdm
    print("Starting article parsing...")
    for url in tqdm(links, desc="Downloading"):
        article_data = parse_article(url)
        if article_data and len(article_data['description']) > 100:
            data.append(article_data)
            
            file_path = f"../data/articles/{article_data['id']}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
                
        time.sleep(1)
        
    with open('../data/dataset_trails.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"\nFinished. Successfully saved {len(data)} articles to data/articles/")

if __name__ == "__main__":
    main()
