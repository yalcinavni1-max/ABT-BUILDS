import re
import time
import random
import logging
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- TAKİP LİSTESİ ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- NOT HESAPLAMA MOTORU ---
def calculate_grade(kda_text):
    try:
        # "3.50:1" gibi gelen veriyi temizle
        # "Perfect" yazıyorsa (hiç ölmemişse) KDA sonsuzdur, direkt S verelim
        if "Perfect" in kda_text or "Mükemmel" in kda_text:
            return "S"
            
        # Regex ile sadece sayıyı al (Örn: 3.50)
        match = re.search(r"(\d+\.?\d*)", kda_text)
        if not match:
            return "-"
            
        kda = float(match.group(1))
        
        # --- SENİN KURALLARIN ---
        if kda >= 4.0: return "S"
        elif 3.0 <= kda < 4.0: return "A"
        elif 2.5 <= kda < 3.0: return "B"
        elif 2.0 <= kda < 2.5: return "C"
        elif 1.0 < kda < 2.0: return "D"
        else: return "F" # 1 ve altı
        
    except:
        return "-"

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- SCRAPER ---
def scrape_summoner(url):
    time.sleep(random.uniform(0.5, 1.5))
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Profil
        summoner_name = "Sihirdar"
        try: summoner_name = soup.find("title").text.split("(")[0].strip().replace(" - League of Legends", "")
        except: pass

        rank_text = "Unranked"
        try:
            banner = soup.find("div", class_="bannerSubtitle")
            rank_text = banner.text.strip() if banner else soup.find("div", class_="league-tier").text.strip()
        except: pass

        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try: profile_icon = "https:" + soup.find("div", class_="img").find("img").get("src")
        except: pass

        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # Şampiyon
                champ_key = "Poro"
                for link in row.find_all("a"):
                    if "/champions/builds/" in link.get("href", ""):
                        parts = link.get("href").split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").lower()
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # İtemler
                items = []
                if row.find("div", class_="items"):
                    for img in row.find("div", class_="items").find_all("img"):
                        src = img.get("src", "")
                        if any(x in src for x in ["champion", "spell", "perk"]): continue
                        m = re.search(r"(\d{4})", src)
                        if m:
                            val = int(m.group(1))
                            if 1000 <= val <= 8000 and not (2020 <= val <= 2030) and not (5000 <= val < 6000):
                                items.append(f"{RIOT_CDN}/item/{val}.png")
                
                clean_items = list(dict.fromkeys(items))[:9] # Duplicate sil ve 9 tane al

                # İstatistikler
                row_text = row.text.strip()
                
                cs_stat = "0 CS"
                cs_m = re.search(r"(\d+)\s*CS", row_text)
                if cs_m: cs_stat = f"{cs_m.group(1)} CS"

                gold_stat = "0k"
                g_m = re.search(r"(\d+\.?\d*)\s*k", row_text)
                if g_m: gold_stat = f"{g_m.group(1)}k"

                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row_text or "Zafer" in row_text else "lose"

                # --- NOT HESAPLAMA ---
                grade = calculate_grade(kda_text)

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "cs": cs_stat,
                    "gold": gold_stat,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade # S, A, B, C...
                })
                if len(matches_info) >= 5: break
            except: continue
        
        return {"summoner": summoner_name, "rank": rank_text, "icon": profile_icon, "matches": matches_info}

    except Exception as e:
        return {"error": str(e), "summoner": "Hata", "matches": []}

@app.route('/api/get-ragnar', methods=['GET'])
def get_all_users():
    all_data = []
    for url in URL_LISTESI:
        all_data.append(scrape_summoner(url))
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
