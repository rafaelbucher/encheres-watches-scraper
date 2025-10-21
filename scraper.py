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
# URL de base sans les paramètres de pagination
SEARCH_URL_BASE = "https://encheres-domaine.gouv.fr/categorie-de-produit/bijoux-mode-et-art-de-vivre/montres-et-horlogerie.html?lot_status=13%2C14&page=1"
KEYWORDS = ['montre', 'horlogerie', 'chronographe', 'rolex', 'omega', 'seiko', 'tocante', 'bracelet-montre']
EMAIL_SENDER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = "rafael.bchr@gmail.com"
MAX_PAGES = 5 # Nombre de pages à scraper

def get_watches():
    all_watches = []
    
    for page in range(MAX_PAGES):
        # Gestion de la pagination (souvent ?page=0, ?page=1 sur ces sites)
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"--- Scraping page {page + 1}/{MAX_PAGES} : {url} ---")
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"Erreur lors de la requête sur la page {page}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'lxml')
        
        # Sélecteur mis à jour : tentative de trouver des éléments plus génériques si fr-card-product échoue
        # On cherche souvent des <article> ou des <div> avec des classes spécifiques aux produits
        items = soup.find_all('div', class_='fr-card-product') or \
                soup.find_all('article') or \
                soup.find_all('div', class_='row-item') # Exemples de fallbacks

        print(f"Nombre d'articles bruts trouvés sur la page : {len(items)}")

        if len(items) == 0:
            print("⚠️ Aucun article trouvé. Les sélecteurs CSS sont peut-être obsolètes.")
            # On peut essayer d'afficher un bout du HTML pour debug si besoin dans les logs
            # print(soup.prettify()[:1000]) 
        
        for item in items:
            # Essai de plusieurs sélecteurs pour le titre
            title_tag = item.find('h3') or \
                        item.find('div', class_='c-card__title') or \
                        item.find('a', class_='fr-card__link') # Nouveau standard gouvernemental possible

            if not title_tag:
                continue
            
            title = title_tag.get_text(strip=True)
            
            # Description
            description_tag = item.find('div', class_='c-card__description') or \
                              item.find('p', class_='fr-card__desc')
            description = description_tag.get_text(strip=True) if description_tag else ""
            
            # Filtrage
            text_to_search = (title + " " + description).lower()
            
            # DEBUG: Décommentez la ligne suivante pour voir TOUS les titres passer dans les logs GitHub
            # print(f"Vu: {title}") 

            if any(keyword in text_to_search for keyword in KEYWORDS):
                print(f"✅ TROUVÉ : {title}")
                link_tag = item.find('a')
                link = BASE_URL + link_tag['href'] if link_tag else "#"
                
                # Gestion des liens relatifs si nécessaire
                if not link.startswith('http'):
                     link = BASE_URL + link

                price_tag = item.find('span', class_='c-card__price') or \
                            item.find('p', class_='fr-badge')
                price = price_tag.get_text(strip=True) if price_tag else "Prix n/c"

                all_watches.append({
                    'title': title,
                    'price': price,
                    'link': link,
                    'desc': description[:150] + "..." if description else "Pas de description"
                })
        
        # Pause pour être gentil avec le serveur
        time.sleep(1)

    return all_watches

def generate_html(watches):
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
            .watch a {{ color: #000091; text-decoration: none; }}
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
        
        {'<div class="empty">Aucune montre trouvée pour le moment.</div>' if not watches else ''}

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
    msg['Subject'] = f"⌚ {count} Montres - Enchères Domaine - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    part = MIMEText(watches_html, 'html')
    msg.attach(part)

    try:
        print(f"Tentative d'envoi d'email de {EMAIL_SENDER} vers {EMAIL_RECEIVER}...")
        # Note: Si vous n'utilisez pas Gmail, changez 'smtp.gmail.com' et 465
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
    print("Démarrage du script...")
    watches = get_watches()
    print(f"Total trouvé : {len(watches)} montres.")

    html = generate_html(watches)
    
    # 1. Toujours sauvegarder l'HTML pour Netlify (même si vide, pour savoir que ça a tourné)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
        print("Fichier index.html mis à jour.")
    
    # 2. Envoyer par mail SEULEMENT si on a trouvé quelque chose
    if watches:
        send_email(html, len(watches))
    else:
        print("📭 Pas d'email envoyé car aucune montre trouvée.")

if __name__ == "__main__":
    main()