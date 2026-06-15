import requests
from bs4 import BeautifulSoup
import json
import time
import os
import argparse
from urllib.parse import urljoin
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def get_natatry_links(base_url, szlaki_url):
    response = requests.get(szlaki_url, headers=HEADERS)
    response.encoding = 'utf-8'
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(szlaki_url, href)
        if full_url.startswith(base_url) and full_url.count('/') > 4: 
            links.add(full_url)
            
    return list(links)

def parse_natatry_article(url):
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
        print(f"Error parsing natatry {url}: {e}")
        return None

def scrape_natatry():
    BASE_URL = "https://natatry.pl"
    SZLAKI_URL = "https://natatry.pl/szlaki"
    print(f"Fetching links from {SZLAKI_URL}...")
    links = get_natatry_links(BASE_URL, SZLAKI_URL)
    print(f"Found {len(links)} potential trails on natatry.pl.")
    
    links = list(links)[:200]
    
    data_dir = os.path.join(os.path.dirname(__file__), '../data/natatry.pl')
    os.makedirs(data_dir, exist_ok=True)
    
    saved_count = 0
    for url in tqdm(links, desc="Downloading natatry.pl"):
        article_data = parse_natatry_article(url)
        if article_data:
            file_path = os.path.join(data_dir, f"{article_data['id']}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            saved_count += 1
                
        time.sleep(0.5)
        
    print(f"\nDone! Saved {saved_count} complete trails.")

def get_tatromaniak_links(base_url, szlaki_url):
    response = requests.get(szlaki_url, headers=HEADERS)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    categories = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(base_url, href)
        if full_url.startswith(szlaki_url) and full_url != szlaki_url:
            categories.add(full_url)
            
    articles = set()
    for cat_url in categories:
        try:
            resp = requests.get(cat_url, headers=HEADERS)
            resp.encoding = 'utf-8'
            cat_soup = BeautifulSoup(resp.text, 'html.parser')
            for a in cat_soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                if full_url.startswith(szlaki_url) and full_url not in categories and full_url != szlaki_url:
                    articles.add(full_url)
        except Exception as e:
            print(f"Error fetching tatromaniak category {cat_url}: {e}")
            
    return list(articles)

def parse_tatromaniak_article(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else url.strip('/').split('/')[-1].replace('-', ' ').title()
        
        tables_content = []
        tables = soup.find_all('table')
        for table in tables:
            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 3:
                    czas_div = tds[1].find('div', class_='table-content')
                    czas = czas_div.get_text(strip=True) if czas_div else tds[1].get_text(strip=True)
                    
                    trudnosc_div = tds[2].find('div', class_='rating')
                    stars = 0
                    if trudnosc_div:
                        stars = len(trudnosc_div.find_all('i', class_='fas fa-star'))
                        
                    tables_content.append(f"Czas przejścia: {czas}")
                    if stars > 0:
                        tables_content.append(f"Trudność: {stars}/5")
                        
        tables_text = "\n".join(tables_content)

        paragraphs = soup.find_all('p')
        text_content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                text_content.append(text)
                
        full_text = " ".join(text_content)
        
        if not full_text:
            return None
            
        if tables_text:
            full_text = f"DANE TECHNICZNE SZLAKU:\n{tables_text}\n\nOPIS SZLAKU:\n{full_text}"
            
        return {
            "id": url.strip('/').split('/')[-1],
            "url": url,
            "nazwa": title,
            "pasmo_gorskie": "Tatry",
            "opis": full_text
        }
    except Exception as e:
        print(f"Error parsing tatromaniak {url}: {e}")
        return None

def scrape_tatromaniak():
    BASE_URL = "https://tatromaniak.pl"
    SZLAKI_URL = "https://tatromaniak.pl/szlaki/"
    print(f"Fetching links from {SZLAKI_URL}...")
    links = get_tatromaniak_links(BASE_URL, SZLAKI_URL)
    print(f"Found {len(links)} potential trails on tatromaniak.pl.")
    
    links = list(links)[:200]
    
    data_dir = os.path.join(os.path.dirname(__file__), '../data/tatromaniak.pl')
    os.makedirs(data_dir, exist_ok=True)
    
    saved_count = 0
    for url in tqdm(links, desc="Downloading tatromaniak.pl"):
        article_data = parse_tatromaniak_article(url)
        if article_data:
            file_path = os.path.join(data_dir, f"{article_data['id']}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            saved_count += 1
                
        time.sleep(0.5)
        
    print(f"\nDone! Saved {saved_count} complete trails.")

def get_tatryinfo_links(base_url, sitemap_url):
    response = requests.get(sitemap_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/'):
            href = urljoin(base_url, href)
            
        if ('/wysokie/' in href or '/zachodnie/' in href or '/slowackie/' in href) \
           and href.endswith('.php') and 'szlaki.php' not in href:
            links.add(href)
            
    return list(links)

def parse_tatryinfo_article(url):
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag = soup.find('h1') or soup.find('title')
        title = title_tag.get_text(strip=True).split('::')[-1].strip() if title_tag else url.split('/')[-1]
        
        specs = []
        for div in soup.find_all('div', class_='description_position'):
            left = div.find('p', class_='left')
            right = div.find('p', class_='right')
            if left and right:
                label = left.get_text(strip=True)
                value = right.get_text(strip=True)
                
                stars_all = right.find_all('img', src=lambda s: s and ('gwiazdka' in s or 'star' in s))
                if stars_all:
                    filled_stars = len([img for img in stars_all if 'gwiazdka1' in img.get('src', '')])
                    value = f"{filled_stars}/5"
                    
                specs.append(f"{label}: {value}")
                
        tables_text = "\n".join(specs)
        
        paragraphs = soup.find_all('p')
        text_content = []
        for p in paragraphs:
            if p.find_parent('div', class_='description_position') or p.find_parent('div', class_='navi') or p.find_parent('div', class_='submenu'):
                continue
            
            text = p.get_text(strip=True)
            if len(text) > 50 and "Copyright" not in text and "cookieKorzystanie" not in text and "Internetowy przewodnik po Tatrach" not in text:
                text_content.append(text)
                
        full_text = "\n".join(text_content)
        
        if not full_text:
            return None
            
        if tables_text:
            full_text = f"DANE TECHNICZNE SZLAKU:\n{tables_text}\n\nOPIS SZLAKU:\n{full_text}"
            
        return {
            "id": url.split('/')[-1].replace('.php', ''),
            "url": url,
            "nazwa": title,
            "pasmo_gorskie": "Tatry",
            "opis": full_text
        }
    except Exception as e:
        print(f"Error parsing tatryinfo {url}: {e}")
        return None

def scrape_tatryinfo():
    BASE_URL = "https://www.tatry.info.pl"
    SITEMAP_URL = "https://www.tatry.info.pl/inne/mapa_serwisu.php"
    print(f"Fetching links from {SITEMAP_URL}...")
    links = get_tatryinfo_links(BASE_URL, SITEMAP_URL)
    print(f"Found {len(links)} potential trails on tatry.info.pl.")
    
    links = list(links)[:200]
    
    data_dir = os.path.join(os.path.dirname(__file__), '../data/tatry.info.pl')
    os.makedirs(data_dir, exist_ok=True)
    
    print("Starting tatry.info.pl article scraping and parsing...")
    saved_count = 0
    for url in tqdm(links, desc="Downloading tatry.info.pl"):
        article_data = parse_tatryinfo_article(url)
        if article_data:
            file_path = os.path.join(data_dir, f"{article_data['id']}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            saved_count += 1
                
        time.sleep(0.5)
        
    print(f"\nDone! Saved {saved_count} complete trails.")

def main():
    parser = argparse.ArgumentParser(description="Pobieranie szlaków z różnych stron.")
    parser.add_argument('--site', type=str, choices=['natatry', 'tatromaniak', 'tatryinfo', 'all'], default='all',
                        help='Wybierz stronę do zescrapowania (domyślnie: all)')
    
    args = parser.parse_args()
    
    if args.site == 'natatry' or args.site == 'all':
        scrape_natatry()
    if args.site == 'tatromaniak' or args.site == 'all':
        scrape_tatromaniak()
    if args.site == 'tatryinfo' or args.site == 'all':
        scrape_tatryinfo()

if __name__ == "__main__":
    main()
