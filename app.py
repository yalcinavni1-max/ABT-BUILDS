import re
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

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

def scrape_summoner(url):
    version = get_latest_version()
    RIOT_CDN = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    
    headers = {
        # En güncel tarayıcı taklidi yapıyoruz ki site bizi bot sanıp resimleri gizlemesin
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- PROFİL ---
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

        # --- MAÇLAR ---
        matches_info = []
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            try:
                kda_div = row.find("div", class_="kda")
                if not kda_div: continue

                # 1. ŞAMPİYON BULMA
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

                # 2. İTEMLER (GÖZÜ KARA MODU)
                items = []
                img_tags = row.find_all("img")
                
                for img in img_tags:
                    # Resmin olası bütün kaynaklarını al (src, data-src, data-original)
                    # League of Graphs, gerçek item linkini genelde 'data-original' içine saklar.
                    possible_urls = [
                        img.get("src", ""),
                        img.get("data-src", ""),
                        img.get("data-original", "")
                    ]
                    
                    for url in possible_urls:
                        if not url: continue
                        
                        # --- FİLTRELER (Çok Basit ve Net) ---
                        
                        # 1. Eğer linkin içinde "champion", "spell", "perk" (rün) kelimeleri varsa ATLA.
                        if any(x in url for x in ["champion", "summoner", "spell", "perk", "rune", "class", "role"]):
                            continue

                        # 2. Linkin içindeki sayıları çek
                        matches = re.findall(r"(\d{4})", url)
                        
                        for num in matches:
                            val = int(num)
                            
                            # 3. SAYI FİLTRESİ (Sadece gerçek item aralığı)
                            # 1000'den küçükse item değildir.
                            # 8000'den büyükse item değildir.
                            if 1000 <= val <= 8000:
                                
                                # Yıl klasörleri (2024, 2025 vb.) -> ATLA
                                if 2020 <= val <= 2030: continue
                                
                                # Rün ID'leri (5000-5999 arası genelde ründür) -> ATLA
                                if 5000 <= val < 6000: continue
                                
                                # Ekran çözünürlüğü (1200, 1080 vb.) -> ATLA
                                if val in [1080, 1200, 1280, 1440, 1920]: continue

                                # Geriye kalan her şey İTEMDİR.
                                items.append(f"{RIOT_CDN}/item/{val}.png")
                                break # Bir resimden bir item çıkardık, diğer URL'lere bakma.

                # Tekrarları Temizle (Set kullanarak)
                clean_items = []
                seen = set()
                for x in items:
                    if x not in seen:
                        clean_items.append(x)
                        seen.add(x)
                
                # İlk 7 tanesini al
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
    for url in URL_LISTESI:
        data = scrape_summoner(url)
        all_data.append(data)
    return jsonify(all_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
