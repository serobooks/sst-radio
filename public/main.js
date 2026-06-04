/* ==========================================
   오늘따라 신승태 라디오 아카이브 프론트엔드 로직
   Vanilla JS & Async Backend Connection
   ========================================== */

document.addEventListener('DOMContentLoaded', () => {
    // 1. DOM 요소 선택
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const recommendTags = document.getElementById('recommend-tags');
    const resultsContainer = document.getElementById('results-container');
    const resultsCount = document.getElementById('results-count');
    const resultsMetaBar = document.querySelector('.results-meta-bar');

    
    // 추천 해시태그 무작위 정렬 및 모바일 대비 4개 제한 노출
    if (recommendTags) {
        const allTags = Array.from(recommendTags.querySelectorAll('.tag-btn'));
        for (let i = allTags.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [allTags[i], allTags[j]] = [allTags[j], allTags[i]];
        }
        recommendTags.innerHTML = '';
        allTags.slice(0, 4).forEach(tag => recommendTags.appendChild(tag));
    }

    
    // 마도사의 조언 (포춘쿠키) 관련 DOM
    const cookieWrapper = document.getElementById('cookie-wrapper');
    const advicePaper = document.getElementById('advice-paper');
    const actionArea = document.getElementById('action-area');
    const adviceBtn = document.getElementById('advice-btn');
    const adviceEp = document.getElementById('advice-ep');
    const adviceText = document.getElementById('advice-text');
    const adviceYoutubeLink = document.getElementById('advice-youtube-link');

    const API_BASE = '/api';
    const SNIPPET_MAX_LENGTH = 180; // 💡 검색 결과 대사 카드에 띄울 최대 글자 수 (이 숫자를 변경해 분량을 조절해 보세요!)

    // 2. 검색 결과 하이라이트 처리 헬퍼 함수 (쉼표로 구분된 다중 키워드 지원)
    function highlightText(text, keyword) {
        if (!keyword) return text;
        const keywords = keyword.split(',').map(k => k.trim()).filter(k => k);
        if (keywords.length === 0) return text;
        
        const escapedKeywords = keywords.map(k => k.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'));
        const regex = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    // 2-2. 검색어 기준 스마트 스니펫 슬라이싱 함수 (모바일 및 가독성 최적화)
    function getSmartSnippet(text, keyword, maxLength = 110) {
        if (!keyword) return text.substring(0, maxLength) + (text.length > maxLength ? "..." : "");
        
        const keywords = keyword.split(',').map(k => k.trim()).filter(k => k);
        let index = -1;
        
        for (const k of keywords) {
            const idx = text.toLowerCase().indexOf(k.toLowerCase());
            if (idx !== -1 && (index === -1 || idx < index)) {
                index = idx;
            }
        }
        
        if (index === -1) {
            return text.substring(0, maxLength) + (text.length > maxLength ? "..." : "");
        }
        
        const prefixLen = Math.floor(maxLength * 0.3);
        let start = Math.max(0, index - prefixLen);
        let end = Math.min(text.length, start + maxLength);
        
        if (end === text.length) {
            start = Math.max(0, end - maxLength);
        }
        
        let snippet = text.substring(start, end);
        if (start > 0) snippet = "..." + snippet;
        if (end < text.length) snippet = snippet + "...";
        
        return snippet;
    }

    // 3. 초 단위 시간을 '분:초' 형태로 깔끔하게 포맷팅
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // 4. API 검색 비동기 실행 함수
    async function performSearch(query) {
        if (!query || !query.trim()) return;
        
        // 검색 중 임시 스켈레톤/로더 렌더링
        resultsContainer.innerHTML = `
            <div class="initial-placeholder-msg text-center">
                <p class="placeholder-emoji">🔍</p>
                <p class="placeholder-text">아카이브 통합 데이터베이스 스캔 중...</p>
            </div>
        `;
        resultsMetaBar.style.display = 'none';

        // static 매핑용 하이라이트 쿼리 전처리
        let highlightQuery = query.trim();
        if (query.startsWith("static:")) {
            const parts = query.replace("static:", "").split(",");
            const words = parts.map(p => p.split("-")[2]).filter(w => w);
            highlightQuery = words.join(",");
        }

        try {
            const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error('API 검색 요청에 실패했습니다.');
            }
            
            const results = await response.json();
            renderResults(results, highlightQuery);
        } catch (error) {
            console.error('검색 중 에러 발생:', error);
            resultsContainer.innerHTML = `
                <div class="no-results-msg text-center">
                    <p class="placeholder-emoji">⚠️</p>
                    <p class="placeholder-text">데이터를 불러오는 중 오류가 발생했습니다. 다시 시도해 주세요.</p>
                </div>
            `;
        }
    }

    // 5. 검색 결과 카드 그리드 렌더링 함수
    function renderResults(results, query) {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = `
                <div class="no-results-msg text-center">
                    <p class="placeholder-emoji">🔍</p>
                    <p class="placeholder-text">아쉽게도 '${query}'(이)가 언급된 순간을 찾지 못했습니다.<br>다른 단어로 다시 검색해보세요!</p>
                </div>
            `;
            resultsMetaBar.style.display = 'none';
            return;
        }

        resultsCount.textContent = results.length;
        resultsMetaBar.style.display = 'block';
        resultsContainer.innerHTML = '';

        results.forEach(item => {
            const card = document.createElement('div');
            card.className = 'glass-card result-card';

            const timeStr = formatTime(item.time);
            const isPlaceholderId = item.video_id.startsWith('YOUTUBE_ID');
            
            // 실제 주소 링크 생성 (유튜브 타임라인 이동 t=초 공식 적용)
            const youtubeUrl = isPlaceholderId 
                ? '#' 
                : `https://youtu.be/${item.video_id}?t=${item.time}`;

            // 스마트 스니펫 추출 및 하이라이트 순차 적용
            const snippet = getSmartSnippet(item.text, query, SNIPPET_MAX_LENGTH);
            const highlightedQuote = highlightText(snippet, query);

            // 유튜브 썸네일 이미지 주소 생성
            const thumbUrl = isPlaceholderId
                ? ''
                : `https://img.youtube.com/vi/${item.video_id}/mqdefault.jpg`;

            card.innerHTML = `
                <div class="thumbnail-area">
                    ${isPlaceholderId ? `
                        <div class="placeholder-thumb" aria-label="임시 썸네일 플레이스홀더">
                            <span class="placeholder-thumb-icon">📻</span>
                            <span class="placeholder-thumb-label">오늘따라 신승태</span>
                        </div>
                    ` : `
                        <img src="${thumbUrl}" class="thumb-img" alt="${item.title} 유튜브 섬네일" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                        <div class="placeholder-thumb" style="display:none;" aria-label="썸네일 로드 실패 플레이스홀더">
                            <span class="placeholder-thumb-icon">📺</span>
                            <span class="placeholder-thumb-label">방송 화면 준비중</span>
                        </div>
                    `}
                </div>
                <div class="card-info-area">
                    <div class="card-meta">
                        <span class="episode-title">${item.title.replace(/오늘따라\s+신승태\s*/g, '')}</span>
                        <span class="episode-time-tag">⏱️ ${timeStr}</span>
                        <span class="episode-date">${item.date}</span>
                    </div>
                    <div class="quote-bubble">
                        <p class="quote-text">${highlightedQuote}</p>
                    </div>
                    <div class="card-action-bar">
                        <a href="${youtubeUrl}" class="link-youtube-timeline" ${isPlaceholderId ? 'onclick="alert(\'유튜브 동영상 ID 매핑 교체 가이드를 참조하여 youtube_mapping.py를 수정하면 실제 유튜브 타임라인 영상으로 즉시 이동합니다.\'); return false;"' : 'target="_blank" rel="noopener noreferrer"'}>
                            🎬 ${isPlaceholderId ? '유튜브 연동 전 (알림 보기)' : '유튜브 재생시점으로 이동'}
                        </a>
                    </div>
                </div>
            `;
            resultsContainer.appendChild(card);
        });
    }

    // 6. '오늘 하루 마도사의 조언' 비동기 갱신 및 애니메이션 제어
    async function fetchRandomAdvice(isSilent = false) {
        try {
            const response = await fetch(`${API_BASE}/advice`);
            if (!response.ok) {
                throw new Error('조언 데이터를 가져오지 못했습니다.');
            }
            const data = await response.json();
            
            // 데이터 업데이트
            adviceEp.textContent = `오늘따라 신승태 ${data.episode}회`;
            adviceText.textContent = `"${data.text}"`;
            
            const isPlaceholderId = data.video_id.startsWith('YOUTUBE_ID');
            if (isPlaceholderId) {
                adviceYoutubeLink.href = '#';
                adviceYoutubeLink.onclick = (e) => {
                    e.preventDefault();
                    alert("실제 유튜브 동영상 ID 매핑 교체 가이드를 참조하여 youtube_mapping.py를 수정하면 가수가 이 말을 건네는 유튜브 영상으로 즉시 이동합니다.");
                };
                adviceYoutubeLink.innerHTML = "🎬 유튜브 연동 전 (알림 보기)";
            } else {
                adviceYoutubeLink.href = `https://youtu.be/${data.video_id}?t=10`;
                adviceYoutubeLink.onclick = null;
                adviceYoutubeLink.innerHTML = "🎬 추천 영상 바로 가기";
            }
        } catch (error) {
            console.error('조언 로딩 중 에러:', error);
            adviceText.textContent = '"건강이 최고입니다. 감기 걸리지 마시고 따뜻한 물 자주 드세요!"';
        }
    }

    // 7. 이벤트 바인딩
    // A. 검색창 이벤트
    searchBtn.addEventListener('click', () => {
        performSearch(searchInput.value);
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch(searchInput.value);
        }
    });

    // B. 추천 해시태그 버튼 클릭 이벤트
    recommendTags.addEventListener('click', (e) => {
        const clickedTag = e.target.closest('.tag-btn');
        if (clickedTag) {
            const query = clickedTag.getAttribute('data-tag');
            
            // static: 쿼리일 경우 검색창에 지저분한 내부 데이터를 노출하지 않고 태그 라벨명만 예쁘게 표시합니다.
            if (query.startsWith("static:")) {
                searchInput.value = clickedTag.textContent.replace('#', '').trim();
            } else {
                searchInput.value = query;
            }
            
            performSearch(query);
        }
    });

    // C. 포춘쿠키 개봉 인터랙션 (클릭 시 쪼개지고 흔들린 후 페이드아웃, 동일 자리에 조언 쪽지 노출)
    cookieWrapper.addEventListener('click', () => {
        // 이미 개봉된 상태라면 무시
        if (cookieWrapper.classList.contains('is-cracked') || cookieWrapper.classList.contains('is-shaking')) return;
        
        const cookieImg = document.getElementById('fortune-cookie-img');
        
        // 1단계: 흔들림 모션 추가 및 즉시 깨진 쿠키 이미지로 교체
        cookieWrapper.classList.add('is-shaking');
        cookieImg.src = 'fortune_cookie_open.png';
        
        // 2단계: 0.4초 흔들림 애니메이션 후, 페이드아웃(is-cracked) 트리거
        setTimeout(() => {
            cookieWrapper.classList.remove('is-shaking');
            cookieWrapper.classList.add('is-cracked');
            
            // 3단계: 페이드아웃이 완성되는 시점에 쪽지와 다시 뽑기 영역 노출
            setTimeout(() => {
                cookieWrapper.style.opacity = '0';
                cookieWrapper.style.pointerEvents = 'none';
                advicePaper.style.display = 'block';
                actionArea.style.display = 'block';
            }, 400);
        }, 400);
    });

    // D. 조언 다시 뽑기 버튼 (쪽지가 사라지고 포춘쿠키가 동일 자리에 퐁! 하고 재생성됨)
    adviceBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        
        // 1단계: 쪽지와 다시뽑기 버튼 숨김
        advicePaper.style.display = 'none';
        actionArea.style.display = 'none';
        
        // 2단계: 포춘쿠키를 퐁! 하고 다시 등장시키며 동시에 비동기로 새 조언 충전해둠
        setTimeout(async () => {
            await fetchRandomAdvice();
            const cookieImg = document.getElementById('fortune-cookie-img');
            cookieImg.src = 'fortune_cookie_closed.png'; // 닫힌 쿠키로 원복
            
            cookieWrapper.style.opacity = '1';
            cookieWrapper.style.pointerEvents = 'auto';
            cookieWrapper.classList.remove('is-cracked');
        }, 300);
    });

    // 7-2. 모바일 반응형 placeholder 업데이트 로직
    const updatePlaceholder = () => {
        if (window.matchMedia('(max-width: 768px)').matches) {
            searchInput.placeholder = '키워드를 입력해 주세요';
        } else {
            searchInput.placeholder = '다시 듣고 싶은 이야기의 키워드를 입력해 보세요(예: 녹음, 경기민요, 선글라스)';
        }
    };
    updatePlaceholder();
    window.addEventListener('resize', updatePlaceholder);

    // 8. 페이지 초기화 로드
    // 최초 구동 시 1회 무작위 조언 가져와서 캐싱해둠
    fetchRandomAdvice(true);
});
