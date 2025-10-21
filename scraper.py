import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import time

# --- CONFIGURATION ---
BASE_URL = "https://encheres-domaine.gouv.fr"
SEARCH_URL_BASE = "https://encheres-domaine.gouv.fr/hermes/biens-mobiliers/bijoux-mode-et-art-de-vivre"
KEYWORDS = ['montre', 'horlogerie', 'chronographe', 'rolex', 'omega', 'seiko', 'tocante', 'gousset', 'cartier', 'tag heuer']
EMAIL_SENDER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = "rafael.bchr@gmail.com"
MAX_PAGES = 5  # Nombre de pages à scraper

def get_watches():
    all_watches = []
    
    for page in range(MAX_PAGES):
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"--- 🕵️ Scraping page {page + 1}/{MAX_PAGES} : {url} ---")
        
        try:
            response = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Erreur lors de la requête sur la page {page}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'lxml')
        
        # SÉLECTEUR MIS À JOUR : Le site utilise le DSFR (Système de Design de l'État)
        # La classe principale pour une "carte" produit est 'fr-card'
        items = soup.find_all('div', class_='fr-card')
        print(f"    Articles bruts trouvés sur cette page : {len(items)}")

        if not items and page == 0:
            print("⚠️ Aucun article trouvé sur la première page. Le sélecteur 'div.fr-card' est peut-être obsolète.")
            # Si vous avez besoin de débugger, décommentez la ligne ci-dessous dans les logs de GitHub
            # print(soup.prettify()[:2000])
        
        for item in items:
            title_tag = item.find('h3', class_='fr-card__title')
            
            if not title_tag:
                continue
            
            title = title_tag.get_text(strip=True)

            # --- Outil de débogage ---
            # Pour voir tous les articles que le script analyse, décommentez la ligne suivante :
            # print(f"    [Analyse] Titre vu : {title}")
            
            description_tag = item.find('p', class_='fr-card__desc')
            description = description_tag.get_text(strip=True) if description_tag else ""
            
            text_to_search = (title + " " + description).lower()
            
            if any(keyword in text_to_search for keyword in KEYWORDS):
                print(f"✅ TROUVÉ : {title}")

                link_tag = item.find('a', class_='fr-card__link') or title_tag.find('a')
                link = "#"
                if link_tag and 'href' in link_tag.attrs:
                    link = link_tag['href']
                    if not link.startswith('http'):
                        link = BASE_URL + link
                
                # Le prix est dans un 'p' avec la classe 'fr-card__detail'
                price_tag = item.find('p', class_='fr-card__detail')
                price = price_tag.get_text(strip=True) if price_tag else "Prix n/c"

                all_watches.append({
                    'title': title,
                    'price': price,
                    'link': link,
                    'desc': description[:150] + "..." if description else "Pas de description"
                })
        
        time.sleep(1) # Soyons polis avec le serveur

    # Dé-duplication au cas où un article apparaîtrait sur deux pages (rare mais possible)
    unique_watches = {watch['link']: watch for watch in all_watches}.values()
    return list(unique_watches)

def generate_html(watches):
    # (Le reste du code est identique à la V2, pas besoin de le modifier)
    # ... (le code de generate_html et send_email reste le même que dans ma réponse précédente)
    # ... je le remets ici pour que vous puissiez tout copier d'un coup.
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Montres Enchères Domaine</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }}
            h1 {{ color: #000091; }} /* Bleu gouvernement */
            .info {{ background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .watch {{ background: #fff; border: 1px solid #e0e0e0; padding: 20px; margin-bottom: 15px; border-radius: 8px; transition: transform 0.2s; }}
            .watch:hover {{ transform: translateY(-3px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            .watch h3 {{ margin-top: 0; }}
            .watch a {{ color: #000091; text-decoration: none; font-size: 1.1em;}}
            .watch a:hover {{ text-decoration: underline; }}
            .price {{ color: #d9534f; font-weight: bold; font-size: 1.2em; }}
            .empty {{ text-align: center; padding: 50px; color: #666; }}
        </style>
    </head>
    <body>
        <h1>⌚ Rapport du {datetime.datetime.now().strftime('%d/%m/%Y')}</h1>
        <div class="info">
            <p>Scraping réalisé sur les <strong>{MAX_PAGES} premières pages</strong> de la catégorie "Bijoux mode et art de vivre".</p>
            <p><strong>{len(watches)}</strong> montre(s) trouvée(s) aujourd'hui.</p>
        </div>
        
        {'<div class="empty"><h3>Aucune montre trouvée pour le moment.</h3><p>Le script a bien fonctionné, mais aucun article ne correspondait aux mots-clés.</p></div>' if not watches else ''}

        {''.join([f'<div class="watch"><h3><a href="{w["link"]}" target="_blank">{w["title"]}</a></h3><p class="price">{w["price"]}</p><p>{w["desc"]}</p></div>' for w in watches])}
    </body>
    </html>
    """
    return html_content


def send_email(watches_html, count):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("❌ Identifiants email manquants. Pas d'envoi.")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"✅ {count} Montre(s) trouvée(s) - Enchères Domaine - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    part = MIMEText(watches_html, 'html')
    msg.attach(part)

    try:
        print(f"Tentative d'envoi d'email de {EMAIL_SENDER} vers {EMAIL_RECEIVER}...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("✅ Email envoyé avec succès !")
    except smtplib.SMTPAuthenticationError:
        print("❌ Erreur d'authentification SMTP. Vérifiez votre adresse et votre Mot de passe d'application.")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email: {e}")

def main():
    print("Démarrage du script v3...")
    watches = get_watches()
    print(f"--- Résultat final ---")
    print(f"Total trouvé : {len(watches)} montre(s) correspondant aux critères.")

    html = generate_html(watches)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
        print("Fichier index.html mis à jour.")
    
    if watches:
        send_email(html, len(watches))
    else:
        print("📭 Pas d'email envoyé car aucune montre trouvée.")

if __name__ == "__main__":
    main()