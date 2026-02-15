const profilesArea = document.getElementById('profiles-area');

async function fetchMatches() {
    // Yükleniyor mesajını göster
    profilesArea.innerHTML = `<div class="loading">Veriler Çekiliyor...<br><small>Bu işlem birkaç saniye sürebilir.</small></div>`;

    try {
        const response = await fetch('/api/get-ragnar');
        if (!response.ok) throw new Error("Sunucu Cevap Vermedi");
        
        const usersData = await response.json();
        profilesArea.innerHTML = ''; // Temizle
        
        const list = Array.isArray(usersData) ? usersData : [usersData];
        
        list.forEach(user => {
            if (user.error) {
                console.error("Kullanıcı Hatası:", user.error);
                // Hata olsa bile kart basmayı dene veya atla
            } else {
                createProfileCard(user);
            }
        });
        
        if (profilesArea.innerHTML === '') {
            profilesArea.innerHTML = '<div style="color:white; text-align:center;">Gösterilecek veri bulunamadı.</div>';
        }

    } catch (error) {
        console.error("JS Hatası:", error);
        profilesArea.innerHTML = `<div style="text-align:center; padding:50px; color:#ff6b6b;">
            <h3>Veriler Yüklenemedi!</h3>
            <p>Lütfen Python sunucusunu yeniden başlatın.</p>
            <small>${error.message}</small>
        </div>`;
    }
}

function createProfileCard(user) {
    const section = document.createElement('div');
    section.className = 'user-section';
    
    // Güvenli Varsayılanlar
    const icon = user.icon || "https://ddragon.leagueoflegends.com/cdn/14.3.1/img/profileicon/29.png";
    const name = user.summoner || "Bilinmeyen";
    const rank = user.rank || "Unranked";

    section.innerHTML = `
        <div class="profile-header">
            <img src="${icon}" class="profile-icon">
            <div class="profile-text">
                <div class="summoner-name-style">${name}</div>
                <div class="rank-text">${rank}</div>
            </div>
        </div>
        <div class="matches-container"></div>
    `;
    
    const container = section.querySelector('.matches-container');

    if (user.matches && user.matches.length > 0) {
        user.matches.forEach(match => {
            const card = document.createElement('div');
            const resClass = match.result ? match.result : 'lose';
            card.classList.add('match-card', resClass);
            card.onclick = () => card.classList.toggle('active');

            // İtemler
            let itemsHtml = '';
            const items = match.items || [];
            items.forEach(url => {
                itemsHtml += `<div class="item-slot"><img src="${url}" class="item-img"></div>`;
            });
            for(let i=items.length; i<7; i++) itemsHtml += `<div class="item-slot empty"></div>`;

            // Veriler
            const champImg = match.img || "";
            const lpText = match.lp_change || "";
            let lpStyle = "color:#aaa;";
            if(lpText.includes('+')) lpStyle = "color:#4cd137;";
            if(lpText.includes('-')) lpStyle = "color:#e84118;";

            card.innerHTML = `
                <div class="card-content">
                    <div class="champ-info">
                        <img src="${champImg}" class="champ-img">
                        <div>
                            <span class="champ-name">${match.champion}</span>
                            <div class="grade-badge grade-${match.grade}">${match.grade}</div>
                        </div>
                    </div>
                    <div class="items-grid">${itemsHtml}</div>
                    <div class="stats">
                        <div class="result-text">${resClass.toUpperCase()}</div>
                        <div class="kda-text">${match.kda}</div>
                        <div style="font-size:0.7rem; color:#666;">▼ Detay</div>
                    </div>
                </div>
                <div class="match-details">
                    <div class="detail-box">
                        <span>KDA Skor</span>
                        <b class="text-white">${match.kda_score}</b>
                    </div>
                    <div class="detail-box">
                        <span>Minyon</span>
                        <b class="text-gray">${match.cs}</b>
                    </div>
                    <div class="detail-box" style="flex-direction:column;">
                        <span style="font-size:0.65rem; color:#aaa;">${match.queue_mode}</span>
                        <img src="${match.rank_img}" style="width:30px; height:30px;">
                        <span style="font-size:0.7rem; font-weight:bold; ${lpStyle}">${lpText}</span>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    } else {
        container.innerHTML = '<div style="padding:20px; text-align:center; color:#666;">Maç bulunamadı.</div>';
    }
    profilesArea.appendChild(section);
}

fetchMatches();
