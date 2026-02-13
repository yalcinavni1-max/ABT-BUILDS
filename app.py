import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- GLOBAL DEĞİŞKENLER ---
# İtem fiyatlarını burada tutacağız {ItemID: Fiyat}
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

# --- 1. İTEM FİYATLARINI YÜKLEME ---
# Uygulama açılınca bir kere çalışır, tüm itemlerin fiyatını öğrenir.
def load_item_data():
    global ITEM_PRICES
    version = get_latest_version()
    print(f"İtem veritabanı yükleniyor... (Versiyon: {version})")
    try:
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()['data']
            for item_id, item_info in data.items():
                # İtemin toplam altın değeri
                if 'gold' in item_info:
                    ITEM_PRICES[int(item_id)] = item_info['gold']['total']
            print("İtem fiyatları başarıyla yüklendi.")
    except Exception as e:
        print(f"İtem verileri çekilemedi: {e}")

# --- 2. NOT HESAPLAMA ---
def calculate_grade(score):
    if score >= 4.0: return "S"
    elif score >= 3.0: return "A"
    elif score >= 2.5: return "B"
    elif score >= 2.0: return "C"
    elif score >= 1.0: return "D"
    else: return "F"

# --- SCRAPER ---
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

                # ŞAMPİYON
                champ_key = "Poro"
                links = row.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "/champions/builds/" in href:
                        parts = href.split("/")
                        if len(parts) > 3:
                            raw = parts[3].replace("-", "").replace(" ", "").lower()
                            name_map = {"wukong": "MonkeyKing", "renata": "Renata", "fiddlesticks": "Fiddlesticks", "kais'a": "Kaisa", "kaisa": "Kaisa", "leesin": "LeeSin", "belveth": "Belveth", "missfortune": "MissFortune", "masteryi": "MasterYi", "drmundo": "DrMundo", "jarvaniv": "JarvanIV", "tahmkench": "TahmKench", "xinzhao": "XinZhao", "kogmaw": "KogMaw", "reksai": "RekSai", "aurelionsol": "AurelionSol", "twistedfate": "TwistedFate"}
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

                # --- İTEMLERİ TOPLA VE FİYAT HESAPLA ---
                items = []
                total_inventory_value = 0 # Envanter değeri
                
                img_tags = row.find_all("img")
                for img in img_tags:
                    img_str = str(img)
                    if "champion" in img_str or "spell" in img_str or "tier" in img_str or "perk" in img_str: continue
                    
                    # Regex ile item ID'sini çekiyoruz
                    candidates = re.findall(r"(\d{4})", img_str)
                    for num in candidates:
                        val = int(num)
                        if 1000 <= val <= 8000:
                            if 5000 <= val < 6000: continue
                            if 2020 <= val <= 2030: continue
                            
                            # İtemi listeye ekle
                            items.append(f"{RIOT_CDN}/item/{val}.png")
                            
                            # İtemin fiyatını bul ve topla
                            if val in ITEM_PRICES:
                                total_inventory_value += ITEM_PRICES[val]
                            else:
                                # Fiyatı listede yoksa ortalama bir değer ekle (Bazen yeni itemler gecikir)
                                total_inventory_value += 2500 

                clean_items = list(dict.fromkeys(items))[:9]

                # --- ALTIN HESABI (İTEMLER + TAHMİNİ CEP HARÇLIĞI) ---
                # İtemlerin toplamı + 750 Gold (Potlar, Wardlar ve cepte kalan para)
                final_gold_value = total_inventory_value + 750
                gold_stat = f"{round(final_gold_value / 1000, 1)}k"

                # --- DİĞER VERİLER ---
                kda_text = kda_div.text.strip()
                result = "win" if "Victory" in row.text or "Zafer" in row.text else "lose"

                # KDA Ayrıştırma
                nums = re.findall(r"(\d+)", kda_text)
                kda_display = "Perfect"
                score_val = 0.0
                if len(nums) >= 3:
                    k, d, a = int(nums[0]), int(nums[1]), int(nums[2])
                    if d > 0:
                        score_val = (k + a) / d
                        kda_display = "{:.2f}".format(score_val)
                    else:
                        score_val = 99.0

                grade = calculate_grade(score_val)

                # CS
                cs_val = 0
                cs_match = re.search(r"(\d+)\s*CS", row.text, re.IGNORECASE)
                if cs_match:
                    cs_val = int(cs_match.group(1))
                cs_stat = f"{cs_val} CS"

                matches_info.append({
                    "champion": champ_key,
                    "result": result,
                    "kda": kda_text,
                    "img": final_champ_img,
                    "items": clean_items,
                    "grade": grade,
                    "cs": cs_stat,
                    "gold": gold_stat, # İtem bazlı hesaplanmış altın
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

# --- UYGULAMA BAŞLANGICI ---
if __name__ == '__main__':
    # Önce item fiyatlarını indiriyoruz
    load_item_data()
    app.run(host='0.0.0.0', port=5000)
