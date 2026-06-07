import requests
from bs4 import BeautifulSoup

url = "https://pieknotatr.pl/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Let's find all links and see what the article links look like
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('https://pieknotatr.pl/') and href != 'https://pieknotatr.pl/':
            links.add(href)
            
    print(f"Found {len(links)} unique links on pieknotatr.pl.")
    print("Sample links:")
    for l in list(links)[:15]:
        print(l)
else:
    print("Error:", response.status_code)
