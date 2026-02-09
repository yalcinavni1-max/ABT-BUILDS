const container = document.getElementById('matches-container');
const profileIcon = document.getElementById('profile-icon');
const summonerName = document.getElementById('summoner-name');
const rankDisplay = document.getElementById('rank-display');

async function fetchMatches() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/get-ragnar');
        const data = await response.json();

        if (data.summoner) summonerName.innerText = data.summoner;
        if (data.rank) rankDisplay.innerText = data.rank;
        if (data.icon) profileIcon.src = data.icon;

        if (data.matches && data.matches.length > 0) {
            renderMatches(data.matches);
        } else {
            container.innerHTML = "<p style='text-align:center;'>Maç verisi yok.</p>";
        }

    } catch (error) {
        console.error("Hata:", error);
        container.innerHTML = "<p style='text-align:center;'>Python sunucusu kapalı olabilir.</p>";
    }
}

function renderMatches(matches) {
    container.innerHTML = '';

    matches.forEach(match => {
        const card = document.createElement('div');
        card.classList.add('match-card', match.result);

        // İtemleri oluştur
        let itemsHtml = '';
        
        // Gelen itemler
        match.items.forEach(itemUrl => {
            // ÖNEMLİ: onerror olayı, resim yüklenemezse onu boş kutuya çevirir.
            itemsHtml += `
                <div class="item-slot">
                    <img src="${itemUrl}" class="item-img" alt="Item" onerror="this.style.display='none'; this.parentElement.classList.add('broken-image');">
                </div>
            `;
        });

        // 7'ye tamamlamak için boş kutular ekle (Düzen bozulmasın diye)
        for (let i = match.items.length; i < 7; i++) {
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
        container.appendChild(card);
    });
}

fetchMatches();