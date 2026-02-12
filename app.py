import re
import time
import random
import logging
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Logları görelim
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- TAKİP LİSTESİ ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- NOT HESAPLAMA MOTORU (S, A, B...) ---
def calculate_grade(kda_text):
    try:
        if "Perfect" in kda_text or "Mükemmel" in kda_text:
            return "S"
            
        match = re.search(r"(\d+\.?\d*)", kda_text)
        if not match: return "-"
            
        kda = float(match.group(1))
        
        if kda >= 4.0: return "S"
        elif 3.0 <= kda < 4.0: return "A"
        elif 2.5 <= kda < 3.0: return "B"
        elif 2.0 <= kda < 2.5: return "C"
        elif 1.0 < kda < 2.0: return "D"
        else: return "F"
    except:
        return "-"

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- SCRAPER (GÜÇLENDİRİLMİŞ İNSAN MODU) ---
def scrape_summoner(url):
    # Bekleme süresi (Siteye yüklenmemek için)
    time.sleep(random.uniform(1.0, 2.0))
    
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # BURASI ÇOK ÖNEMLİ: Standart bir Windows Chrome tarayıcısı gibi görünüyoruz
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        
        # Eğer site bizi engellerse loga yaz
        if response.status_code != 200:
            logger.error(f"HATA: Site engelledi veya açılmadı. Kod: {response.status_code}")
            return {"error": "Site Erişimi Yok", "summoner": "Veri Alınamadı", "matches": []}

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Profil Bilgileri ---
        summoner_name = "Sihirdar"
        try: summoner_name = soup.find("title").text.split("(")[0].strip().replace(" - League of Legends", "")
        except: pass

        rank_text = "Unranked"
        try:
            banner = soup.find("div", class_="bannerSubtitle")
            if banner: rank_text = banner.text.strip()
            else:
                tier = soup.find("div", class_="league-tier")
                if tier: rank_text = tier.text.strip()
        except: pass

        profile_icon = f"{RIOT_CDN}/profileicon/29.png"
        try:
            img_div = soup.find("div", class_="img")
            if img_div and img_div.find("img"):
                profile_icon = "https:" + img_div.find("img").get("src")
        except: pass

        # --- Maçlar ---
        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                # KDA divi yoksa bu bir maç satırı değildir, geç
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # Şampiyon Bulma
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            # Bazı özel isim düzeltmeleri
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate", "leesin": "LeeSin", "kaisa": "Kaisa"}
                            champ_key = name_map.get(raw, raw.capitalize())
                            break
                final_champ_img = f"{RIOT_CDN}/champion/{champ_key}.png"

                # İtemler (Eski sağlam yöntem + yeni filtreler)
                items = []
                img_tags = row.find_all("img")
                for img in img_tags:
                    src = img.get("src", "")
                    # Gereksiz resimleri ele
                    if any(x in src for x in ["champion", "spell", "perk", "rune", "class", "role"]): continue
                    
                    # Sayı bul
                    m = re.search(r"(\d{4})", src)
                    if m:
                        val = int(m.group(1))
                        # Mantıklı item ID aralığı
                        if 1000 <= val <= 8000:
                            if 2020 <= val <= 2030: continue # Yıllar
                            if 5000 <= val < 6000: continue # Bazı rünler
                            items.append(f"{RIOT_CDN}/item/{val}.png")

                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                clean_items = clean_items[:9]

                # --- İstatistikler (CS & Gold & KDA) ---
                row_text = row.text.strip()
                
                # CS
                cs_stat = "0 CS"
                cs_m = re.search(r"(\d+)\s*CS", row_text)
                if cs_m: cs_stat = f"{cs_m.group(1)} CS"

                # Altın
                gold_stat = "0k"
                g_m = re.search(r"(\d+\.?\d*)\s*k", row_text)
                if g_m: gold_stat = f"{g_m.group(1)}k"

                # KDA Metni
                kda_text = kda_div.text.strip()
                
                # Sonuç
                result = "lose"
                if "Victory" in row_text or "Zafer" in row_text: result = "win"

                # Not Hesapla
                grade = calculate_grade(kda_text)

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "cs": cs_stat,
                    "gold": gold_stat,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade
                })
                if len(matches_info) >= 5: break
            except Exception as e:
                continue
        
        return {
            "summoner": summoner_name,
            "rank": rank_text,
            "icon": profile_icon,
            "matches": matches_info
        }

    except Exception as e:
        logger.error(f"GENEL HATA: {e}")
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
