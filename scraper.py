def get_latest_watches():
    watches = []
    page = 0
    
    while len(watches) < TARGET_COUNT and page < MAX_PAGES:
        url = f"{SEARCH_URL_BASE}?page={page}"
        print(f"\n🕵️  PAGE {page + 1}: {url}")
        
        # ✅ CORRECTION CLÉ : Ajoutez verify=False
        r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        print(f"   ✅ Statut HTTP: {r.status_code}")
        
        soup = BeautifulSoup(r.content, 'lxml')
        
        cards = (soup.find_all('div', class_='fr-card-product') or 
                 soup.find_all('article', class_='fr-card-product') or 
                 soup.find_all('div', {'class': lambda x: x and 'card-product' in x}))
        
        print(f"   📊 CARTES TROUVÉES: {len(cards)}")
        
        if len(cards) == 0:
            print("   ❌ AUCUNE CARTE ! Debug HTML:")
            print(soup.select_one('main')[:1000])
            break
        
        # DEBUG: Affiche les 5 premiers titres
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