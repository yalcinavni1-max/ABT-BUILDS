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
        parts = time_str.split(':')
        if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except: return 1800
    return 0

# --- 2. ALTIN HESAPLAMA MOTORU (Minyon Tablosu + Pasif Gelir) ---
def calculate_gold_smart(kills, assists, cs, duration_seconds):
    # A) Başlangıç
    gold = 500
    
    # B) Minyon Geliri (Senin Tablona Göre Ortalama ~21g)
    # 234 minyon = ~4900 gold ise tanesi ortalama 20.9g eder. Biz düz 21 alıyoruz.
    gold += (cs * 21)
    
    # C) Skor Geliri
    gold += (kills * 300)
    gold += (assists * 150)
    
    # D) Pasif Gelir (Süre Bazlı)
    # 1:05 (65. saniye) sonra başlar, saniyede ~2.04 altın
    if duration_seconds > 65:
        passive_time = duration_seconds - 65
        gold += (passive_time * 2.04)
        
    return f"{round(gold / 1000, 1)}k"

# --- 3. NOT HESAPLAMA ---
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

# --- SCRAPER (SENİN ORİJİNAL ÇALIŞAN KODUN) ---
def scrape_summoner(url):
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # SENİN HEADERS AYARLARIN
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

                # --- ŞAMPİYON BULMA (ORİJİNAL MANTIK) ---
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            name_map = {
                                "wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                
                # Yedek Kontrol (Poro olmasın diye)
                if champ_key == "Poro":
                    imgs = row.find_all("img")
                    for img in imgs:
                        alt = img.get("alt", "")
                        if alt and len(alt) > 2 and alt not in ["Victory", "Defeat", "Role", "Item", "Gold"]:
                            champ_key = alt.replace(" ", "").replace("'", "").replace(".", "")
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # --- İTEMLER (SENİN ORİJİNAL MANTIĞIN) ---
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
                
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen: clean_items.append(x); seen.add(x)
                clean_items = clean_items[:9]

                # --- VERİ İŞLEME ---
                row_text = row.text.strip()
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                # 1. KDA ANALİZİ
                k, d, a = 0, 0, 0
                nums = re.findall(r"(\d+)", kda_text)
                kda_display = "Perfect"
                
                if len(nums) >= 3:
                    k, d, a = int(nums[0]), int(nums[1]), int(nums[2])
                    if d > 0:
                        score_val = (k + a) / d
                        kda_display = "{:.2f}".format(score_val)
                    else:
                        score_val = 99.0
                else:
                    score_val = 0.0
                    kda_display = "-"

                # 2. NOT
                grade = calculate_grade(score_val)

                # 3. CS (Minyon)
                cs_val = 0
                cs_match = re.search(r"(\d+)\s*CS", row_text, re.IGNORECASE)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                cs_stat = f"{cs_val} CS"

                # 4. SÜRE BULMA (Altın Hesabı İçin)
                duration_sec = 0
                dur_div = row.find("div", class_="gameDuration")
                if dur_div:
                    duration_sec = parse_duration_to_seconds(dur_div.text.strip())
                else:
                    time_match = re.search(r"(\d{1,2}:\d{2})", row_text)
                    if time_match: duration_sec = parse_duration_to_seconds(time_match.group(1))
                    else: duration_sec = 1500 # Bulamazsa 25 dk

                # 5. ALTIN HESAPLA (YENİ FORMÜL)
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
