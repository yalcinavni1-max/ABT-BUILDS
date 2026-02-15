import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
import time
import random

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
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=3)
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- NOT HESAPLAMA ---
def calculate_grade(score):
    if score >= 4.0: return "S"
    elif score >= 3.0: return "A"
    elif score >= 2.5: return "B"
    elif score >= 2.0: return "C"
    elif score >= 1.0: return "D"
    else: return "F"

# --- SCRAPER ---
def scrape_summoner(url):
    # Bot koruması için bekleme ve İngilizce Header (QueueType'ı garanti yakalamak için)
    time.sleep(random.uniform(0.3, 0.8))
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
        summoner_name = "Sihirdar"
        try: summoner_name = soup.find("title").text.split("(")[0].strip().replace(" - League of Legends", "")
        except: pass

        rank_text = "Unranked"
        try:
            banner = soup.find("div", class_="bannerSubtitle")
            rank_text = banner.text.strip() if banner else soup.find("div", class_="league-tier").text.strip()
        except: pass

        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try:
            img = soup.find("div", class_="img").find("img")
            if img: profile_icon = "https:" + img.get("src")
        except: pass

        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # --- 1. OYUN TÜRÜ (SENİN KODUNDAKİ ÇALIŞAN MANTIK) ---
                queue_mode = "Normal"
                
                # A) Direkt QueueType Div'i
                q_div = row.find("div", class_="queueType")
                if q_div:
                    raw_q = q_div.text.strip()
                    if "Ranked Solo" in raw_q: queue_mode = "Solo/Duo"
                    elif "Ranked Flex" in raw_q: queue_mode = "Flex"
                    elif "ARAM" in raw_q: queue_mode = "ARAM"
                    elif "Arena" in raw_q: queue_mode = "Arena"
                    else: queue_mode = raw_q.split()[0]
                else:
                    # B) GameMode Div'i (Bazı sayfalarda buradadır)
                    g_div = row.find("div", class_="gameMode")
                    if g_div:
                        raw_g = g_div.text.strip()
                        if "Solo" in raw_g: queue_mode = "Solo/Duo"
                        elif "Flex" in raw_g: queue_mode = "Flex"
                        else: queue_mode = raw_g
                    else:
                        # C) Metin Taraması (Son Çare)
                        row_text = row.text.strip()
                        if "Ranked Solo" in row_text: queue_mode = "Solo/Duo"
                        elif "Ranked Flex" in row_text: queue_mode = "Flex"
                        elif "ARAM" in row_text: queue_mode = "ARAM"

                # --- 2. ŞAMPİYON BULMA ---
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
                if champ_key == "Poro":
                    for img in row.find_all("img"):
                        alt = img.get("alt", "")
                        if alt and len(alt) > 2 and alt not in ["Victory", "Defeat", "Role", "Item", "Gold"]:
                            champ_key = alt.replace(" ", "").replace("'", "").replace(".", "")
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # --- 3. İTEMLER (BENİM KODUMDAKİ ÇALIŞAN MANTIK) ---
                # src yerine str(img) kullanarak her türlü ID'yi yakalar
                items = []
                img_tags = row.find_all("img")
                for img in img_tags:
                    img_str = str(img)
                    if "champion" in img_str or "spell" in img_str or "tier" in img_str or "perk" in img_str: continue
                    candidates = re.findall(r"(\d{4})", img_str)
                    for num in candidates:
                        val = int(num)
                        if 1000 <= val <= 8000:
                            if 5000 <= val < 6000: continue
                            if 2020 <= val <= 2030: continue
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                clean_items = list(dict.fromkeys(items))[:9]

                # --- 4. TEMEL VERİLER ---
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                nums = re.findall(r"(\d+)", kda_text)
                kda_display = "Perfect"
                score_val = 99.0
                if len(nums) >= 3:
                    k, d, a = int(nums[0]), int(nums[1]), int(nums[2])
                    if d > 0:
                        score_val = (k + a) / d
                        kda_display = "{:.2f}".format(score_val)
                    else: score_val = 99.0
                grade = calculate_grade(score_val)

                # --- 5. CS / GÖRÜŞ SKORU (SUP KONTROLÜ) ---
                cs_val = 0
                cs_div = row.find("div", class_="minions")
                if cs_div:
                    m = re.search(r"(\d+)", cs_div.text)
                    if m: cs_val = int(m.group(1))
                else:
                    m = re.search(r"(\d+)\s*CS", row.text, re.IGNORECASE)
                    if m: cs_val = int(m.group(1))
                
                # EŞİK KONTROLÜ: 70
                # Varsayılan metin
                cs_stat = f"{cs_val} CS"

                if cs_val < 70:
                    # Minyon sayısı 70'in altındaysa Vision Score (veya Totem) ara
                    ward_score = "0"
                    
                    # Totem sayısını bulmaya çalış (League of Graphs'ta "wards" div'i içinde olabilir)
                    wards_div = row.find("div", class_="wards")
                    if wards_div:
                        wm = re.search(r"(\d+)", wards_div.text)
                        if wm: ward_score = wm.group(1)
                    
                    # Ekrana basılacak metni değiştir: "75 VS"
                    cs_stat = f"{ward_score} VS"

                # LP
                lp_text = ""
                lp_match = re.search(r"([+-]\d+)\s*LP", row.text)
                if lp_match: lp_text = f"{lp_match.group(1)} LP"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat, # Artık burası "145 CS" veya "25 VS" olabilir
                    "queue_mode": queue_mode, # Çalışan SoloQ mantığı
                    "lp_change": lp_text,
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
    print("Veriler çekiliyor...")
    for url in URL_LISTESI:
        all_data.append(scrape_summoner(url))
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
