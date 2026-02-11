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
    # Engel yememek için rastgele bekleme
    time.sleep(random.uniform(1.0, 3.0))
    
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # SİHİRLİ DOKUNUŞ: iPhone gibi davranıyoruz
    # Bu sayede site bize basit HTML gönderiyor ve resimler gizlenmiyor.
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8"
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
            # Mobil görünümde rank yeri değişebilir, genel arama yapıyoruz
            rank_div = soup.find("div", class_="league-tier")
            if rank_div: rank_text = rank_div.text.strip()
            else:
                banner = soup.find("div", class_="bannerSubtitle")
                if banner: rank_text = banner.text.strip()
        except: pass

        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try:
            # Profil resmi
            img_div = soup.find("div", class_="img")
            if img_div and img_div.find("img"):
                src = img_div.find("img").get("src")
                if src: profile_icon = "https:" + src
        except: pass

        # --- MAÇLAR ---
        matches_info = []
        # Maç tablosunu bul
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                # KDA'sı olmayan satır maç değildir
                if not row.find("div", class_="kda"): continue

                # 1. ŞAMPİYON BULMA
                champ_key = "Poro"
                # Linklerden şampiyon adını çek
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        # URL yapısı: /champions/builds/annie
                        if len(parts) >= 3:
                            # Parçaları temizle
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            # Bazı özel isimleri düzelt
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
                
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # 2. İTEMLER (HEDEF ODAKLI TARAMA)
                items = []
                
                # Sadece itemlerin bulunduğu özel kutuyu buluyoruz: <div class="items">
                # Bu yöntem, sayfadaki diğer sayıları item sanmamızı engeller.
                items_container = row.find("div", class_="items")
                
                if items_container:
                    # Kutu içindeki tüm resimleri al
                    images = items_container.find_all("img")
                    
                    for img in images:
                        # Link nerede olursa olsun al (src, data-src)
                        src = img.get("src") or img.get("data-src") or ""
                        if not src: continue
                        
                        # Linkin içindeki sayıyı çek
                        # Sadece sayıları arıyoruz, link yapısına takılmıyoruz.
                        num_match = re.search(r"(\d+)", src)
                        if num_match:
                            val = int(num_match.group(1))
                            
                            # Mantık Süzgeci
                            # 1000'den küçük ve 8000'den büyük sayılar item değildir.
                            # 5000-6000 arası ründür, almıyoruz.
                            if 1000 <= val <= 8000:
                                if 5000 <= val < 6000: continue 
                                if 2020 <= val <= 2030: continue # Yıllar
                                if val == 3350: continue # Totem trinket bazen karışır, istersen tut.
                                
                                items.append(f"{RIOT_CDN}/item/{val}.png")

                # Tekrarları temizle
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                
                # 7 İtem Limiti
                clean_items = clean_items[:7]

                # KDA ve Sonuç
                kda_div = row.find("div", class_="kda")
                kda_text = kda_div.text.strip()
                
                result = "lose"
                # Satırın metninde "Victory" veya "Zafer" geçiyor mu?
                row_text = row.text.lower()
                if "victory" in row_text or "zafer" in row_text: 
                    result = "win"
                
                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items
                })
                if len(matches_info) >= 5: break
            except Exception as inner_e:
                continue
        
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
