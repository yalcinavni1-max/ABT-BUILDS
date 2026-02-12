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
# Sitede altın yazmadığı için bunu biz hesaplıyoruz
def estimate_gold(kills, deaths, assists, cs):
    # Temel Altın: 500
    # Kill: 300
    # Assist: 150 (Ortalama)
    # Minyon: 21 (Ortalama)
    # Pasif Gelir (Süre bazlı): Yaklaşık 3000-4000 (Minyon sayısıyla orantılı artar)
    
    estimated = 500 + (kills * 300) + (assists * 150) + (cs * 21) + (cs * 15)
    
    # Binlik formata çevir (Örn: 12500 -> 12.5k)
    return f"{round(estimated / 1000, 1)}k"

# --- 2. LEVEL HESAPLAMA MOTORU ---
# Sitede level yazmadığı için item sayısından buluyoruz
def estimate_level(item_count, cs):
    if item_count >= 5: return "17-18"
    elif item_count == 4: return "14-16"
    elif item_count == 3: return "11-13"
    elif item_count == 2: return "9-11"
    elif item_count == 1: return "6-8"
    else: return "1-5"

# --- 3. NOT HESAPLAMA ---
def calculate_grade(kda_text):
    try:
        if "Perfect" in kda_text or "Mükemmel" in kda_text: return "S"
        nums = re.findall(r"(\d+)", kda_text)
        if len(nums) >= 3:
            k, d, a = float(nums[0]), float(nums[1]), float(nums[2])
            score = (k + a) / d if d > 0 else 99
            
            if score >= 4.0: return "S"
            elif score >= 3.0: return "A"
            elif score >= 2.5: return "B"
            elif score >= 2.0: return "C"
            elif score >= 1.0: return "D"
            else: return "F"
    except: pass
    return "-"

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
                        if 1000 <= val <= 8000:
                            if 5000 <= val < 6000: continue
                            if 2020 <= val <= 2030: continue
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen: clean_items.append(x); seen.add(x)
                clean_items = clean_items[:9]

                # --- VERİ İŞLEME VE HESAPLAMA ---
                row_text = row.text.strip().replace('\n', ' ') # Satırı temizle
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"
                grade = calculate_grade(kda_text)

                # 1. CS (Minyon) BULMA
                cs_val = 0
                cs_stat = "0 CS"
                # Regex: Sayı + CS (Örn: 195 CS)
                cs_match = re.search(r"(\d+)\s*CS", row_text)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                    cs_stat = f"{cs_val} CS"
                
                # 2. KDA SAYILARINI AYRIŞTIR (Altın hesabı için)
                k_num, d_num, a_num = 0, 0, 0
                kda_nums = re.findall(r"(\d+)", kda_text)
                if len(kda_nums) >= 3:
                    k_num = int(kda_nums[0])
                    d_num = int(kda_nums[1])
                    a_num = int(kda_nums[2])

                # 3. ALTIN HESAPLA (Sitede yazmadığı için hesaplıyoruz)
                gold_stat = estimate_gold(k_num, d_num, a_num, cs_val)

                # 4. LEVEL HESAPLA (Sitede yazmadığı için itemlerden buluyoruz)
                # İtem sayısı + Farm durumuna göre tahmin
                raw_level = estimate_level(len(clean_items), cs_val)
                level_stat = f"Lvl {raw_level}"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat,  # Hesaplanan Altın
                    "level": level_stat # Hesaplanan Level
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
