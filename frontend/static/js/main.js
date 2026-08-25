// 1. 카드 리스트 검색 함수
async function searchCards() {
    const input = document.getElementById('searchInput');
    const query = input.value.trim();
    
    // HTML의 id="langSelect"와 일치시킴
    const langSelect = document.getElementById('langSelect');
    // 사용자가 선택한 값 (EN 또는 JP)을 가져옴
    const selectedLang = langSelect ? langSelect.value : 'EN';

    if (!query) {
        alert("검색하실 포켓몬 이름을 입력해주세요!");
        return;
    }

    const cardListSection = document.getElementById('cardListSection');
    const cardList = document.getElementById('cardList');
    const priceSection = document.getElementById('priceResultSection');
    
    cardList.innerHTML = '<p style="text-align:center; width:100%; padding: 40px;">🔍 데이터를 찾는 중입니다...</p>';
    cardListSection.classList.remove('hidden');
    priceSection.classList.add('hidden'); 

    try {
        // 서버 API 호출 시 language 파라미터에 EN 또는 JP 전달
        const response = await fetch(`/api/search?name=${encodeURIComponent(query)}&language=${selectedLang}`);
        if (!response.ok) throw new Error("서버 응답 오류");
        
        const cards = await response.json();
        cardList.innerHTML = '';

        if (!cards || cards.length === 0) {
            cardList.innerHTML = '<p style="text-align:center; width:100%; padding: 40px;">해당하는 카드가 없습니다.</p>';
            return;
        }

        cards.forEach(card => {
            const cardName = (card.name || "Unknown Name").replace(/'/g, "\\'");
            const cardSeries = (card.series || "Unknown Set").replace(/'/g, "\\'");
            const cardSeriesId = (card.series_id || "").replace(/'/g, "\\'");
            const cardNum = card.number || "??";
            
            // [수정 핵심] selectedLang이 'JP'인 경우 'ja'로, 아니면 'en'으로 서버에서 처리하도록 language 정보 저장
            const cardLang = card.language || (selectedLang === 'JP' ? 'ja' : 'en');

            const cardElement = document.createElement('div');
            cardElement.className = 'card-item';
            cardElement.innerHTML = `
                <div class="card-image-container">
                    <img class="card-image" src="${card.image_url}" alt="${cardName}" onerror="this.src='https://via.placeholder.com/150?text=No+Image'">
                </div>
                <div class="card-info">
                    <h4>${card.name}</h4>
                    <p class="series-info">${card.series} <b style="color:#3b4cca;">(${card.series_id})</b></p>
                    <p class="number-info">#${card.number}</p>
                    <button onclick="getPrices('${cardName}', '${cardSeries}', '${cardNum}', '${cardSeriesId}', '${cardLang}')">시세 확인</button>
                </div>
            `;
            cardList.appendChild(cardElement);
        });

    } catch (error) {
        console.error("검색 중 오류:", error);
        cardList.innerHTML = '<p style="text-align:center; width:100%; padding: 40px; color:red;">데이터를 가져오는 중 오류가 발생했습니다.</p>';
    }
}

// 2. 이베이 시세 가져오기 함수
async function getPrices(name, series, number, series_id, language) {
    const priceSection = document.getElementById('priceResultSection');
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('priceTableBody');
    
    priceSection.classList.remove('hidden');
    loading.classList.remove('hidden');
    tableBody.innerHTML = '';
    
    priceSection.scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch('/api/price', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name: name, 
                series: series, 
                number: number,
                series_id: series_id,
                lang: language // 'ja' 또는 'en'이 전달됨
            })
        });

        if (!response.ok) throw new Error("시세 데이터를 가져오는데 실패했습니다.");

        const prices = await response.json();
        loading.classList.add('hidden');

        if (!prices || prices.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:gray; padding: 20px;">최근 판매 내역을 찾을 수 없습니다. (eBay 데이터 없음)</td></tr>';
            return;
        }

        // 판매완료(sold) 데이터가 하나도 없고 전부 현재 판매중(active) 매물이면,
        // "실거래가 아님"을 표 위에 안내한다 (Marketplace Insights API 미승인 시 대체 데이터).
        const isAllActive = prices.every(item => item.status === 'active');
        if (isAllActive) {
            tableBody.innerHTML += `
                <tr>
                    <td colspan="3" style="text-align:center; color:#e67e22; background:#fff8ec; padding: 12px; font-size:0.85rem;">
                        ⚠️ 판매완료 데이터를 아직 가져올 수 없어, 현재 판매중인 매물의 호가를 참고용으로 보여드립니다.
                    </td>
                </tr>
            `;
        }

        prices.forEach(item => {
            // item.link는 eBay가 내려주는 실제 상품 상세 페이지 URL(itemWebUrl).
            // 없을 때만(예전 데이터 등) 검색 결과 페이지로 대체 이동한다.
            const ebayLink = item.link || `https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(item.title)}`;
            const statusBadge = item.status === 'sold'
                ? '<span style="color:#2ecc71; font-weight:bold;">판매완료</span>'
                : '<span style="color:#e67e22;">판매중(참고)</span>';

            const row = `
                <tr style="cursor:pointer;" title="클릭하면 이베이 상세 페이지로 이동합니다">
                    <td>
                        <div style="font-size:0.85rem; color:#444; line-height:1.4;">${item.title}</div>
                        <a href="${ebayLink}" target="_blank" rel="noopener noreferrer" style="color:#3498db; font-weight:bold; text-decoration:none; font-size:0.85rem;">🔗 이베이에서 상세 보기</a>
                        <span style="margin-left:6px; font-size:0.8rem;">${statusBadge}</span>
                    </td>
                    <td><b style="color:#2f3542; white-space: nowrap;">${item.price} ${item.currency}</b></td>
                    <td style="color:#747d8c; font-size:0.85rem; white-space: nowrap;">${item.sold_date}</td>
                </tr>
            `;
            tableBody.innerHTML += row;
        });
    } catch (error) {
        console.error("시세조회 오류:", error);
        loading.classList.add('hidden');
        tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:red; padding: 20px;">시세를 가져오는 중 에러가 발생했습니다.</td></tr>';
    }
}