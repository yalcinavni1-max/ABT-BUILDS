import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- TAKİP EDİLECEK HESAPLAR LİSTESİ ---
URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# --- GELİŞMİŞ NOT HESAPLAMA MOTORU ---
def calculate_grade(kda_text):
    try:
        # 1. "Perfect" (Hiç ölmemiş) kontrolü
        if "Perfect" in kda_text or "Mükemmel" in kda_text:
            return "S"
            
        # 2. Metnin içindeki sayıları bul (Örn: "3 / 9 / 15" -> [3, 9, 15])
        # Regex ile string içindeki tüm sayıları liste olarak alıyoruz
        numbers = re.findall(r"(\d+)", kda_text)
        
        kda_score = 0.0
        
        # Eğer en az 3 sayı bulduysak (Kill, Death, Assist) formülü uygula
        if len(numbers) >= 3:
            kills = float(numbers[0])
            deaths = float(numbers[1])
            assists = float(numbers[2])
            
            # KDA Formülü: (Kill + Asist) / Ölüm
            if deaths == 0:
                kda_score = 99.0 # Ölüm 0 ise skor sonsuzdur, direkt S alır
            else:
                kda_score = (kills + assists) / deaths
                
        else:
            # Eğer 3 sayı bulamazsa (belki site "3.50:1" formatında vermiştir)
            # Eski yöntemi yedek olarak kullanalım
            match = re.search(r"(\d+\.?\d*)", kda_text)
            if match:
                kda_score = float(match.group(1))
            else:
                return "-"

        # 3. Hesaplanan skora göre not ver
        if kda_score >= 4.0: return "S"       # 4 ve üzeri
        elif 3.0 <= kda_score < 4.0: return "A" # 3-4 arası
        elif 2.5 <= kda_score < 3.0: return "B" # 2.5-3 arası
        elif 2.0 <= kda_score < 2.5: return "C" # 2-2.5 arası
        elif 1.0 < kda_score < 2.0: return "D"  # 1-2 arası
        else: return "F"                        # 1 ve altı
        
    except:
        return "-"

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- KULLANICI ÇEKEN FONKSİYON ---
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

                # İTEMLER
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
                clean_items = clean_items[:9]

                kda_text = kda_div.text.strip()
                result = "lose"
                if "Victory" in row.text or "Zafer" in row.text: result = "win"
                
                # --- YENİ EKLENEN KISIMLAR ---
                
                # 1. NOT HESAPLAMA (DÜZELTİLDİ: (K+A)/D formülü)
                grade = calculate_grade(kda_text)

                # 2. CS ve ALTIN ÇEKME
                row_text = row.text.strip()
                
                cs_stat = "0 CS"
                cs_match = re.search(r"(\d+)\s*CS", row_text)
                if cs_match:
                    cs_stat = f"{cs_match.group(1)} CS"

                gold_stat = "0k"
                gold_match = re.search(r"(\d+\.?\d*)\s*k", row_text)
                if gold_match:
                    gold_stat = f"{gold_match.group(1)}k"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat
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

# --- API: TÜM KULLANICILARI DÖNDÜR ---
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
