import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import time
import urllib3

# Désactiver les avertissements SSL car on utilise verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
BASE_URL = "https://encheres-domaine.gouv.fr"
SEARCH_URL_BASE = "https://encheres-domaine.gouv.fr/hermes/biens-mobiliers/bijoux-mode-et-art-de-vivre"
# Liste de mots-clés étendue pour ne rien rater
KEYWORDS = [
    'montre', 'horlogerie', 'chronographe', 'chrono', 'gousset', 'tocante', 'garde-temps',
    'rolex', 'omega', 'seiko', 'tudor', 'cartier', 'tag heuer', 'tag-heuer', 'longines',
    'tissot', 'breitling', 'iwc', 'jaeger', 'patek', 'audemars', 'vacheron', 'breguet',
    'panerai', 'hublot', 'hamilton', 'citizen', 'swatch', 'casio', 'lip', 'hermes', 'chanel'
]
EMAIL_SENDER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = "rafael.bchr@gmail.com"

# Headers pour imiter un vrai navigateur
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
}

def get_all_watches():
    all_watches = []
    seen_links = set()
    page = 0
    max_safety_pages = 100 # Sécurité pour éviter une boucle infinie en cas de bug du site

    print("🚀 Démarrage du scraping INTÉGRAL...")

    while page < max_safety_pages:
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"\n📄 Traitement de la page {page}...")
        
        try:
            # verify=False est INDISPENSABLE pour GitHub Actions sur ce site gouvernemental
            response = requests.get(url, headers=HEADERS, timeout=30, verify=False)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Erreur critique sur la page {page}: {e}")
            break

        soup = BeautifulSoup(response.content, 'lxml')
        
        # Sélecteur robuste pour trouver les cartes produits
        cards = soup.find_all('div', class_='fr-card-product')
        
        if not cards:
            print("🏁 Plus aucune carte trouvée. Fin du scraping.")
            break

        print(f"   ↳ {len(cards)} articles détectés sur cette page.")
        
        items_found_on_page = 0
        for card in cards:
            # Extraction du Titre et Lien
            title_tag = card.select_one('h3.fr-card-product__title a')
            if not title_tag: continue
            
            title = title_tag.get_text(strip=True)
            link = title_tag['href']
            if not link.startswith('http'):
                link = BASE_URL + link

            # Éviter les doublons si le site affiche deux fois le même objet
            if link in seen_links: continue
            seen_links.add(link)

            # Extraction de la Description pour améliorer la recherche
            desc_tag = card.select_one('p.fr-card-product__desc')
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            
            # Recherche des mots-clés dans le Titre ET la Description
            full_text_search = (title + " " + desc).lower()
            
            if any(kw in full_text_search for kw in KEYWORDS):
                # Extraction des détails supplémentaires
                price_tag = card.select_one('p.fr-price__price')
                price = price_tag.get_text(strip=True) if price_tag else "N/C"

                status_tag = card.select_one('.fr-badge')
                status = status_tag.get_text(strip=True) if status_tag else ""

                # Date de fin souvent dans un <li> avec une icône calendrier
                end_date = "N/C"
                date_li = card.select_one('li:has(.fr-icon-calendar-event-line)')
                if date_li:
                     end_date = date_li.get_text(strip=True).replace('Clôture le', '').strip()

                all_watches.append({
                    'title': title,
                    'price': price,
                    'link': link,
                    'status': status,
                    'end_date': end_date
                })
                items_found_on_page += 1
                print(f"   ✅ Trouvé : {title} ({price})")

        if items_found_on_page == 0:
            print("   (Aucune montre sur cette page)")

        page += 1
        time.sleep(0.5) # Petite pause pour être gentil avec le serveur

    print(f"\n🎉 TERMINÉ ! Total trouvé : {len(all_watches)} montres sur {page} pages parcourues.")
    return all_watches

def generate_html(watches):
    date_str = datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')
    
    rows_html = ""
    for w in watches:
        # Coloration simple selon le statut
        status_class = "status-green" if "cours" in w['status'].lower() else "status-gray"
        
        rows_html += f"""
        <tr>
            <td><a href="{w['link']}" target="_blank"><strong>{w['title']}</strong></a></td>
            <td class="price">{w['price']}</td>
            <td><span class="badge {status_class}">{w['status']}</span></td>
            <td>{w['end_date']}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Toutes les Montres - Enchères Domaine</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f8f9fa; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #000091; border-bottom: 2px solid #000091; padding-bottom: 10px; }}
            .info {{ background: #e8edff; padding: 15px; border-radius: 8px; margin-bottom: 25px; color: #000091; }}
            table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
            th {{ background-color: #f1f3f8; text-align: left; padding: 15px; color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }}
            td {{ padding: 15px; border-top: 1px solid #eee; vertical-align: middle; }}
            tr:hover {{ background-color: #f8f9ff; }}
            a {{ color: #000091; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .price {{ font-weight: bold; color: #d9534f; font-size: 1.1em; white-space: nowrap; }}
            .badge {{ padding: 4px 8px; border-radius: 12px; font-size: 0.85em; font-weight: bold; display: inline-block; }}
            .status-green {{ background-color: #d1fae5; color: #065f46; }}
            .status-gray {{ background-color: #f3f4f6; color: #1f2937; }}
            .empty {{ text-align: center; padding: 60px; color: #999; font-size: 1.2em; background: white; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <h1>⌚ Observatoire des Montres - Domaine</h1>
        <div class="info">
            Rapport généré le <strong>{date_str}</strong>.<br>
            <strong>{len(watches)}</strong> montres trouvées au total sur le site.
        </div>

        {f'<table><thead><tr><th>Modèle</th><th>Mise à prix</th><th>Statut</th><th>Fin de vente</th></tr></thead><tbody>{rows_html}</tbody></table>' if watches else '<div class="empty">Aucune montre disponible actuellement sur le site.</div>'}
    </body>
    </html>
    """
    return html

def send_email(html_content, count):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("⚠️ Pas d'envoi d'email (secrets manquants).")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"⌚ {count} Montres disponibles - Rapport Complet - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # Configuration pour Gmail SSL
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("✅ Email de rapport envoyé avec succès !")
    except Exception as e:
        print(f"❌ Échec de l'envoi de l'email : {e}")

def main():
    # 1. Scraping intégral
    watches = get_all_watches()
    
    # 2. Génération du rapport HTML
    html = generate_html(watches)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("💾 Fichier index.html généré.")
    
    # 3. Envoi de l'email (seulement s'il y a des résultats, ou toujours si vous préférez)
    # J'ai mis > 0 pour ne pas spammer s'il n'y a vraiment rien, mais changez à True pour forcer.
    if len(watches) > 0:
        send_email(html, len(watches))
    else:
        print("📭 Aucune montre trouvée, pas d'email envoyé.")

if __name__ == "__main__":
    main()