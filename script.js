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

            // Tıklayınca Detay Açma Olayı
            card.onclick = function() {
                this.classList.toggle('active');
            };

            let itemsHtml = '';
            if (match.items) {
                match.items.forEach(itemUrl => {
                    itemsHtml += `<div class="item-slot"><img src="${itemUrl}" class="item-img" onerror="this.parentElement.style.display='none'"></div>`;
                });
            }
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 9; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            // Puan Rengi Belirleme
            let scoreClass = "score-gray";
            if (match.score === "MVP" || match.score === "S") scoreClass = "score-gold";
            else if (match.score === "A") scoreClass = "score-green";

            card.innerHTML = `
                <div class="match-summary">
                    <div class="champ-info">
                        <img src="${match.img}" class="champ-img" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <span class="score-badge ${scoreClass}">${match.score}</span>
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
                        <span>Seviye: <strong>${match.level}</strong></span>
                        <span>Minyon (CS): <strong>${match.cs}</strong></span>
                    </div>
                    <div class="detail-extra">
                        Maç detaylarına gitmek için <a href="#" style="color:#00bba3;">LeagueOfGraphs</a> (Temsili)
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
