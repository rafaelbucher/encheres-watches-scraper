import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime

# --- CONFIGURATION ---
BASE_URL = "https://encheres-domaine.gouv.fr"
SEARCH_URL = "https://encheres-domaine.gouv.fr/categorie-de-produit/bijoux-mode-et-art-de-vivre/montres-et-horlogerie.html"
KEYWORDS = ['montre', 'montres', 'horlogerie', 'chronographe', 'rolex', 'omega', 'seiko', 'tocante']
EMAIL_SENDER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = "rafael.bchr@gmail.com"

def get_watches():
    print(f"Scraping {SEARCH_URL}...")
    try:
        response = requests.get(SEARCH_URL, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Erreur lors de la requête : {e}")
        return []

    soup = BeautifulSoup(response.content, 'lxml')
    # NOTE: Ces sélecteurs CSS dépendent de la structure actuelle du site.
    # Il faudra les vérifier avec "Inspecter l'élément" sur le site si cela ne fonctionne pas.
    items = soup.find_all('div', class_='c-card') # Classe générique souvent utilisée

    watches = []
    for item in items:
        title_tag = item.find('h3') or item.find('div', class_='c-card__title')
        if not title_tag: continue
        
        title = title_tag.get_text(strip=True)
        description_tag = item.find('div', class_='c-card__description')
        description = description_tag.get_text(strip=True) if description_tag else ""
        
        # Filtrage par mot-clé
        text_to_search = (title + " " + description).lower()
        if any(keyword in text_to_search for keyword in KEYWORDS):
            link_tag = item.find('a')
            link = BASE_URL + link_tag['href'] if link_tag else "#"
            
            price_tag = item.find('span', class_='c-card__price') # Exemple de classe
            price = price_tag.get_text(strip=True) if price_tag else "Prix non indiqué"

            watches.append({
                'title': title,
                'price': price,
                'link': link,
                'desc': description[:100] + "..."
            })
    
    return watches

def generate_html(watches):
    html_content = f"""
    <html>
    <head>
        <title>Dernières Montres - Enchères Domaine</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .watch {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
            .price {{ color: #d9534f; font-weight: bold; }}
            .date {{ color: #666; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>Rapport du {datetime.datetime.now().strftime('%d/%m/%Y')}</h1>
        <p>{len(watches)} montres trouvées aujourd'hui.</p>
        {''.join([f'<div class="watch"><h3><a href="{w["link"]}">{w["title"]}</a></h3><p class="price">{w["price"]}</p><p>{w["desc"]}</p></div>' for w in watches])}
    </body>
    </html>
    """
    return html_content

def send_email(watches_html):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("Identifiants email manquants. Pas d'envoi.")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"⌚ Montres Enchères Domaine - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    part = MIMEText(watches_html, 'html')
    msg.attach(part)

    try:
        # Utilisation de Gmail comme exemple
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("Email envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")

def main():
    watches = get_watches()
    html = generate_html(watches)
    
    # 1. Sauvegarder pour Netlify
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    # 2. Envoyer par mail s'il y a des résultats
    if watches:
        send_email(html)
    else:
        print("Aucune montre trouvée aujourd'hui.")

if __name__ == "__main__":
    main()