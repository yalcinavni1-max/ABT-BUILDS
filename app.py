import re
import time
import random
import json
import os
import logging
# 'request' modülü EKLENDİ. Loglama EKLENDİ.
from flask import Flask, jsonify, send_from_directory, request 
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

# --- PROFESYONEL AYARLAR ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
logging.basicConfig(level=logging.INFO) # Render loglarında hatayı görmek için
logger = logging.getLogger(__name__)

VOTE_FILE = 'votes.json'

# --- GÜVENLİ VERİ YÖNETİCİSİ SINIFI ---
class VoteManager:
    def __init__(self, filename):
        self.filename = filename
        self.data = self.load()

    def load(self):
        if not os.path.exists(self.filename):
            return {}
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Veritabanı okuma hatası: {e}")
            return {} # Dosya bozuksa boş başlat

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Veritabanı kaydetme hatası: {e}")

    def add_vote(self, match_id, points):
        if match_id not in self.data:
            self.data[match_id] = {"total": 0, "count": 0}
        
        self.data[match_id]["total"] += int(points)
        self.data[match_id]["count"] += 1
        self.save()
        return self.get_average(match_id)

    def get_average(self, match_id):
        if match_id not in self.data or self.data[match_id]["count"] == 0:
            return {"average": "-", "count": 0}
        
        avg = self.data[match_id]["total"] / self.data[match_id]["count"]
        return {
            "average": round(avg, 1),
            "count": self.data[match_id]["count"]
        }

# Yöneticimizi başlatıyoruz
vote_manager = VoteManager(VOTE_FILE)

URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- API: OY VERME ---
@app.route('/api/vote', methods=['POST'])
def submit_vote():
    try:
        # Gelen veriyi kontrol et
        data = request.json
        if not data:
            return jsonify({"error": "Veri yok"}), 400

        match_id = data.get('match_id')
        points = data.get('points')

        logger.info(f"Oy Geldi -> ID: {match_id}, Puan: {points}")

        if not match_id or points is None:
            return jsonify({"error": "Eksik bilgi"}), 400

        # Oyu işle
        result = vote_manager.add_vote(match_id, points)
        return jsonify(result)

    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return jsonify({"error": str(e)}), 500

# --- YARDIMCI: GÜVENLİ ID OLUŞTURUCU ---
def generate_safe_id(text):
    # Türkçe karakterleri ve boşlukları temizler
    text = text.replace(" ", "").replace(":", "").replace("/", "")
    text = text.replace("ı", "i").replace("İ", "I").replace("ö", "o").replace("Ö", "O")
    text = text.replace("ü", "u").replace("Ü", "U").replace("ş", "s").replace("Ş", "S")
    text = text.replace("ğ", "g").replace("Ğ", "G").replace("ç", "c").replace("Ç", "C")
    return text

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- SCRAPER (VERİ ÇEKİCİ) ---
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

        summoner_name = "Bilinmeyen"
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

                # ŞAMPİYON
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            # Basit mapping
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
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

                # İTEMLER
                items = []
                img_tags = row.find_all("img")
                for img in img_tags:
                    img_str = str(img)
                    if any(x in img_str for x in ["champion", "spell", "tier", "perk"]): continue
                    candidates = re.findall(r"(\d{4})", img_str)
                    for num in candidates:
                        val = int(num)
                        if 1000 <= val <= 8000 and not (5000 <= val < 6000) and not (2020 <= val <= 2030):
                            items.append(f"{RIOT_CDN}/item/{val}.png")

                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                clean_items = clean_items[:9]

                kda_text = kda_div.text.strip()
                result = "lose"
                if "Victory" in row.text or "Zafer" in row.text: result = "win"
                
                # --- PUAN SİSTEMİ ENTEGRASYONU ---
                # Güvenli ID oluşturuyoruz
                raw_id = f"{summoner_name}-{champ_key}-{kda_text}"
                match_id = generate_safe_id(raw_id)
                
                # Veritabanından çek
                vote_data = vote_manager.get_average(match_id)

                matches_info.append({
                    "match_id": match_id,
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "user_score": vote_data["average"],
                    "vote_count": vote_data["count"]
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
        logger.error(f"Scrape Hatası: {e}")
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
