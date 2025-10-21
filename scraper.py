import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import time

BASE_URL = "https://encheres-domaine.gouv.fr"
SEARCH_URL_BASE = "https://encheres-domaine.gouv.fr/hermes/biens-mobiliers/bijoux-mode-et-art-de-vivre"
KEYWORDS = ['montre', 'horlogerie', 'chronographe', 'rolex', 'omega', 'bracelet-montre', 'gousset']
TARGET_COUNT = 20
MAX_PAGES = 10

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_latest_watches():
    watches = []
    page = 0
    
    while len(watches) < TARGET_COUNT and page < MAX_PAGES:
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"\n🕵️  PAGE {page + 1}: {url}")
        
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"   ✅ Statut HTTP: {r.status_code}")
        
        soup = BeautifulSoup(r.content, 'lxml')
        
        # MULTIPLES SÉLECTEURS (au cas où)
        cards = (soup.find_all('div', class_='fr-card-product') or 
                 soup.find_all('article', class_='fr-card-product') or 
                 soup.find_all('div', {'class': lambda x: x and 'card-product' in x}))
        
        print(f"   📊 CARTES TROUVÉES: {len(cards)}")
        
        if len(cards) == 0:
            print("   ❌ AUCUNE CARTE ! Debug HTML:")
            print(soup.select_one('main')[:1000])  # Premier bout de HTML
            break
        
        # DEBUG: Affiche les 5 PREMIERS TITRES
        titles = []
        for card in cards[:5]:
            title_elem = (card.select_one('h3.fr-card-product__title a') or 
                          card.select_one('a[href*="/lot/"]') or 
                          card.find('a'))
            if title_elem:
                title = title_elem.get_text(strip=True)
                titles.append(title)
                print(f"   🔍 TITRE VRAI: '{title}'")
        
        print(f"   📋 5 premiers titres: {titles}")
        
        for card in cards:
            title_elem = (card.select_one('h3.fr-card-product__title a') or 
                          card.select_one('a[href*="/lot/"]'))
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            link = BASE_URL + title_elem['href'] if title_elem['href'].startswith('/') else title_elem['href']
            
            # MATCH KEYWORDS ?
            if any(kw in title.lower() for kw in KEYWORDS):
                print(f"   ✅ 🎯 MATCH: {title}")
                
                price_elem = card.select_one('p.fr-price__price')
                price = price_elem.get_text(strip=True) if price_elem else "N/C"
                
                watches.append({
                    'title': title,
                    'price': price,
                    'link': link
                })
        
        page += 1
        time.sleep(1)
    
    print(f"\n🎯 FINAL: {len(watches)} montres")
    return watches

def generate_html(watches):
    date_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    
    if watches:
        items = "".join([f'<div><h3><a href="{w["link"]}">{w["title"]}</a></h3><p>{w["price"]}</p></div>' for w in watches])
        content = f'<div>{items}</div>'
    else:
        content = '<div class="empty"><h2>Aucune montre</h2><p>Vérifiez les logs GitHub pour debug.</p></div>'
    
    return f"""<!DOCTYPE html>
<html><head><title>Debug Montres</title><style>body{{max-width:800px;margin:0 auto;padding:20px;}} .empty{{color:red;}}</style></head>
<body><h1>⌚ {len(watches)}/20 Montres - {date_str}</h1>{content}</body></html>"""

def send_email(html, count):
    sender = os.environ.get('EMAIL_ADDRESS')
    password = os.environ.get('EMAIL_PASSWORD')
    if not sender or not password:
        print("❌ No email secrets")
        return
    
    msg = MIMEMultipart()
    msg['Subject'] = f"DEBUG: {count} Montres"
    msg['From'] = sender
    msg['To'] = "rafael.bchr@gmail.com"
    msg.attach(MIMEText(html, 'html'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.sendmail(sender, "rafael.bchr@gmail.com", msg.as_string())
        server.quit()
        print("✅ EMAIL OK")
    except Exception as e:
        print(f"❌ Email fail: {e}")

def main():
    watches = get_latest_watches()
    html = generate_html(watches)
    
    with open("index.html", "w") as f:
        f.write(html)
    
    send_email(html, len(watches))

if __name__ == "__main__":
    main()