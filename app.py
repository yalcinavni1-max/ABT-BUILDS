import re
import time
import random
import json
import os
import logging
from flask import Flask, jsonify, send_from_directory, request
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VOTE_FILE = 'votes.json'

# --- GÜVENLİ OYLAMA YÖNETİCİSİ ---
class VoteManager:
    def __init__(self, filename):
        self.filename = filename

    def load_safe(self):
        if not os.path.exists(self.filename): return {}
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except Exception as e:
            logger.error(f"Veritabanı okuma hatası: {e}")
            return {}

    def save_safe(self, data):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except: pass

    def add_vote(self, match_id, points):
        data = self.load_safe()
        if match_id not in data: data[match_id] = {"total": 0, "count": 0}
        data[match_id]["total"] += int(points)
        data[match_id]["count"] += 1
        self.save_safe(data)
        return self.calculate_avg(data[match_id])

    def get_stats(self, match_id):
        data = self.load_safe()
        return self.calculate_avg(data.get(match_id, {"total":0, "count":0}))

    def calculate_avg(self, record):
        if record["count"] == 0: return {"average": "-", "count": 0}
        return {"average": round(record["total"] / record["count"], 1), "count": record["count"]}

vote_manager = VoteManager(VOTE_FILE)

URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/vote', methods=['POST'])
def submit_vote():
    try:
        data = request.json
        match_id = data.get('match_id')
        points = data.get('points')
        if not match_id or points is None: return jsonify({"error": "Eksik bilgi"}), 400
        result = vote_manager.add_vote(match_id, points)
        return jsonify(result)
    except Exception as e: return jsonify({"error": str(e)}), 500

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- SCRAPER ---
def scrape_summoner(url):
    time.sleep(random.uniform(0.5, 1.5))
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Profil Bilgileri
        summoner_name = "Sihirdar"
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

        # Maçlar
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
                items_div = row.find("div", class_="items")
                if items_div:
                    for img in items_div.find_all("img"):
                        src = img.get("src", "")
                        if any(x in src for x in ["champion", "spell", "perk"]): continue
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

                # --- YENİ EKLENEN KISIM: CS VE ALTIN ---
                row_text = row.text.strip() # Satırın tüm yazısını al
                
                # CS Bulma (Örn: "185 CS")
                cs_stat = "0 CS"
                cs_match = re.search(r"(\d+)\s*CS", row_text)
                if cs_match:
                    cs_stat = f"{cs_match.group(1)} CS"

                # Altın Bulma (Örn: "12.4k")
                gold_stat = "0k"
                gold_match = re.search(r"(\d+\.?\d*)\s*k", row_text)
                if gold_match:
                    gold_stat = f"{gold_match.group(1)}k"

                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row_text or "Zafer" in row_text else "lose"

                # Puan Çekme
                raw_id = f"{summoner_name}-{champ_key}-{kda_text}".replace(" ", "").replace("/", "").replace(":", "")
                stats = vote_manager.get_stats(raw_id)

                matches_info.append({
                    "match_id": raw_id,
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "cs": cs_stat,      # Yeni Veri
                    "gold": gold_stat,  # Yeni Veri
                    "img": final_champ_img,
                    "items": clean_items,
                    "user_score": stats["average"],
                    "vote_count": stats["count"]
                })
                if len(matches_info) >= 5: break
            except: continue
        
        return {"summoner": summoner_name, "rank": rank_text, "icon": profile_icon, "matches": matches_info}

    except Exception as e:
        logger.error(f"HATA: {e}")
        return {"error": str(e), "summoner": "Hata", "matches": []}

@app.route('/api/get-ragnar', methods=['GET'])
def get_all_users():
    all_data = []
    for url in URL_LISTESI:
        all_data.append(scrape_summoner(url))
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
