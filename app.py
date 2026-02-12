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

# --- AYARLAR ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Logları açalım ki Render panelinde ne olduğunu görelim
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VOTE_FILE = 'votes.json'

# --- PROFESYONEL VERİ YÖNETİCİSİ ---
class VoteManager:
    def __init__(self, filename):
        self.filename = filename
        # Başlangıçta dosyayı kontrol et, yoksa yarat
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Dosya yoksa veya bozuksa sıfırdan oluşturur."""
        if not os.path.exists(self.filename):
            self._write_empty()
            return

        # Dosya sağlam mı diye test et
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content: # Dosya boşsa
                    self._write_empty()
                else:
                    json.loads(content) # JSON geçerli mi?
        except Exception as e:
            logger.warning(f"Veritabanı bozuk, sıfırlanıyor: {e}")
            self._write_empty()

    def _write_empty(self):
        """Temiz bir JSON dosyası oluşturur."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        except Exception as e:
            logger.error(f"Dosya oluşturma hatası: {e}")

    def load(self):
        """Dosyayı her seferinde diskten okur (En güncel veri için)."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            # Okuyamazsa sıfırla ve boş döndür
            self._write_empty()
            return {}

    def save(self, data):
        """Veriyi diske yazar."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Kayıt hatası: {e}")

    def add_vote(self, match_id, points):
        # 1. En güncel veriyi çek
        data = self.load()
        
        # 2. Kayıt yoksa oluştur
        if match_id not in data:
            data[match_id] = {"total": 0, "count": 0}
        
        # 3. Puanı ekle
        data[match_id]["total"] += int(points)
        data[match_id]["count"] += 1
        
        # 4. Hemen kaydet
        self.save(data)
        
        # 5. Yeni ortalamayı döndür
        return self.calculate_average(data[match_id])

    def get_stats(self, match_id):
        data = self.load()
        if match_id in data:
            return self.calculate_average(data[match_id])
        return {"average": "-", "count": 0}

    def calculate_average(self, record):
        if record["count"] == 0:
            return {"average": "-", "count": 0}
        avg = record["total"] / record["count"]
        return {
            "average": round(avg, 1),
            "count": record["count"]
        }

# Yöneticiyi Başlat
vote_manager = VoteManager(VOTE_FILE)

# --- TAKİP LİSTESİ ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- OY VERME API'si ---
@app.route('/api/vote', methods=['POST'])
def submit_vote():
    try:
        data = request.json
        match_id = data.get('match_id')
        points = data.get('points')

        if not match_id or points is None:
            return jsonify({"error": "Eksik bilgi"}), 400

        # Yöneticiye işi devret
        result = vote_manager.add_vote(match_id, points)
        
        logger.info(f"OY VERİLDİ: {match_id} -> {points} Puan. Yeni Ort: {result['average']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"API Hatası: {e}")
        return jsonify({"error": str(e)}), 500

# --- SCRAPER YARDIMCILARI ---
def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

def generate_safe_id(text):
    # ID oluştururken sorun çıkaran karakterleri temizle
    return text.replace(" ", "").replace("/", "").replace(":", "")

# --- VERİ ÇEKME FONKSİYONU (GOOGLEBOT MODU) ---
def scrape_summoner(url):
    time.sleep(random.uniform(0.5, 1.5)) # Hızlı cevap için süreyi azalttım
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # İsim ve Rank
        summoner_name = "Sihirdar"
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

        # Maçlar
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
                
                if champ_key == "Poro":
                    imgs = row.find_all("img")
                    for img in imgs:
                        alt = img.get("alt", "")
                        if alt and len(alt) > 2 and alt not in ["Victory", "Defeat", "Role", "Item", "Gold"]:
                            champ_key = alt.replace(" ", "").replace("'", "").replace(".", "")
                            break
                
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # İtemler (Googlebot moduyla)
                items = []
                items_container = row.find("div", class_="items")
                if items_container:
                    images = items_container.find_all("img")
                    for img in images:
                        src = img.get("src") or img.get("data-original") or ""
                        if not src: continue
                        if any(x in src for x in ["champion", "spell", "perk", "rune", "summoner", "class"]): continue
                        match = re.search(r"(\d{4})", src)
                        if match:
                            val = int(match.group(1))
                            if 1000 <= val <= 8000:
                                if 2020 <= val <= 2030: continue
                                if 5000 <= val < 6000: continue
                                items.append(f"{RIOT_CDN}/item/{val}.png")

                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                clean_items = clean_items[:7] # 7 item

                kda_text = kda_div.text.strip()
                result = "lose"
                if "Victory" in row.text or "Zafer" in row.text: result = "win"
                
                # --- PUANLARI AL (GÜNCEL) ---
                # ID oluştururken Türkçe karakterleri temizle
                raw_id = f"{summoner_name}-{champ_key}-{kda_text}"
                match_id = generate_safe_id(raw_id)
                
                # Dosyadan anlık veriyi çek
                stats = vote_manager.get_stats(match_id)

                matches_info.append({
                    "match_id": match_id,
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "user_score": stats["average"],
                    "vote_count": stats["count"]
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
