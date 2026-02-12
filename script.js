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
        profilesArea.innerHTML = `<div style="text-align:center; padding:50px; color:#aaa;">Veriler yükleniyor...</div>`;
    }
}

// Oy Gönderme Fonksiyonu
async function sendVote(matchId, points, elementId) {
    try {
        const response = await fetch('/api/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ match_id: matchId, points: points })
        });
        
        const result = await response.json();
        
        // Ekrana yeni puanı yaz
        const scoreElement = document.getElementById(elementId);
        if (scoreElement) {
            scoreElement.innerHTML = `<span style="color:#ffd700;">★ ${result.average}</span> <span style="font-size:0.7rem; color:#888;">(${result.count} oy)</span>`;
        }
        
        alert("Puanın kaydedildi!");
        
    } catch (error) {
        alert("Oy verilirken hata oluştu.");
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
            <img src="${icon}" class="profile-icon" alt="Icon">
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

            // Detay açma/kapama
            card.onclick = function(e) {
                // Eğer butonlara tıklanırsa kartı açma
                if(e.target.tagName === 'BUTTON') return;
                this.classList.toggle('active');
            };

            let itemsHtml = '';
            if (match.items) {
                match.items.forEach(itemUrl => {
                    itemsHtml += `<div class="item-slot"><img src="${itemUrl}" class="item-img"></div>`;
                });
            }
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 9; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            // Benzersiz ID oluştur (Puanı güncellemek için)
            const scoreDisplayId = `score-${name}-${index}`.replace(/\s/g, '');

            // Puan Butonlarını Oluştur (1-10 arası)
            let buttonsHtml = '';
            for(let i=1; i<=10; i++) {
                buttonsHtml += `<button class="vote-btn" onclick="sendVote('${match.match_id}', ${i}, '${scoreDisplayId}')">${i}</button>`;
            }

            card.innerHTML = `
                <div class="match-summary">
                    <div class="champ-info">
                        <img src="${match.img}" class="champ-img">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <div id="${scoreDisplayId}" class="user-score-display">
                                <span style="color:#ffd700;">★ ${match.user_score || '-'}</span> 
                                <span style="font-size:0.7rem; color:#888;">(${match.vote_count || 0} oy)</span>
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
                    <div style="margin-bottom:10px; color:#ccc;">Bu performansa puan ver:</div>
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
