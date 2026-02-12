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

# --- NOT HESAPLAMA (S, A, B...) ---
def calculate_grade(kda_text):
    try:
        if "Perfect" in kda_text or "Mükemmel" in kda_text: return "S"
        numbers = re.findall(r"(\d+)", kda_text)
        kda_score = 0.0
        if len(numbers) >= 3:
            kills = float(numbers[0])
            deaths = float(numbers[1])
            assists = float(numbers[2])
            if deaths == 0: kda_score = 99.0
            else: kda_score = (kills + assists) / deaths
        else:
            match = re.search(r"(\d+\.?\d*)", kda_text)
            if match: kda_score = float(match.group(1))
            else: return "-"

        if kda_score >= 4.0: return "S"
        elif 3.0 <= kda_score < 4.0: return "A"
        elif 2.5 <= kda_score < 3.0: return "B"
        elif 2.0 <= kda_score < 2.5: return "C"
        elif 1.0 < kda_score < 2.0: return "D"
        else: return "F"
    except: return "-"

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Profil Bilgileri
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

        # Maçlar
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
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # İtemler
                items = []
                img_tags = row.find_all("img")
                for img in img_tags:
                    src = img.get("src", "")
                    if any(x in src for x in ["champion", "spell", "tier", "perk"]): continue
                    m = re.search(r"(\d{4})", src)
                    if m:
                        val = int(m.group(1))
                        if 1000 <= val <= 8000 and not (5000 <= val < 6000) and not (2020 <= val <= 2030):
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen: clean_items.append(x); seen.add(x)
                clean_items = clean_items[:9]

                # --- DETAY VERİLERİ (LEVEL, CS, GOLD) ---
                row_text = row.text.strip()
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row_text or "Zafer" in row_text else "lose"
                grade = calculate_grade(kda_text)

                # 1. Level Bulma
                level_stat = "Lvl ?"
                lvl_match = re.search(r"Lvl\.?\s*(\d+)", row_text)
                if lvl_match: level_stat = f"Lvl {lvl_match.group(1)}"

                # 2. CS Bulma
                cs_stat = "0 CS"
                cs_match = re.search(r"(\d+)\s*CS", row_text)
                if cs_match: cs_stat = f"{cs_match.group(1)} CS"

                # 3. Altın Bulma (Hatalı ID'leri önlemek için nokta kontrolü yapıyoruz)
                # Genelde altın "12.5k" formatında olur.
                gold_stat = "-"
                gold_match = re.search(r"(\d+\.\d+)k", row_text)
                if gold_match:
                    gold_stat = f"{gold_match.group(1)}k"
                else:
                    # Tam sayı ise ve mantıklı bir aralıktaysa (örn: 5k - 30k arası)
                    gold_int_match = re.search(r"\s(\d+)k", row_text)
                    if gold_int_match:
                        val = int(gold_int_match.group(1))
                        if 3 <= val <= 40: # ID numarası (0138) karışmasın diye limit koyduk
                            gold_stat = f"{val}k"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "level": level_stat,
                    "cs": cs_stat,
                    "gold": gold_stat
                })
                if len(matches_info) >= 5: break
            except: continue
        
        return {"summoner": summoner_name, "rank": rank_text, "icon": profile_icon, "matches": matches_info}

    except Exception as e:
        return {"error": str(e), "summoner": "Hata", "matches": []}

@app.route('/api/get-ragnar', methods=['GET'])
def get_all_users():
    all_data = []
    print("Veriler çekiliyor...")
    for url in URL_LISTESI:
        all_data.append(scrape_summoner(url))
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
