const profilesArea = document.getElementById('profiles-area');

async function fetchMatches() {
    try {
        // API'den verileri çek (Çoklu Kullanıcı Modu)
        const response = await fetch('/api/get-ragnar');
        
        // Eğer sunucu hata verirse yakala
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const usersData = await response.json();

        // "Yükleniyor..." yazısını temizle
        profilesArea.innerHTML = '';

        // Gelen her kullanıcı için kart oluştur
        if (Array.isArray(usersData)) {
            usersData.forEach(user => {
                createProfileCard(user);
            });
        } else {
            // Eğer tek kullanıcı gelirse (eski format koruması)
            createProfileCard(usersData);
        }

    } catch (error) {
        console.error("Hata:", error);
        profilesArea.innerHTML = `
            <div style="text-align:center; margin-top:50px;">
                <h3 style="color:#ff5555;">Sunucuya Bağlanılamadı</h3>
                <p style="color:#aaa;">Lütfen 1-2 dakika bekleyip sayfayı yenileyin (F5).</p>
            </div>
        `;
    }
}

function createProfileCard(user) {
    // 1. Profil Kapsayıcısı
    const profileSection = document.createElement('div');
    profileSection.classList.add('user-section');

    // Hata durumunda boş gelirse diye varsayılan değerler
    const icon = user.icon || "https://ddragon.leagueoflegends.com/cdn/14.3.1/img/profileicon/29.png";
    const name = user.summoner || "Sihirdar";
    const rank = user.rank || "Unranked";

    // 2. Profil Başlığı
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
    
    // Maçları Ekle
    const matchesContainer = profileSection.querySelector('.matches-container');

    if (user.matches && user.matches.length > 0) {
        user.matches.forEach(match => {
            const card = document.createElement('div');
            card.classList.add('match-card', match.result); // win veya lose sınıfı

            // --- İTEM DÜZENLEME (KRİTİK BÖLÜM) ---
            let itemsHtml = '';
            
            // 1. Gelen İtemleri Listele
            // Eğer resim bozuksa (onerror), kutuyu silme (.remove yapma!), sadece resmi gizle (display='none').
            // Böylece boş bir kutu olarak kalır ve hizalama bozulmaz.
            if (match.items) {
                match.items.forEach(itemUrl => {
                    itemsHtml += `
                        <div class="item-slot">
                        // DOĞRUSU BU:
                        <img src="${itemUrl}" class="item-img" alt="Item" onerror="this.style.display='none'">


                        </div>
                    `;
                });
            }

            // 2. Kalanları 7'ye Tamamla (Boş Kutular)
            const currentItemCount = match.items ? match.items.length : 0;
            for (let i = currentItemCount; i < 7; i++) {
                itemsHtml += `<div class="item-slot empty"></div>`;
            }
            // -------------------------------------

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
        matchesContainer.innerHTML = "<p style='text-align:center; color:#777; padding:20px;'>Maç verisi bulunamadı veya yükleniyor...</p>";
    }

    // Kartı sayfaya bas
    profilesArea.appendChild(profileSection);
}

// Başlat
fetchMatches();

