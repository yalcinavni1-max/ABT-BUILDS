const profilesArea = document.getElementById('profiles-area');

async function fetchMatches() {
    try {
        const response = await fetch('/api/get-ragnar');
        if (!response.ok) throw new Error("Sunucu Hatası");
        const usersData = await response.json();
        profilesArea.innerHTML = '';
        if (Array.isArray(usersData)) usersData.forEach(user => createProfileCard(user));
        else createProfileCard(usersData);
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

    profileSection.innerHTML = `
        <div class="profile-header">
            <img src="${icon}" class="profile-icon" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/profileicon/29.png'">
            <div class="profile-text">
                <div class="summoner-name-style">${name}</div>
                <div class="rank-text">${rank}</div>
            </div>
        </div>
        <div class="matches-container"></div>
    `;
    
    const matchesContainer = profileSection.querySelector('.matches-container');

    if (user.matches && user.matches.length > 0) {
        user.matches.forEach(match => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result);
            card.onclick = function() { this.classList.toggle('active'); };

            let itemsHtml = '';
            if (match.items) match.items.forEach(url => itemsHtml += `<div class="item-slot"><img src="${url}" class="item-img" onerror="this.parentElement.style.display='none'"></div>`);
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 9; i++) itemsHtml += `<div class="item-slot empty"></div>`;

            const gradeClass = `grade-${match.grade}`;

            card.innerHTML = `
                <div class="card-content">
                    <div class="champ-info">
                        <img src="${match.img}" class="champ-img" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <div class="grade-badge ${gradeClass}">${match.grade}</div>
                        </div>
                    </div>
                    
                    <div class="items-grid">${itemsHtml}</div>

                    <div class="stats">
                        <div class="result-text">${match.result.toUpperCase()}</div>
                        <div class="kda-text">${match.kda}</div>
                        <div style="font-size: 0.7rem; color: #666; margin-top: 4px;">▼ Detay</div>
                    </div>
                </div>

                <div class="match-details">
                    <div class="detail-box">
                        <span class="detail-label">KDA Skor</span>
                        <span class="detail-val text-white">${match.kda_score}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Minyon</span>
                        <span class="detail-val text-gray">${match.cs}</span>
                    </div>
                    <div class="detail-box" style="display: flex; flex-direction: column; align-items: center;">
                        <span class="detail-label" style="margin-bottom: 2px; font-size: 0.7rem; color: #aaa;">${match.queue_mode}</span>
                        <img src="${match.rank_img}" style="width: 35px; height: 35px; object-fit: contain;">
                    </div>
                </div>
            `;
            matchesContainer.appendChild(card);
        });
    } else { matchesContainer.innerHTML = "<p style='text-align:center;'>Veri yok.</p>"; }
    profilesArea.appendChild(profileSection);
}
fetchMatches();
