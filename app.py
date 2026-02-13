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

# --- 1. SÜRE ÇEVİRİCİ ---
def parse_duration_to_seconds(time_str):
    try:
        # "25:12" formatını saniyeye çevirir
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3: # Saatli maçlar
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except:
        return 1800 # Hata olursa 30dk varsay
    return 0

# --- 2. ALTIN HESAPLAMA MOTORU (Senin Formülün) ---
def calculate_gold_smart(kills, assists, cs, duration_seconds):
    # A) Başlangıç Parası
    gold = 500 
    
    # B) Minyon Geliri (Attığın tabloya göre ortalama minyon değeri ~21g)
    gold += (cs * 21)
    
    # C) Skor Geliri
    gold += (kills * 300)
    gold += (assists * 150)
    
    # D) Pasif Gelir (Senin Formülün)
    # 1:05 (65 saniye) çıktıktan sonraki her saniye için ~2.04 altın
    if duration_seconds > 65:
        passive_time = duration_seconds - 65
        gold += (passive_time * 2.04)
        
    # Binlik formata çevir (Örn: 12.5k)
    return f"{round(gold / 1000, 1)}k"

# --- 3. KDA NOT HESAPLAMA ---
def calculate_grade(score):
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

# --- SCRAPER (ÇALIŞAN SÜRÜM) ---
def scrape_summoner(url):
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # BU HEADERS SENİN "ÇALIŞIYOR" DEDİĞİN SÜRÜMDÜR - DOKUNULMADI
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

        # MAÇLAR
        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # --- ŞAMPİYON BULMA (ORİJİNAL) ---
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").lower()
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"
                if champ_key == "Poro": # Yedek kontrol
                     for img in row.find_all("img"):
                        if img.get("alt") and len(img.get("alt")) > 2:
                            champ_key = img.get("alt").replace(" ", "").replace("'", "").replace(".", "")
                            break

                # --- İTEMLER (ORİJİNAL) ---
                items = []
                for img in row.find_all("img"):
                    src = img.get("src", "")
                    if any(x in src for x in ["champion", "spell", "tier", "perk"]): continue
                    m = re.search(r"(\d{4})", src)
                    if m:
                        val = int(m.group(1))
                        if 1000 <= val <= 8000:
                            if 5000 <= val < 6000: continue
                            if 2020 <= val <= 2030: continue
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                clean_items = list(dict.fromkeys(items))[:9]

                # --- VERİ İŞLEME VE HESAPLAMA ---
                row_text = row.text.strip()
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                # 1. KDA ANALİZİ
                k, d, a = 0, 0, 0
                nums = re.findall(r"(\d+)", kda_text)
                kda_score_val = 0.0
                kda_display = "Perfect"

                if len(nums) >= 3:
                    k, d, a = int(nums[0]), int(nums[1]), int(nums[2])
                    if d > 0:
                        kda_score_val = (k + a) / d
                        kda_display = "{:.2f}".format(kda_score_val)
                    else:
                        kda_score_val = 99.0
                
                # 2. NOT HESAPLA
                grade = calculate_grade(kda_score_val)

                # 3. CS (Minyon) BULMA - (Destekler için daha hassas regex)
                cs_val = 0
                cs_stat = "0 CS"
                cs_match = re.search(r"(\d+)\s*CS", row_text, re.IGNORECASE)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                    cs_stat = f"{cs_val} CS"

                # 4. SÜRE BULMA
                duration_sec = 0
                # Sitede süreyi bulmak için önce "gameDuration" classına bakarız
                dur_div = row.find("div", class_="gameDuration")
                if dur_div:
                    duration_sec = parse_duration_to_seconds(dur_div.text.strip())
                else:
                    # Bulamazsa metin içindeki saat formatını (25:12) ararız
                    time_match = re.search(r"(\d{1,2}:\d{2})", row_text)
                    if time_match:
                         duration_sec = parse_duration_to_seconds(time_match.group(1))
                    else:
                        duration_sec = 1500 # Bulamazsa 25 dk say

                # 5. ALTIN HESAPLA (Senin Özel Formülün)
                gold_stat = calculate_gold_smart(k, a, cs_val, duration_sec)

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat,
                    "kda_score": kda_display
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
