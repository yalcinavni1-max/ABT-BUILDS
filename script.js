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
        profilesArea.innerHTML = `<div style="text-align:center; padding:50px; color:#aaa;">Veriler yükleniyor veya sunucu meşgul...<br>Lütfen bekleyin.</div>`;
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
        user.matches.forEach(match => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result);

            // İTEMLERİ DİZ
            let itemsHtml = '';
            
            // 1. Gelen itemleri ekle
            if (match.items) {
                match.items.forEach(itemUrl => {
                    // DİKKAT: Eğer resim yüklenemezse (onerror), bu sefer kutuyu GİZLE (display:none).
                    // Ama parent elementi (item-slot) gizlememiz lazım ki boşluk kalmasın.
                    itemsHtml += `
                        <div class="item-slot">
                            <img src="${itemUrl}" class="item-img" alt="Item" onerror="this.parentElement.style.display='none'">
                        </div>
                    `;
                });
            }

            // 2. Kalanları boş kutuyla doldur (7'ye tamamla)
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 7; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            card.innerHTML = `
                <div class="champ-info">
                    <img src="${match.img}" class="champ-img" alt="${match.champion}" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                    <div>
                        <span class="champ-name">${match.champion}</span>
                        <span class="game-mode">Dereceli</span>
                    </div>
                </div>
                
                <div class="items-grid">
                    ${itemsHtml}
                </div>

                <div class="stats">
                    <div class="result-text">${match.result.toUpperCase()}</div>
                    <div class="kda-text">${match.kda}</div>
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
