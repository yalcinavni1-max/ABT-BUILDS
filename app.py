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

session = requests.Session()

def scrape_summoner(url):
    # Bekleme süresi
    time.sleep(random.uniform(1.0, 2.0))
    
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # KİLİT NOKTA: Kendimizi Google Botu olarak tanıtıyoruz.
    # Siteler Google botuna resimleri asla gizlemez.
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = session.get(url, headers=headers, timeout=20)
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
                # KDA divi yoksa maç satırı değildir
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # 1. ŞAMPİYON BULMA
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

                # 2. İTEMLER (GOOGLEBOT MODU)
                items = []
                
                # Sadece itemlerin olduğu "items" kutusunu buluyoruz.
                # Googlebot olduğumuz için site burada "img" etiketlerini açıkça verecektir.
                items_container = row.find("div", class_="items")
                
                if items_container:
                    # Kutu içindeki tüm resimleri al
                    images = items_container.find_all("img")
                    
                    for img in images:
                        # Resmin linkini al
                        src = img.get("src") or img.get("data-original") or ""
                        
                        if not src: continue

                        # Linkin içinde "champion", "spell" vb. varsa atla (Garanti olsun)
                        if any(x in src for x in ["champion", "spell", "perk", "rune", "summoner", "class"]):
                            continue

                        # Linkin içindeki 4 haneli sayıyı al
                        # Örnek: .../3078.png -> 3078
                        match = re.search(r"(\d{4})", src)
                        if match:
                            val = int(match.group(1))
                            
                            # Filtreler (Hata payını sıfıra indirmek için)
                            if 1000 <= val <= 8000:
                                if 2020 <= val <= 2030: continue # Yıllar
                                if 5000 <= val < 6000: continue # Rünler
                                if val in [1080, 1200, 1280, 1440, 1920]: continue # Ekran boyutu

                                items.append(f"{RIOT_CDN}/item/{val}.png")

                # Tekrarları Temizle
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                
                # İlk 7 itemi al
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
