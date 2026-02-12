import re
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

# --- ALTIN HESAPLAMA MOTORU (SİMÜLASYON) ---
def estimate_gold(kills, deaths, assists, cs, time_minutes=30):
    # LoL Ortalama Altın Değerleri:
    # Kill: ~300g (Bounty hariç ortalama)
    # Assist: ~150g
    # CS (Minyon): ~20g (Melee, Caster, Cannon ortalaması)
    # Pasif Altın: Dakikada ~120g (Oyun ortası)
    # Başlangıç: 500g
    
    gold = 500 # Başlangıç
    gold += kills * 300
    gold += assists * 100 # Asist değeri biraz düşüktür
    gold += cs * 21 # Ortalama minyon değeri
    gold += time_minutes * 100 # Pasif gelir tahmini
    
    # 1000'e bölüp 'k' formatına çevir (Örn: 12.4k)
    return f"{round(gold / 1000, 1)}k"

# --- LEVEL TAHMİN MOTORU ---
def estimate_level(item_count, cs):
    # İtem sayısına ve farma göre level tahmini
    if item_count >= 5 or cs > 200: return "16-18"
    elif item_count == 4 or cs > 150: return "14-16"
    elif item_count == 3 or cs > 100: return "11-13"
    elif item_count == 2: return "9-11"
    else: return "6-9"

# --- NOT HESAPLAMA ---
def calculate_grade(kda_text):
    try:
        if "Perfect" in kda_text or "Mükemmel" in kda_text: return "S"
        numbers = re.findall(r"(\d+)", kda_text)
        if len(numbers) >= 3:
            k = float(numbers[0])
            d = float(numbers[1])
            a = float(numbers[2])
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
        summoner_name = "Bilinmeyen"
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
                        if 1000 <= val <= 8000 and not (2020 <= val <= 2030) and not (5000 <= val < 6000):
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen: clean_items.append(x); seen.add(x)
                clean_items = clean_items[:9]

                # --- VERİ ANALİZİ VE TAHMİN ---
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"
                grade = calculate_grade(kda_text)

                # CS Çekme
                cs_val = 0
                cs_stat = "0 CS"
                cs_match = re.search(r"(\d+)\s*CS", row.text)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                    cs_stat = f"{cs_val} CS"

                # KDA Sayılarını Ayrıştır (Altın hesabı için lazım)
                kills, deaths, assists = 0, 0, 0
                kda_nums = re.findall(r"(\d+)", kda_text)
                if len(kda_nums) >= 3:
                    kills = int(kda_nums[0])
                    deaths = int(kda_nums[1])
                    assists = int(kda_nums[2])

                # 1. AKILLI ALTIN TAHMİNİ
                # Sitede yazmıyorsa biz hesaplarız!
                gold_stat = estimate_gold(kills, deaths, assists, cs_val)

                # 2. AKILLI LEVEL TAHMİNİ
                # Sitede yazmıyorsa item sayısından tahmin ederiz!
                level_stat = estimate_level(len(clean_items), cs_val)

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "level": f"Lvl {level_stat}",
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
