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

// --- PROFESYONEL OY GÖNDERME FONKSİYONU ---
async function sendVote(matchId, points, elementId, btnElement) {
    // 1. Kullanıcıya geri bildirim ver (Butonu pasif yap)
    const originalText = btnElement.innerText;
    btnElement.innerText = "⏳";
    btnElement.disabled = true;

    try {
        console.log(`Oy gönderiliyor: ID=${matchId}, Puan=${points}`);

        const response = await fetch('/api/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ match_id: matchId, points: points })
        });
        
        if (!response.ok) throw new Error("API Hatası");
        
        const result = await response.json();
        
        // 2. Skoru güncelle (Animasyonlu geçiş gibi hissettirir)
        const scoreElement = document.getElementById(elementId);
        if (scoreElement) {
            scoreElement.innerHTML = `
                <span style="color:#ffd700; font-size:1.1em;">★ ${result.average}</span> 
                <span style="font-size:0.75rem; color:#aaa;">(${result.count} oy)</span>`;
        }
        
        // 3. Başarı durumunda butonu yeşil yap
        btnElement.style.backgroundColor = "#2deb90";
        btnElement.style.color = "#000";
        setTimeout(() => {
            btnElement.innerText = originalText;
            btnElement.disabled = false;
            btnElement.style.backgroundColor = ""; // Eski rengine dön
            btnElement.style.color = "";
        }, 1000);

    } catch (error) {
        console.error(error);
        btnElement.innerText = "❌";
        setTimeout(() => {
            btnElement.innerText = originalText;
            btnElement.disabled = false;
        }, 2000);
        alert("Oy verilemedi. Lütfen sayfayı yenileyip tekrar dene.");
    }
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
        user.matches.forEach((match, index) => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result);

            // Karta tıklama olayı
            card.onclick = function(e) {
                if(e.target.tagName === 'BUTTON') return;
                this.classList.toggle('active');
            };

            let itemsHtml = '';
            // İtemler
            if (match.items) {
                match.items.forEach(itemUrl => {
                    itemsHtml += `<div class="item-slot"><img src="${itemUrl}" class="item-img" onerror="this.parentElement.style.display='none'"></div>`;
                });
            }
            // Boşluklar (9 Slot)
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 9; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            // Benzersiz ID (Sayısal index yerine timestamp kullanarak çakışmayı önle)
            const safeName = name.replace(/[^a-zA-Z0-9]/g, '');
            const scoreDisplayId = `score-${safeName}-${index}`;
            
            // Butonları oluştur (this parametresi eklendi)
            let buttonsHtml = '';
            for(let i=1; i<=10; i++) {
                buttonsHtml += `<button class="vote-btn" onclick="sendVote('${match.match_id}', ${i}, '${scoreDisplayId}', this)">${i}</button>`;
            }

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
                    <div class="champ-info">
                        <img src="${match.img}" class="champ-img" alt="${match.champion}" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <div id="${scoreDisplayId}" style="font-weight:bold; margin-top:2px;">
                                <span style="color:#ffd700;">★ ${match.user_score || '-'}</span> 
                                <span style="font-size:0.75rem; color:#aaa;">(${match.vote_count || 0} oy)</span>
                            </div>
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
                    <div style="margin-bottom:8px; color:#bbb; font-size:0.85rem; border-bottom:1px solid #444; padding-bottom:5px;">PERFORMANS PUANLAMASI</div>
                    <div class="vote-buttons-container">
                        ${buttonsHtml}
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
