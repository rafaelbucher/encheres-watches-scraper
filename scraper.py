import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import time
import re

# --- CONFIGURATION ---
BASE_URL = "https://encheres-domaine.gouv.fr"
SEARCH_URL_BASE = "https://encheres-domaine.gouv.fr/hermes/biens-mobiliers/bijoux-mode-et-art-de-vivre"
KEYWORDS = ['montre', 'horlogerie', 'chronographe', 'chrono', 'gousset', 'bracelet-montre',
            'rolex', 'omega', 'seiko', 'tudor', 'cartier', 'tag heuer', 'tag-heuer', 'longines',
            'tissot', 'breitling', 'iwc', 'jaeger', 'jaeger-lecoultre', 'patek', 'audemars',
            'vacheron', 'breguet', 'panerai', 'hublot', 'hamilton', 'citizen', 'swatch']
EMAIL_SENDER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = "rafael.bchr@gmail.com"
TARGET_COUNT = 20  # Objectif : 20 dernières montres
MAX_PAGES = 50     # Max pages à scraper pour atteindre l'objectif

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def matches_keywords(text):
    return any(keyword in text.lower() for keyword in KEYWORDS)

def get_latest_watches():
    watches = []
    seen_links = set()
    page = 0

    while len(watches) < TARGET_COUNT and page < MAX_PAGES:
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"🕵️ Scraping page {page + 1}/{MAX_PAGES} : {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Erreur page {page}: {e}")
            break

        soup = BeautifulSoup(response.content, 'lxml')
        cards = soup.find_all('div', class_='fr-card-product')
        print(f"   📊 {len(cards)} cartes totales sur cette page")

        for card in cards:
            title_elem = card.select_one('h3.fr-card-product__title a')
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            link = BASE_URL + title_elem['href'] if title_elem['href'].startswith('/') else title_elem['href']

            if link in seen_links:
                continue
            seen_links.add(link)

            # Description complète
            desc_elem = card.select_one('p.fr-card-product__desc')
            desc_full = (desc_elem.get_text(strip=True) + " ") if desc_elem else ""
            ellipsis_p = card.select_one('div.fr-text--sm.fr-ellipsis--3 p')
            desc_full += ellipsis_p.get_text(strip=True) if ellipsis_p else ""

            # Vérifier si c'est une montre
            full_text = f"{title} {desc_full}"
            if matches_keywords(full_text):
                print(f"   ✅ MONTRE TROUVÉE: {title}")

                # Prix
                price_elem = card.select_one('p.fr-price__price')
                price = price_elem.get_text(strip=True) if price_elem else "Prix n/c"

                # Date clôture
                closure_li = card.select_one('li:has(span.fr-icon-calendar-event-line)')
                closure = closure_li.select_one('strong').get_text(strip=True) if closure_li else "N/C"

                # Statut
                status_elem = card.select_one('p.fr-badge--green-emeraude')
                status = status_elem.get_text(strip=True) if status_elem else "N/C"

                watches.append({
                    'title': title,
                    'desc': desc_full[:200] + "..." if len(desc_full) > 200 else desc_full,
                    'price': price,
                    'closure': closure,
                    'status': status,
                    'link': link
                })

                if len(watches) >= TARGET_COUNT:
                    break

        page += 1
        time.sleep(1)  # Pause polie

    print(f"🎯 Total montres collectées: {len(watches)}")
    return watches[:TARGET_COUNT]
    
def generate_html(watches):
    date_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # Utilisation d'un TABLEAU pour une présentation claire
    table_rows = ""
    if watches:
        table_rows = "".join([
            f"""
            <tr>
                <td><a href="{w['link']}" target="_blank">{w['title']}</a></td>
                <td>{w['price']}</td>
                <td>{w['status']}</td>
                <td>{w['closure']}</td>
                <td>{w['desc']}</td>
            </tr>
            """ for w in watches
        ])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>20 Dernières Montres - Enchères Domaine</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #000091; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            a {{ color: #000091; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .empty {{ text-align: center; padding: 50px; color: #666; }}
        </style>
    </head>
    <body>
        <h1>⌚ 20 Dernières Montres Mises en Ligne</h1>
        <p>Mis à jour le {date_str} | Scraping sur catégorie "Bijoux, mode et art de vivre"</p>
        <p><strong>{len(watches)}/{TARGET_COUNT}</strong> montres trouvées.</p>
        
        {'<div class="empty">Aucune montre trouvée aujourd\'hui. Revenez demain !</div>' if not watches else 
         f'<table><thead><tr><th>Titre</th><th>Prix</th><th>Statut</th><th>Clôture</th><th>Description</th></tr></thead><tbody>{table_rows}</tbody></table>'}
    </body>
    </html>
    """
    return html

def send_email(html_content, count):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("❌ Secrets email manquants")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"⌚ {count} Dernières Montres - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, text)
        server.quit()
        print("✅ EMAIL ENVOYÉ !")
    except Exception as e:
        print(f"❌ Erreur email: {e}")

def main():
    watches = get_latest_watches()
    html = generate_html(watches)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("📄 index.html mis à jour")
    
    send_email(html, len(watches))  # TOUJOURS envoyé

if __name__ == "__main__":
    main()