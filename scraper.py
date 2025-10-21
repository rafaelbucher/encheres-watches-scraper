import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import time
import urllib3
import re

# Désactive les alertes SSL pour des logs propres
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
BASE_URL = "https://encheres-domaine.gouv.fr"
# ON UTILISE VOTRE URL SPÉCIFIQUE
SEARCH_URL_BASE = "https://encheres-domaine.gouv.fr/categorie-de-produit/bijoux-mode-et-art-de-vivre/montres-et-horlogerie.html"

EMAIL_SENDER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = "rafael.bchr@gmail.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def get_all_watches():
    all_watches = []
    seen_links = set()
    page = 1  # On commence à 1 pour cette URL spécifique
    
    print(f"🚀 Démarrage du scraping sur : {SEARCH_URL_BASE}")

    while True:
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"\n📄 Scraping page {page} : {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30, verify=False)
            # Si on est redirigé vers la page 1 ou une autre catégorie, c'est qu'on est au bout
            if page > 1 and response.url != url and 'page=' not in response.url:
                 print("🔀 Redirection détectée, fin probable des résultats.")
                 break
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Erreur page {page}: {e}")
            break

        soup = BeautifulSoup(response.content, 'lxml')
        
        # --- STRATÉGIE DE SÉLECTION ROBUSTE ---
        # 1. On cherche les conteneurs classiques
        cards = soup.find_all('div', class_='fr-card-product')
        
        # 2. Fallback : si pas de conteneurs, on cherche TOUS les liens de lots
        if not cards:
            print("⚠️ Pas de 'fr-card-product' trouvé, tentative de recherche par liens bruts...")
            lot_links = soup.find_all('a', href=re.compile(r'/lot/\d+.*\.html'))
            if lot_links:
                print(f"   ↳ {len(lot_links)} liens de lots trouvés via fallback !")
                # On simule des cartes pour la boucle suivante
                cards = [link.find_parent('div') or link.parent for link in lot_links]
            else:
                # Vraiment rien trouvé sur cette page
                if page == 1:
                    print("❌ ERREUR CRITIQUE : Aucun lot trouvé dès la page 1.")
                    print("🔍 DEBUG HTML (début) :")
                    print(soup.prettify()[:1000])
                else:
                    print("🏁 Page vide atteinte. Fin du scraping.")
                break

        print(f"   📊 {len(cards)} articles potentiels sur cette page.")
        
        items_added = 0
        for card in cards:
            if not card: continue
            
            # Essai de trouver le titre et le lien
            title_tag = card.find('h3') or card.find('a', href=re.compile(r'/lot/'))
            if not title_tag:
                 # Dernier essai : le conteneur LUI-MÊME est peut-être le lien
                 if card.name == 'a' and '/lot/' in card.get('href', ''):
                     title_tag = card
                 else:
                     continue

            # Nettoyage du titre (parfois le titre est dans un sous-tag <a> du <h3>)
            if title_tag.name == 'h3' and title_tag.find('a'):
                link_tag = title_tag.find('a')
                title = link_tag.get_text(strip=True)
                link = link_tag['href']
            else:
                title = title_tag.get_text(strip=True)
                link = title_tag.get('href') if title_tag.has_attr('href') else title_tag.find('a')['href']

            if not link: continue
            if not link.startswith('http'): link = BASE_URL + link
            
            if link in seen_links: continue
            seen_links.add(link)

            # Prix
            price_tag = card.select_one('.fr-price__price') or card.find(string=re.compile(r'\d+ €'))
            price = price_tag.get_text(strip=True) if price_tag else (str(price_tag) if price_tag else "N/C")
            if "Mise à prix" in price: price = price.replace("Mise à prix", "").strip()

            # Statut & Date
            status = "En vente"
            status_tag = card.select_one('.fr-badge')
            if status_tag: status = status_tag.get_text(strip=True)
            
            end_date = "N/C"
            date_li = card.select_one('li:has(.fr-icon-calendar-event-line)')
            if date_li: end_date = date_li.get_text(strip=True).replace('Clôture le', '').strip()

            all_watches.append({
                'title': title,
                'price': price,
                'link': link,
                'status': status,
                'end_date': end_date
            })
            items_added += 1
            print(f"   ✅ +1: {title[:30]}...")

        if items_added == 0 and page > 1:
             print("🏁 Aucune nouvelle montre sur cette page. Fin.")
             break

        page += 1
        time.sleep(1)

    print(f"\n🎉 TERMINÉ : {len(all_watches)} montres trouvées au total.")
    return all_watches

# --- (Les fonctions generate_html et send_email 