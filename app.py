import re
import time
import random
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

def scrape_summoner(url):
    # Siteyi yormamak ve engel yememek için bekleme
    time.sleep(random.uniform(1.0, 2.5))
    
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- PROFİL ---
        summoner_name = "Sihirdar"
        try:
            title = soup.find("title").text
            summoner_name = title.split("(")[0].strip().replace(" - League of Legends", "")
        except: pass

        rank_text = "Unranked"
        try:
            banner_sub = soup.find("div", class_="bannerSubtitle")
            if banner_sub: rank_text = banner_sub.text.strip()
            else:
                tier = soup.find("div", class_="league-tier")
                if tier: rank_text = tier.text.strip()
        except: pass

        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try:
            img = soup.find("div", class_="img").find("img")
            if img: profile_icon = "https:" + img.get("src")
        except: pass

        # --- MAÇLAR ---
        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # 1. ŞAMPİYON
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            name_map = {
                                "wukong": "MonkeyKing", "renata": "Renata", "fiddlesticks": "Fiddlesticks",
                                "kais'a": "Kaisa", "kaisa": "Kaisa", "leesin": "LeeSin", "belveth": "Belveth",
                                "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo",
                                "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao",
                                "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol",
                                "twistedfate": "TwistedFate"
                            }
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                
                if champ_key == "Poro":
                    imgs = row.find_all("img")
                    for img in imgs:
                        alt = img.get("alt", "")
                        if alt and len(alt) > 2 and alt not in ["Victory", "Defeat", "Role", "Item", "Gold"]:
                            champ_key = alt.replace(" ", "").replace("'", "").replace(".", "")
                            break

                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # 2. İTEMLER (HİBRİT TOPLAYICI)
                items = []
                
                # Sadece itemlerin olduğu özel kutuyu buluyoruz.
                # League of Graphs'ta bu genelde "items" class'ına sahip bir div'dir.
                items_container = row.find("div", class_="items")
                
                # Eğer özel kutu yoksa satırın tamamına bak (Yedek Plan)
                search_area = items_container if items_container else row
                
                # O alandaki tüm resimleri bul
                img_tags = search_area.find_all("img")
                
                for img in img_tags:
                    # Resmin tüm olası kaynaklarını tek bir metinde birleştir
                    full_tag = str(img) + img.get("src", "") + img.get("data-original", "")
                    
                    # 1. ELEME: Şampiyon, Rün, Büyü resimlerini direkt atla
                    if any(x in full_tag for x in ["champion", "spell", "perk", "rune", "class", "role", "summoner"]):
                        continue

                    # 2. ARAMA: İçindeki 4 haneli sayıyı bul
                    # Regex sadece sayıyı alır, uzantıya (.png) bakmaz.
                    match = re.search(r"(\d{4})", full_tag)
                    
                    if match:
                        val = int(match.group(1))
                        
                        # 3. DOĞRULAMA: Sayı mantıklı bir item ID'si mi?
                        if 1000 <= val <= 8000:
                            # 2024, 2025 (Yıl) -> Çöp
                            if 2020 <= val <= 2030: continue
                            # 5000-6000 (Rün) -> Çöp
                            if 5000 <= val < 6000: continue
                            # Ekran Genişlikleri -> Çöp
                            if val in [1080, 1200, 1280, 1440, 1920]: continue
                            
                            # ALTIN VURUŞ: Riot'un temiz sunucusundan resmi oluştur
                            items.append(f"{RIOT_CDN}/item/{val}.png")

                # Tekrarları Temizle
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                
                # 7 İtem Limiti
                clean_items = clean_items[:7]

                kda_text = kda_div.text.strip()
                result = "lose"
                if "Victory" in row.text or "Zafer" in row.text: result = "win"
                
                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items
                })
                if len(matches_info) >= 5: break
            except: continue
        
        return {
            "summoner": summoner_name,
            "rank": rank_text,
            "icon": profile_icon,
            "matches": matches_info
        }

    except Exception as e:
        return {"error": str(e), "summoner": "Hata", "matches": []}

@app.route('/api/get-ragnar', methods=['GET'])
def get_all_users():
    all_data = []
    for url in URL_LISTESI:
        data = scrape_summoner(url)
        all_data.append(data)
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
