import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- TAKİP EDİLECEK HESAPLAR ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- 1. ALTIN HESAPLAMA MOTORU ---
def estimate_gold(kills, deaths, assists, cs):
    # Basit bir simülasyon:
    # Base: 500, Kill: 300, Assist: 150, CS: 21, Pasif: ~3000
    base_passive = 3000
    gold = 500 + base_passive + (kills * 300) + (assists * 150) + (cs * 21)
    return f"{round(gold / 1000, 1)}k"

# --- 2. NOT HESAPLAMA (Grade) ---
def calculate_grade(score):
    if score == 99.0: return "S" # Perfect KDA
    
    if score >= 4.0: return "S"
    elif score >= 3.0: return "A"
    elif score >= 2.5: return "B"
    elif score >= 2.0: return "C"
    elif score >= 1.0: return "D"
    else: return "F"

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- SCRAPER ---
def scrape_summoner(url):
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # İsim ve Rank
        summoner_name = "Bilinmeyen Sihirdar"
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
                img_tags = row.find_all("img")
                for img in img_tags:
                    src = img.get("src", "")
                    if any(x in src for x in ["champion", "spell", "tier", "perk"]): continue
                    m = re.search(r"(\d{4})", src)
                    if m:
                        val = int(m.group(1))
                        if 1000 <= val <= 8000 and not (5000 <= val < 6000) and not (2020 <= val <= 2030):
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                clean_items = list(dict.fromkeys(items))[:9] # Duplicate önle

                # --- VERİ İŞLEME ---
                row_text = row.text.strip()
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                # 1. KDA ANALİZİ (Sayıları Çek)
                k, d, a = 0, 0, 0
                nums = re.findall(r"(\d+)", kda_text)
                kda_score_val = 0.0
                kda_display = "0.00"

                if len(nums) >= 3:
                    k = float(nums[0])
                    d = float(nums[1])
                    a = float(nums[2])
                    
                    # (Kill + Asist) / Death
                    if d == 0:
                        kda_score_val = 99.0
                        kda_display = "Perfect"
                    else:
                        kda_score_val = (k + a) / d
                        kda_display = "{:.2f}".format(kda_score_val)
                
                # 2. NOT HESAPLA
                grade = calculate_grade(kda_score_val)

                # 3. CS (Minyon)
                cs_val = 0
                cs_stat = "0 CS"
                cs_match = re.search(r"(\d+)\s*CS", row_text)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                    cs_stat = f"{cs_val} CS"

                # 4. ALTIN TAHMİNİ
                gold_stat = estimate_gold(k, d, a, cs_val)

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat,
                    "kda_score": kda_display # Yeni hesaplanan veri
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
