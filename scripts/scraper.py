import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin

BASE_URL = "https://natatry.pl"
SZLAKI_URL = "https://natatry.pl/szlaki"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def get_article_links(base_url):
    response = requests.get(SZLAKI_URL, headers=HEADERS)
    response.encoding = 'utf-8'
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(SZLAKI_URL, href)
        if full_url.startswith(BASE_URL) and full_url.count('/') > 4: 
            links.add(full_url)
            
    return list(links)

def parse_article(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else url.split('/')[-1].replace('-', ' ').title()
        
        article = soup.find('main') or soup.find('article') or soup.find('div', id='content')
        if not article:
            article = soup
            
        tables_content = []
        tables = article.find_all('table')
        if not tables:
            tables = soup.find_all('table')
            
        for table in tables:
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
                if len(cells) >= 2 and cells[0] and cells[1]:
                    tables_content.append(f"{cells[0]}: {cells[1]}")
                    
        tables_text = "\n".join(tables_content)
        
        paragraphs = article.find_all('p')
            
        text_content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                text_content.append(text)
                
        full_text = " ".join(text_content)
        if tables_text:
            full_text = f"DANE TECHNICZNE SZLAKU:\n{tables_text}\n\nOPIS SZLAKU:\n{full_text}"
        
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
    print(f"Fetching links from {SZLAKI_URL}...")
    links = get_article_links(SZLAKI_URL)
    print(f"Found {len(links)} potential trails.")
    
    links = list(links)[:200]
    
    data_dir = os.path.join(os.path.dirname(__file__), '../data/natatry.pl')
    os.makedirs(data_dir, exist_ok=True)
    
    from tqdm import tqdm
    print("Starting article scraping and parsing...")
    saved_count = 0
    for url in tqdm(links, desc="Downloading"):
        article_data = parse_article(url)
        if article_data:
            file_path = os.path.join(data_dir, f"{article_data['id']}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            saved_count += 1
                
        time.sleep(0.5)
        
    print(f"\nDone! Saved {saved_count} complete trails to {data_dir}.")

if __name__ == "__main__":
    main()
