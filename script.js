const profilesArea = document.getElementById('profiles-area');

async function fetchMatches() {
    try {
        // API artık bir liste ([User1, User2]) döndürüyor
        const response = await fetch('/api/get-ragnar');
        const usersData = await response.json();

        // Yükleniyor yazısını temizle
        profilesArea.innerHTML = '';

        // Gelen her kullanıcı için döngü
        usersData.forEach(user => {
            createProfileCard(user);
        });

    } catch (error) {
        console.error("Hata:", error);
        profilesArea.innerHTML = "<p style='text-align:center;'>Sunucuya bağlanılamadı.</p>";
    }
}

function createProfileCard(user) {
    // 1. Profil Kapsayıcısı (Kutusu)
    const profileSection = document.createElement('div');
    profileSection.classList.add('user-section');

    // 2. Profil Başlığı (Resim, İsim, Rank)
    const headerHtml = `
        <div class="profile-header">
            <img src="${user.icon}" class="profile-icon" alt="Icon">
            <div class="profile-text">
                <div class="summoner-name-style">${user.summoner}</div>
                <div class="rank-text">${user.rank}</div>
            </div>
        </div>
        <div class="matches-container"></div>
    `;
    
    profileSection.innerHTML = headerHtml;
    
    // Maçları ekleyelim
    const matchesContainer = profileSection.querySelector('.matches-container');

    if (user.matches && user.matches.length > 0) {
        user.matches.forEach(match => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result);

            // İtemleri oluştur
            let itemsHtml = '';
            match.items.forEach(itemUrl => {
                itemsHtml += `
                    <div class="item-slot">
                        <img src="${itemUrl}" class="item-img" alt="Item" onerror="this.closest('.item-slot').remove()">
                    </div>
                `;
            });

            // 7'ye tamamla (Boş kutular)
            for (let i = match.items.length; i < 7; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            card.innerHTML = `
                <div class="champ-info">
                    <img src="${itemUrl}" class="item-img" alt="Item" onerror="this.style.display='none'">
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

    // Oluşturulan kartı ana ekrana ekle
    profilesArea.appendChild(profileSection);
}

fetchMatches();

