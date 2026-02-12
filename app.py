import re
import time
import random
import json
import os
from flask import Flask, jsonify, send_from_directory, request
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- 1. OYLAMA SİSTEMİ ALTYAPISI (YENİ) ---
VOTE_FILE = 'votes.json'

def load_votes():
    if not os.path.exists(VOTE_FILE):
        return {}
    try:
        with open(VOTE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_votes(votes):
    with open(VOTE_FILE, 'w') as f:
        json.dump(votes, f)

votes_db = load_votes()

# --- TAKİP EDİLECEK HESAPLAR LİSTESİ ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- 2. OY VERME API'si (YENİ) ---
@app.route('/api/vote', methods=['POST'])
def submit_vote():
    data = request.json
    match_id = data.get('match_id')
    points = data.get('points')

    if not match_id or points is None:
        return jsonify({"error": "Eksik bilgi"}), 400

    if match_id not in votes_db:
        votes_db[match_id] = {"total": 0, "count": 0}

    votes_db[match_id]["total"] += int(points)
    votes_db[match_id]["count"] += 1
    
    save_votes(votes_db)

    avg = votes_db[match_id]["total"] / votes_db[match_id]["count"]
    return jsonify({"average": round(avg, 1), "count": votes_db[match_id]["count"]})

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- TEK BİR KULLANICIYI ÇEKEN FONKSİYON (SENİN KODUN) ---
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

        # 1. İSİM VE RANK
        summoner_name = "Bilinmeyen Sihirdar"
        try:
            title = soup.find("title").text
            summoner_name = title.split("(")[0].strip().replace(" - League of Legends", "")
        except: pass

        rank_text = "Unranked"
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

        # 2. MAÇLAR
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

                # İTEMLER (SENİN MANTIĞIN - DOKUNMADIK)
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
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                clean_items = clean_items[:9] # Senin ayarın: 9 İtem

                kda_text = kda_div.text.strip()
                result = "lose"
                if "Victory" in row.text or "Zafer" in row.text: result = "win"
                
                # --- 3. PUAN VERİSİNİ EKLEME (YENİ) ---
                match_id = f"{summoner_name}-{champ_key}-{kda_text}".replace(" ", "")
                current_score = "-"
                vote_count = 0
                
                if match_id in votes_db:
                    total = votes_db[match_id]["total"]
                    count = votes_db[match_id]["count"]
                    if count > 0:
                        current_score = round(total / count, 1)
                        vote_count = count

                matches_info.append({
                    "match_id": match_id,  # Frontend için ID
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "user_score": current_score, # Puan
                    "vote_count": vote_count     # Oy sayısı
                })
                if len(matches_info) >= 5: break
            except: continue
            
        return {
            "summoner": summoner_name,
            "rank": rank_text,
            "icon": profile_icon,
            "matches": matches_info
        }

    except Exception as e:
        return {"error": str(e), "summoner": "Hata", "matches": []}

@app.route('/api/get-ragnar', methods=['GET'])
def get_all_users():
    all_data = []
    print("Veriler çekiliyor...")
    for url in URL_LISTESI:
        data = scrape_summoner(url)
        all_data.append(data)
    
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
