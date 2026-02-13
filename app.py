import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- TAKİP EDİLECEK HESAPLAR LİSTESİ ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- SÜRE AYRIŞTIRICI (Dakika:Saniye -> Toplam Saniye) ---
def parse_game_duration(duration_str):
    try:
        # "25:12" formatını saniyeye çevirir
        parts = duration_str.split(':')
        if len(parts) == 2: # Dakika:Saniye
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3: # Saat:Dakika:Saniye (Uzun maçlar)
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except:
        return 1800 # Hata olursa ortalama 30 dk (1800 sn) döndür
    return 0

# --- 1. ALTIN HESAPLAMA MOTORU (GELİŞMİŞ) ---
def estimate_gold(kills, deaths, assists, cs, duration_seconds):
    # 1. Başlangıç Altını
    gold = 500 
    
    # 2. Pasif Altın Geliri (Senin Formülün)
    # 1:05 (65. saniye) sonra başlar, saniyede 2 altın (10 saniyede 20)
    if duration_seconds > 65:
        passive_gold = (duration_seconds - 65) * 2.04 # Oyunun gerçek değeri 2.04'tür ama 2 de yakındır
        gold += passive_gold
        
    # 3. Aksiyon Gelirleri
    gold += (kills * 300)
    gold += (assists * 150)
    gold += (cs * 21) # Ortalama minyon değeri
    
    # Küsüratı atıp 'k' formatına çevir
    return f"{round(gold / 1000, 1)}k"

# --- 2. LEVEL HESAPLAMA MOTORU ---
def estimate_level(item_count):
    if item_count >= 5: return "17-18"
    elif item_count == 4: return "15-16"
    elif item_count == 3: return "12-14"
    elif item_count == 2: return "9-11"
    else: return "6-9"

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
    
    # SENİN ÇALIŞAN HEADERS AYARLARIN
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
            banner_sub = soup.find("div", class_="bannerSubtitle")
            if banner_sub: rank_text = banner_sub.text.strip()
            else:
                tier = soup.find("div", class_="league-tier")
                if tier: rank_text = tier.text.strip()
        except: pass

        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try: profile_icon = "https:" + soup.find("div", class_="img").find("img").get("src")
        except: pass

        # MAÇLAR
        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # Şampiyon
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"
                if champ_key == "Poro":
                    for img in row.find_all("img"):
                        if img.get("alt") and len(img.get("alt")) > 2:
                            champ_key = img.get("alt").replace(" ", "").replace("'", "").replace(".", "")
                            break

                # İtemler
                items = []
                for img in row.find_all("img"):
                    src = img.get("src", "")
                    if any(x in src for x in ["champion", "spell", "tier", "perk"]): continue
                    m = re.search(r"(\d{4})", src)
                    if m:
                        val = int(m.group(1))
                        if 1000 <= val <= 8000 and not (5000 <= val < 6000) and not (2020 <= val <= 2030):
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                clean_items = list(dict.fromkeys(items))[:9]

                # --- VERİLERİ İŞLEME ---
                row_text = row.text.strip()
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                # 1. NOT
                grade = calculate_grade(kda_text)

                # 2. CS (Minyon)
                cs_val = 0
                cs_match = re.search(r"(\d+)\s*CS", row_text)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                cs_stat = f"{cs_val} CS"

                # 3. KDA (Sayılar)
                k_num, d_num, a_num = 0, 0, 0
                kda_nums = re.findall(r"(\d+)", kda_text)
                if len(kda_nums) >= 3:
                    k_num, d_num, a_num = int(kda_nums[0]), int(kda_nums[1]), int(kda_nums[2])
                    kda_disp = "Perfect" if d_num == 0 else "{:.2f}".format((k_num+a_num)/d_num)
                else:
                    kda_disp = "-"

                # 4. SÜRE ÇEKME VE ALTIN HESAPLAMA (YENİ)
                # Sitede süre genelde "gameDuration" class'lı bir div içindedir
                duration_sec = 0
                duration_div = row.find("div", class_="gameDuration")
                if duration_div:
                    duration_sec = parse_game_duration(duration_div.text.strip())
                else:
                    # Div yoksa text içinde süre formatı ara (örn: 25:12)
                    time_match = re.search(r"(\d{1,2}:\d{2})", row_text)
                    if time_match:
                         duration_sec = parse_game_duration(time_match.group(1))
                    else:
                        duration_sec = 1500 # Bulamazsa ortalama 25 dk say

                # Senin Formülünle Altın Hesabı:
                gold_stat = estimate_gold(k_num, d_num, a_num, cs_val, duration_sec)

                # 5. Level Tahmini
                level_stat = f"Lvl {estimate_level(len(clean_items))}"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat,
                    "kda_score": kda_disp
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
