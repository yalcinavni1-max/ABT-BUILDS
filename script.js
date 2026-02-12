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

async function sendVote(matchId, points, elementId, btnElement) {
    const originalText = btnElement.innerText;
    btnElement.innerText = "⏳";
    btnElement.disabled = true;
    try {
        const response = await fetch('/api/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ match_id: matchId, points: points })
        });
        if (!response.ok) throw new Error("API Hatası");
        const result = await response.json();
        
        const scoreElement = document.getElementById(elementId);
        if (scoreElement) {
            scoreElement.innerHTML = `<span style="color:#ffd700; font-size:1.1em;">★ ${result.average}</span> <span style="font-size:0.75rem; color:#aaa;">(${result.count} oy)</span>`;
        }
        btnElement.style.backgroundColor = "#2deb90";
        btnElement.style.color = "#000";
        setTimeout(() => {
            btnElement.innerText = originalText;
            btnElement.disabled = false;
            btnElement.style.backgroundColor = "";
            btnElement.style.color = "";
        }, 1000);
    } catch (error) {
        btnElement.innerText = "❌";
        setTimeout(() => { btnElement.innerText = originalText; btnElement.disabled = false; }, 2000);
        alert("Hata oluştu.");
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
        user.matches.forEach((match, index) => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result);
            card.onclick = function(e) { if(e.target.tagName !== 'BUTTON') this.classList.toggle('active'); };

            let itemsHtml = '';
            if (match.items) match.items.forEach(url => itemsHtml += `<div class="item-slot"><img src="${url}" class="item-img" onerror="this.parentElement.style.display='none'"></div>`);
            const currentCount = match.items ? match.items.length : 0;
            for (let i = currentCount; i < 9; i++) itemsHtml += `<div class="item-slot empty"></div>`;

            const safeName = name.replace(/[^a-zA-Z0-9]/g, '');
            const scoreDisplayId = `score-${safeName}-${index}`;
            let buttonsHtml = '';
            for(let i=1; i<=10; i++) buttonsHtml += `<button class="vote-btn" onclick="sendVote('${match.match_id}', ${i}, '${scoreDisplayId}', this)">${i}</button>`;

            card.innerHTML = `
                <div class="card-content">
                    <div class="champ-info">
                        <img src="${match.img}" class="champ-img" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <div id="${scoreDisplayId}" style="font-weight:bold; margin-top:2px;">
                                <span style="color:#ffd700;">★ ${match.user_score || '-'}</span> 
                                <span style="font-size:0.75rem; color:#aaa;">(${match.vote_count || 0} oy)</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="items-grid">${itemsHtml}</div>

                    <div class="stats-group">
                        <div class="result-text">${match.result.toUpperCase()}</div>
                        <div class="kda-text">${match.kda}</div>
                        <div class="farm-text">
                            <span class="cs-val">${match.cs}</span> 
                            <span class="gold-val" style="color:#ffd700;">💰${match.gold}</span>
                        </div>
                    </div>
                </div>

                <div class="match-details">
                    <div style="margin-bottom:8px; color:#bbb; font-size:0.85rem; border-bottom:1px solid #444; padding-bottom:5px;">PERFORMANS PUANLAMASI</div>
                    <div class="vote-buttons-container">${buttonsHtml}</div>
                </div>
            `;
            matchesContainer.appendChild(card);
        });
    } else { matchesContainer.innerHTML = "<p style='text-align:center;'>Veri yok.</p>"; }
    profilesArea.appendChild(profileSection);
}
fetchMatches();
