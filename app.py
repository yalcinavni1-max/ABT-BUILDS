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

# --- 1. ALTIN HESAPLAMA MOTORU (Sitede yazmadığı için) ---
def estimate_gold(kills, deaths, assists, cs):
    # Tahmini Altın Hesabı:
    # 500 (Başlangıç) + Kill(300) + Asist(150) + CS(21) + Pasif Gelir(~3000)
    base_passive = 3000 
    gold = 500 + base_passive + (kills * 300) + (assists * 150) + (cs * 21)
    return f"{round(gold / 1000, 1)}k"

# --- 2. LEVEL HESAPLAMA MOTORU (Sitede yazmadığı için) ---
def estimate_level(item_count, cs):
    # İtem sayısına göre level tahmini
    if item_count >= 5: return "17-18"
    elif item_count == 4: return "14-16"
    elif item_count == 3: return "12-13"
    elif item_count == 2: return "9-11"
    else: return "6-9"

# --- 3. NOT HESAPLAMA (Grade) ---
def calculate_grade(kda_text):
    try:
        if "Perfect" in kda_text or "Mükemmel" in kda_text: return "S"
        
        # Sayıları ayıkla
        nums = re.findall(r"(\d+)", kda_text)
        if len(nums) >= 3:
            k = float(nums[0])
            d = float(nums[1])
            a = float(nums[2])
            
            # (Kill + Asist) / Death
            score = (k + a) / d if d > 0 else 99
            
            if score >= 4.0: return "S"
            elif score >= 3.0: return "A"
            elif score >= 2.5: return "B"
            elif score >= 2.0: return "C"
            elif score >= 1.0: return "D"
            else: return "F"
    except: pass
    return "-"

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- TEK BİR KULLANICIYI ÇEKEN FONKSİYON ---
def scrape_summoner(url):
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    # SENİN GÖNDERDİĞİN, ÇALIŞAN HEADERS AYARLARI (AYNEN KORUNDU)
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

                # ŞAMPİYON BULMA MANTIĞI (ORİJİNAL KOD KORUNDU)
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

                # İTEMLER (ORİJİNAL KOD KORUNDU)
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
                
                # --- YENİ ÖZELLİKLER BURADA EKLENİYOR (ESKİ KODU BOZMADAN) ---
                
                # 1. Not Hesapla
                grade = calculate_grade(kda_text)

                # 2. CS (Minyon) Bul
                cs_val = 0
                cs_stat = "0 CS"
                # Regex ile metnin içindeki sayıyı çekiyoruz
                cs_match = re.search(r"(\d+)\s*CS", row.text)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                    cs_stat = f"{cs_val} CS"

                # 3. KDA Sayılarını Ayrıştır (Altın Hesabı İçin)
                k_num, d_num, a_num = 0, 0, 0
                kda_nums = re.findall(r"(\d+)", kda_text)
                if len(kda_nums) >= 3:
                    k_num = int(kda_nums[0])
                    d_num = int(kda_nums[1])
                    a_num = int(kda_nums[2])

                # 4. Altın Hesapla (Sitede yazmadığı için)
                gold_stat = estimate_gold(k_num, d_num, a_num, cs_val)

                # 5. Level Hesapla (Sitede yazmadığı için)
                raw_level = estimate_level(len(clean_items), cs_val)
                level_stat = f"Lvl {raw_level}"

                # Listeye yeni verileri de ekliyoruz
                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,       # Yeni
                    "cs": cs_stat,        # Yeni
                    "gold": gold_stat,    # Yeni
                    "level": level_stat   # Yeni
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
