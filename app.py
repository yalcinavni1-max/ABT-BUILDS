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

def calculate_grade(score):
    if score >= 4.0: return "S"
    elif score >= 3.0: return "A"
    elif score >= 2.5: return "B"
    elif score >= 2.0: return "C"
    elif score >= 1.0: return "D"
    else: return "F"

def scrape_summoner(url):
    time.sleep(random.uniform(0.1, 0.4)) # Hızlandırıldı
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # Dili İNGİLİZCE (en-US) zorluyoruz. Bu sayede "Ranked Solo" garantilenir.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=1.0" 
    }
    
    try:
        # URL 'tr' olsa bile header ile İngilizce içerik isteyeceğiz
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

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

                # --- 1. OYUN TÜRÜ (İNGİLİZCE TARAMA) ---
                queue_mode = "Normal"
                full_text = row.text.strip() # Tüm satır metni
                
                # Header sayesinde artık Türkçe aramaya gerek yok.
                # League of Graphs İngilizce terimleri: "Ranked Solo/Duo", "Ranked Flex"
                
                if "Ranked Solo" in full_text: queue_mode = "Solo/Duo"
                elif "Ranked Flex" in full_text: queue_mode = "Flex"
                
                # Eğer dereceli değilse bu maçı HİÇ alma, döngüyü atla
                if queue_mode not in ["Solo/Duo", "Flex"]:
                    continue

                # --- 2. ŞAMPİYON ---
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

                # --- 3. İTEMLER ---
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

                # --- 4. VERİLER ---
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in full_text or "Zafer" in full_text else "lose"

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

                # CS
                cs_val = 0
                cs_div = row.find("div", class_="minions")
                if cs_div:
                    m = re.search(r"(\d+)", cs_div.text)
                    if m: cs_val = int(m.group(1))
                else:
                    m = re.search(r"(\d+)\s*CS", full_text, re.IGNORECASE)
                    if m: cs_val = int(m.group(1))
                cs_stat = f"{cs_val} CS"

                # LP
                lp_text = ""
                lp_match = re.search(r"([+-]\d+)\s*LP", full_text)
                if lp_match: lp_text = f"{lp_match.group(1)} LP"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "queue_mode": queue_mode,
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
