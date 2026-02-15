const profilesArea = document.getElementById('profiles-area');

async function fetchMatches() {
    try {
        const response = await fetch('/api/get-ragnar');
        if (!response.ok) throw new Error("Sunucu Hatası");
        
        const usersData = await response.json();
        profilesArea.innerHTML = '';
        
        // Veri tekil mi yoksa liste mi kontrol et
        if (Array.isArray(usersData)) {
            usersData.forEach(user => {
                // Eğer kullanıcı verisinde hata varsa (Scraper hatası gibi) kartı oluşturma
                if (!user.error) {
                    createProfileCard(user);
                } else {
                    console.warn("Kullanıcı verisi alınamadı:", user);
                }
            });
        } else {
            if (!usersData.error) createProfileCard(usersData);
        }
    } catch (error) {
        console.error("Hata:", error);
        profilesArea.innerHTML = `<div style="text-align:center; padding:50px; color:#aaa;">Veriler yüklenirken hata oluştu.<br>Lütfen sayfayı yenileyin.</div>`;
    }
}

function createProfileCard(user) {
    const profileSection = document.createElement('div');
    profileSection.classList.add('user-section');
    
    // Güvenli Veri Atama (Varsayılan Değerler)
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
            // Sonuç yoksa varsayılan 'lose' ata ki stil bozulmasın
            const resultClass = match.result ? match.result : 'lose';
            card.classList.add('match-card', resultClass);
            
            // Kart tıklama olayı
            card.onclick = function() { this.classList.toggle('active'); };

            // İtemleri Güvenli Oluştur
            let itemsHtml = '';
            if (match.items && Array.isArray(match.items)) {
                match.items.forEach(url => {
                    itemsHtml += `<div class="item-slot"><img src="${url}" class="item-img" onerror="this.parentElement.style.display='none'"></div>`;
                });
            }
            
            // Boş item slotlarını doldur
            const currentCount = (match.items && Array.isArray(match.items)) ? match.items.length : 0;
            for (let i = currentCount; i < 7; i++) { // Genelde 6-7 item slotu vardır
                itemsHtml += `<div class="item-slot empty"></div>`;
            }

            const gradeVal = match.grade || '-';
            const gradeClass = `grade-${gradeVal}`;
            const champImg = match.img || "https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png";
            const champName = match.champion || "Şampiyon";
            
            // Yeni Eklenen Veriler İçin Güvenlik Kontrolü
            const queueMode = match.queue_mode || "Normal";
            const rankImg = match.rank_img || "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-unranked.png";

            card.innerHTML = `
                <div class="card-content">
                    <div class="champ-info">
                        <img src="${champImg}" class="champ-img" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/14.3.1/img/champion/Poro.png'">
                        <div>
                            <span class="champ-name">${champName}</span>
                            <div class="grade-badge ${gradeClass}">${gradeVal}</div>
                        </div>
                    </div>
                    
                    <div class="items-grid">${itemsHtml}</div>

                    <div class="stats">
                        <div class="result-text">${resultClass.toUpperCase()}</div>
                        <div class="kda-text">${match.kda || '0/0/0'}</div>
                        <div style="font-size: 0.7rem; color: #666; margin-top: 4px;">▼ Detay</div>
                    </div>
                </div>

                <div class="match-details">
                    <div class="detail-box">
                        <span class="detail-label">KDA Skor</span>
                        <span class="detail-val text-white">${match.kda_score || '-'}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Minyon</span>
                        <span class="detail-val text-gray">${match.cs || '0 CS'}</span>
                    </div>
                    
                    <div class="detail-box" style="display: flex; flex-direction: column; align-items: center;">
                        <span class="detail-label" style="margin-bottom: 2px; font-size: 0.7rem; color: #aaa;">${queueMode}</span>
                        <img src="${rankImg}" style="width: 35px; height: 35px; object-fit: contain;" onerror="this.style.display='none'">
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

// Sayfa yüklendiğinde çalıştır
fetchMatches();
