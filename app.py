import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- GLOBAL İTEM FİYAT LİSTESİ ---
ITEM_PRICES = {}

URL_LISTESI = [
    "https://www.leagueofgraphs.com/summoner/tr/Ragnar+Lothbrok-0138",
    "https://www.leagueofgraphs.com/summoner/tr/D%C3%96L+VE+OKS%C4%B0JEN-011"
]

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

def get_latest_version():
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        if r.status_code == 200: return r.json()[0]
    except: pass
    return "14.3.1"

# --- 1. İTEM FİYATLARINI ÇEKEN FONKSİYON ---
# Uygulama başlarken bir kere çalışır, tüm fiyatları hafızaya alır.
def load_item_prices():
    global ITEM_PRICES
    version = get_latest_version()
    print(f"İtem fiyatları Riot sunucusundan çekiliyor... (v{version})")
    try:
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()['data']
            for item_id, info in data.items():
                if 'gold' in info:
                    ITEM_PRICES[int(item_id)] = info['gold']['total']
            print(f"Başarılı! {len(ITEM_PRICES)} adet item fiyatı yüklendi.")
    except Exception as e:
        print(f"İtem fiyatları yüklenirken hata: {e}")

# --- 2. NOT HESAPLAMA ---
def calculate_grade(score):
    if score >= 4.0: return "S"
    elif score >= 3.0: return "A"
    elif score >= 2.5: return "B"
    elif score >= 2.0: return "C"
    elif score >= 1.0: return "D"
    else: return "F"

# --- SCRAPER (SENİN ÇALIŞAN ORİJİNAL KODUN) ---
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

                # ŞAMPİYON BULMA
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

                # --- İTEMLER VE FİYAT HESAPLAMA ---
                items = []
                current_match_gold = 0 # Bu maçtaki itemlerin toplam fiyatı
                
                img_tags = row.find_all("img")
                for img in img_tags:
                    img_str = str(img)
                    if "champion" in img_str or "spell" in img_str or "tier" in img_str or "perk" in img_str: continue
                    candidates = re.findall(r"(\d{4})", img_str)
                    for num in candidates:
                        val = int(num)
                        # Senin item filtrelerin (Çalışan koddan)
                        if 1000 <= val <= 8000:
                            if 5000 <= val < 6000: continue
                            if 2020 <= val <= 2030: continue
                            
                            # İtemi ekle
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                            
                            # Fiyatını topla (Riot veritabanından bakarak)
                            if val in ITEM_PRICES:
                                current_match_gold += ITEM_PRICES[val]
                            else:
                                current_match_gold += 2500 # Fiyatı bulunamazsa ortalama ekle
                
                clean_items = list(dict.fromkeys(items))[:9]

                # --- ALTIN HESABI (İTEMLER + 900) ---
                total_gold = current_match_gold + 900
                gold_stat = f"{round(total_gold / 1000, 1)}k"

                # --- DİĞER VERİLER ---
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                # KDA
                nums = re.findall(r"(\d+)", kda_text)
                kda_display = "Perfect"
                score_val = 99.0
                if len(nums) >= 3:
                    k, d, a = int(nums[0]), int(nums[1]), int(nums[2])
                    if d > 0:
                        score_val = (k + a) / d
                        kda_display = "{:.2f}".format(score_val)
                    else: score_val = 99.0
                else:
                    kda_display = "-"
                    score_val = 0.0

                grade = calculate_grade(score_val)

                # CS (Minyon) - Düzeltilmiş Arama
                cs_val = 0
                cs_div = row.find("div", class_="minions")
                if cs_div:
                    num_match = re.search(r"(\d+)", cs_div.text)
                    if num_match: cs_val = int(num_match.group(1))
                else:
                    cs_match = re.search(r"(\d+)\s*CS", row.text, re.IGNORECASE)
                    if cs_match: cs_val = int(cs_match.group(1))
                cs_stat = f"{cs_val} CS"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat, # İtem + 900 hesabı
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

# --- ANA ÇALIŞTIRMA ---
if __name__ == '__main__':
    # Sunucu kalkarken fiyatları çek
    load_item_prices()
    app.run(host='0.0.0.0', port=5000)
