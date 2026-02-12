const profilesArea = document.getElementById('profiles-area');

async function fetchMatches() {
    try {
        const response = await fetch('/api/get-ragnar');
        if (!response.ok) throw new Error("Sunucu Hatası");
        
        const usersData = await response.json();
        profilesArea.innerHTML = '';

        if (Array.isArray(usersData)) {
            usersData.forEach(user => createProfileCard(user));
        } else {
            createProfileCard(usersData);
        }

    } catch (error) {
        console.error("Hata:", error);
        profilesArea.innerHTML = `<div style="text-align:center; padding:50px; color:#aaa;">Veriler yükleniyor...<br>Lütfen bekleyin.</div>`;
    }
}

function calculateScore(kdaStr) {
    // KDA metnini parçala (Örn: "9 / 3 / 12")
    // Python'dan gelen veri bazen boşluklu bazen boşluksuz olabilir, regex ile sayıları alalım.
    const nums = kdaStr.match(/\d+/g);
    
    if (!nums || nums.length < 3) return { score: '-', class: 'score-c', ratio: 0 };

    const k = parseInt(nums[0]);
    const d = parseInt(nums[1]);
    const a = parseInt(nums[2]);

    // KDA Oranı: (Kill + Asist) / Death
    // Eğer ölüm 0 ise, bölen 1 olsun (sonsuz hatası vermemesi için)
    const divisor = d === 0 ? 1 : d;
    const ratio = (k + a) / divisor;

    let score = "C";
    let scoreClass = "score-c";

    if (ratio >= 5.0) { score = "MVP"; scoreClass = "score-mvp"; }
    else if (ratio >= 4.0) { score = "S+"; scoreClass = "score-s"; }
    else if (ratio >= 3.0) { score = "S"; scoreClass = "score-s"; }
    else if (ratio >= 2.5) { score = "A"; scoreClass = "score-a"; }
    else if (ratio >= 1.5) { score = "B"; scoreClass = "score-b"; }

    return { score, class: scoreClass, ratio: ratio.toFixed(2) };
}

function createProfileCard(user) {
    const profileSection = document.createElement('div');
    profileSection.classList.add('user-section');

    const icon = user.icon || "https://ddragon.leagueoflegends.com/cdn/14.3.1/img/profileicon/29.png";
    const name = user.summoner || "Sihirdar";
    const rank = user.rank || "Unranked";

    const headerHtml = `
        <div class="profile-header">
            <img src="${icon}" class="profile-icon" alt="Icon" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/profileicon/29.png'">
            <div class="profile-text">
                <div class="summoner-name-style">${name}</div>
                <div class="rank-text">${rank}</div>
            </div>
        </div>
        <div class="matches-container"></div>
    `;
    
    profileSection.innerHTML = headerHtml;
    const matchesContainer = profileSection.querySelector('.matches-container');

    if (user.matches && user.matches.length > 0) {
        user.matches.forEach(match => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result);

            // KDA Puanını Hesapla
            const calc = calculateScore(match.kda);

            // Tıklayınca Açılma Olayı
            card.onclick = function() {
                this.classList.toggle('active');
            };

            // İtemleri Hazırla
            let itemsHtml = '';
            if (match.items) {
                match.items.forEach(itemUrl => {
                    itemsHtml += `<div class="item-slot"><img src="${itemUrl}" class="item-img" onerror="this.parentElement.style.display='none'"></div>`;
                });
            }
            // Boş Slotları Doldur
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 9; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            // Kartın İçeriği (Özet + Detay)
            card.innerHTML = `
                <div class="match-summary">
                    <div class="champ-info">
                        <img src="${match.img}" class="champ-img" alt="${match.champion}" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <span class="score-badge ${calc.class}">${calc.score}</span>
                        </div>
                    </div>
                    
                    <div class="items-grid">
                        ${itemsHtml}
                    </div>

                    <div class="stats">
                        <div class="result-text">${match.result.toUpperCase()}</div>
                        <div class="kda-text">${match.kda}</div>
                    </div>
                </div>

                <div class="match-details">
                    <div class="detail-row">
                        <span class="detail-label">KDA Oranı:</span>
                        <span>${calc.ratio}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Skor Performansı:</span>
                        <span style="font-weight:bold;">${calc.score} Tier</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Oyun Modu:</span>
                        <span>Dereceli Tek/Çift</span>
                    </div>
                    <div style="text-align:center; font-size:0.8rem; color:#666; margin-top:10px;">
                        Detaylı analiz için LeagueOfGraphs ziyaret edilebilir.
                    </div>
                </div>
            `;
            matchesContainer.appendChild(card);
        });
    } else {
        matchesContainer.innerHTML = "<p style='text-align:center; color:#777;'>Maç verisi bulunamadı.</p>";
    }

    profilesArea.appendChild(profileSection);
}

fetchMatches();
