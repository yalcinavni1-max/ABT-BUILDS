import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
import os

# Render için gerekli ayar (Siteyi buradan sunacak)
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

HEDEF_URL = "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138"

# --- 1. SİTEYİ AÇAN KOD ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- 2. RAGNAR V33 (ZAMAN YOLCUSU) ---
def get_latest_ddragon_version():
    try:
        # Riot'tan en güncel sürümü çek (16.3.1 gibi)
        response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5)
        if response.status_code == 200:
            versions = response.json()
            return versions[0]
    except: pass
    return "14.3.1" # Yedek

@app.route('/api/get-ragnar', methods=['GET'])
def get_ragnar_data():
    current_version = get_latest_ddragon_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{current_version}/img"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(HEDEF_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # LEVEL / RANK
        rank_text = "Level Bilgisi Yok"
        try:
            banner_sub = soup.find("div", class_="bannerSubtitle")
            if banner_sub: rank_text = banner_sub.text.strip()
            else:
                tier = soup.find("div", class_="league-tier")
                if tier: rank_text = tier.text.strip()
        except: pass

        # Profil Resmi
        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try:
            img = soup.find("div", class_="img").find("img")
            if img: profile_icon = "https:" + img.get("src")
        except: pass

        # MAÇLAR
        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # ŞAMPİYON
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            name_map = {
                                "wukong": "MonkeyKing", "renata": "Renata", "fiddlesticks": "Fiddlesticks",
                                "kais'a": "Kaisa", "kaisa": "Kaisa", "leesin": "LeeSin", "belveth": "Belveth",
                                "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo",
                                "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao",
                                "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol",
                                "twistedfate": "TwistedFate"
                            }
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                
                if champ_key == "Poro":
                    imgs = row.find_all("img")
                    for img in imgs:
                        alt = img.get("alt", "")
                        if alt and len(alt) > 2 and alt not in ["Victory", "Defeat", "Role", "Item", "Gold"]:
                            champ_key = alt.replace(" ", "").replace("'", "").replace(".", "")
                            break

                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # İTEMLER (V33 MANTIĞI - Sen bunu sevmiştin)
                items = []
                img_tags = row.find_all("img")
                
                for img in img_tags:
                    img_str = str(img)
                    
                    if "champion" in img_str or "spell" in img_str or "tier" in img_str or "perk" in img_str:
                        continue
                    
                    candidates = re.findall(r"(\d{4})", img_str)
                    
                    for num in candidates:
                        val = int(num)
                        # V33 Filtreleri
                        if 2020 <= val <= 2030: continue # Yılları at
                        if 5000 <= val < 6000: continue # Rünleri at
                        
                        if 1000 <= val <= 8000:
                            items.append(f"{RIOT_CDN}/item/{val}.png")

                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                clean_items = clean_items[:7]

                kda_text = kda_div.text.strip()
                result = "lose"
                if "Victory" in row.text or "Zafer" in row.text: result = "win"
                
                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items
                })

                if len(matches_info) >= 5: break

            except: continue
        
        return jsonify({
            "summoner": "Ragnar Lothbrok #0138",
            "rank": rank_text,
            "icon": profile_icon,
            "matches": matches_info
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    # Render'da çalışması için host='0.0.0.0' şart
    app.run(host='0.0.0.0', port=5000)
