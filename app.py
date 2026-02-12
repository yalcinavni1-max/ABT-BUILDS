import re
import time
import random
from flask import Flask, jsonify, send_from_directory
import cloudscraper # SİHİRLİ KÜTÜPHANE
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

# CloudScraper nesnesi oluştur (Bot korumasını aşan araç)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

def get_latest_version():
    try:
        # Versiyon kontrolü için basit requests yeterli
        import requests
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

def scrape_summoner(url):
    # Siteyi yormamak için kısa bekleme
    time.sleep(random.uniform(1.0, 3.0))
    
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    try:
        # BURASI DEĞİŞTİ: requests yerine scraper kullanıyoruz
        response = scraper.get(url)
        
        # Eğer koruma sayfası geldiyse bile scraper bunu genelde çözer.
        if response.status_code != 200:
            print(f"Hata Kodu: {response.status_code}")
            return {"error": "Site Erişimi Engellendi", "summoner": "Veri Yok", "matches": []}

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
                # KDA olmayan satırı atla
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

                # 2. İTEMLER (HEM RESİM HEM CLASS TARAMA)
                items = []
                
                # Sadece itemlerin bulunduğu alanı al
                items_container = row.find("div", class_="items")
                search_area = items_container if items_container else row
                
                # HTML kodunu metne çevir
                html_text = str(search_area)

                # YÖNTEM A: Resim yollarındaki sayıları bul (items/6672.png)
                matches_img = re.findall(r"items\/[\w\/]*(\d{4})", html_text)
                
                # YÖNTEM B: Class isimlerindeki sayıları bul (requireTooltip-item-6672)
                # League of Graphs bazen item ID'sini class içine gizler.
                matches_class = re.findall(r"item[-_]?(\d{4})", html_text)

                # YÖNTEM C: Düz 4 haneli sayıları bul (img src=".../3078.png")
                matches_raw = re.findall(r"[\"\/](\d{4})\.(png|jpg|webp)", html_text)
                
                # Raw match sonucunda tuple döner (id, uzantı), sadece id'yi alalım
                raw_ids = [m[0] for m in matches_raw]

                # Hepsini birleştir
                all_candidates = matches_img + matches_class + raw_ids
                
                for num in all_candidates:
                    val = int(num)
                    
                    # FİLTRELER
                    if 1000 <= val <= 8000:
                        # Yasaklı ID'ler (Yıllar, Rünler, Ekran Boyutları)
                        if 2020 <= val <= 2030: continue
                        if 5000 <= val < 6000: continue
                        if val in [1080, 1200, 1280, 1440, 1920, 2560]: continue
                        
                        items.append(f"{RIOT_CDN}/item/{val}.png")

                # Tekrarları temizle
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                
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
